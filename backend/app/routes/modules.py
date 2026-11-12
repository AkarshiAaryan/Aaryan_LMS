from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, LearningModule, Lesson, ModuleCompletion
from ..schemas import (
    LearningModuleOut, LearningModuleCreate, LessonOut, LessonCreate
)
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_staff,
    get_user_course_role,
    log_activity,
)
from ..clock import Clock

router = APIRouter(tags=["Learning Modules"])


def serialize_module(m: LearningModule, include_lessons: bool = True, redact_content: bool = False) -> Dict[str, Any]:
    lessons_data = []
    if include_lessons and m.lessons:
        for l in sorted(m.lessons, key=lambda x: x.order_index):
            lessons_data.append({
                "id": l.id,
                "module_id": l.module_id,
                "title": l.title,
                "content": "[Content Locked]" if redact_content else l.content,
                "order_index": l.order_index,
                "is_published": l.is_published,
                "created_at": l.created_at,
            })

    return {
        "id": m.id,
        "course_id": m.course_id,
        "title": m.title,
        "description": m.description,
        "order_index": m.order_index,
        "is_published": m.is_published,
        "unlock_date": m.unlock_date or "",
        "prerequisite_id": m.prerequisite_id,
        "prerequisite_title": m.prerequisite.title if m.prerequisite else None,
        "created_at": m.created_at,
        "lessons": lessons_data,
    }


def is_module_unlocked(module: LearningModule, request: Request) -> bool:
    """Check if the module unlock date has passed relative to simulation clock."""
    if not module.unlock_date:
        return True
    try:
        unlock_dt = Clock.parse_iso_datetime(module.unlock_date)
        current_time = Clock.get_time(request)
        return current_time >= unlock_dt
    except Exception:
        return True


@router.get("/courses/{course_id}/modules", response_model=List[LearningModuleOut])
def list_course_modules(
    course_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List learning modules for a course. Students only see published, unlocked modules."""
    verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    query = select(LearningModule).where(LearningModule.course_id == course_id)
    if course_role not in ["admin", "professor", "ta"]:
        query = query.where(LearningModule.is_published == True)

    modules = db.scalars(query.order_index_by(LearningModule.order_index) if hasattr(query, 'order_index_by') else query.order_by(LearningModule.order_index)).all()

    result = []
    for m in modules:
        if course_role in ["admin", "professor", "ta"]:
            result.append(serialize_module(m, include_lessons=True, redact_content=False))
        else:
            unlocked = is_module_unlocked(m, request)
            # If locked by date, lessons are listed but content is redacted
            result.append(serialize_module(m, include_lessons=True, redact_content=not unlocked))

    log_activity(
        db=db,
        user=current_user,
        action="LIST_LEARNING_MODULES",
        resource_type="module",
        resource_id=f"course:{course_id}",
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} listed {len(result)} modules for course #{course_id}.",
    )
    return result


@router.post("/courses/{course_id}/modules", response_model=LearningModuleOut, status_code=status.HTTP_201_CREATED)
def create_module(
    course_id: int,
    module_data: LearningModuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new learning module. Course staff only."""
    verify_course_staff(course_id, current_user, db)

    # Validate prerequisite belongs to same course
    if module_data.prerequisite_id:
        prereq = db.get(LearningModule, module_data.prerequisite_id)
        if not prereq or prereq.course_id != course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prerequisite module does not exist or belongs to another course.",
            )

    new_module = LearningModule(
        course_id=course_id,
        title=module_data.title,
        description=module_data.description,
        order_index=module_data.order_index,
        is_published=module_data.is_published,
        unlock_date=module_data.unlock_date,
        prerequisite_id=module_data.prerequisite_id,
    )
    db.add(new_module)
    db.commit()
    db.refresh(new_module)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_LEARNING_MODULE",
        resource_type="module",
        resource_id=str(new_module.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"Staff {current_user.username} created module #{new_module.id} in course #{course_id}.",
    )
    return serialize_module(new_module)


@router.get("/modules/{module_id}", response_model=LearningModuleOut)
def get_module(
    module_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get single module details and lessons."""
    module = db.get(LearningModule, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    verify_course_access(module.course_id, current_user, db)
    course_role = get_user_course_role(module.course_id, current_user, db)

    if course_role not in ["admin", "professor", "ta"]:
        if not module.is_published:
            log_activity(
                db=db,
                user=current_user,
                action="VIEW_LEARNING_MODULE",
                resource_type="module",
                resource_id=str(module_id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {current_user.username} blocked from unpublished module #{module_id}.",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This module is not published.")

        if not is_module_unlocked(module, request):
            log_activity(
                db=db,
                user=current_user,
                action="VIEW_LEARNING_MODULE",
                resource_type="module",
                resource_id=str(module_id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {current_user.username} blocked from locked module #{module_id} (unlocks {module.unlock_date}).",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Module locked until {module.unlock_date}.")

        # Prerequisite check
        if module.prerequisite_id:
            completed_prereq = db.scalar(
                select(ModuleCompletion).where(
                    ModuleCompletion.module_id == module.prerequisite_id,
                    ModuleCompletion.student_id == current_user.id,
                )
            )
            if not completed_prereq:
                prereq_title = module.prerequisite.title if module.prerequisite else f"Module #{module.prerequisite_id}"
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: you must complete prerequisite module '{prereq_title}' first.",
                )

    return serialize_module(module, include_lessons=True, redact_content=False)


@router.post("/modules/{module_id}/complete")
def complete_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a learning module as completed for the current student."""
    module = db.get(LearningModule, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    verify_course_access(module.course_id, current_user, db)

    existing = db.scalar(
        select(ModuleCompletion).where(
            ModuleCompletion.module_id == module_id,
            ModuleCompletion.student_id == current_user.id,
        )
    )
    if not existing:
        completion = ModuleCompletion(
            module_id=module_id,
            student_id=current_user.id,
        )
        db.add(completion)
        db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="COMPLETE_LEARNING_MODULE",
        resource_type="module",
        resource_id=str(module_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} marked module #{module_id} as completed.",
    )
    return {"message": f"Module '{module.title}' marked as completed."}


@router.get("/modules/{module_id}/progress")
def get_module_progress(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get completion status of a module for the current student."""
    module = db.get(LearningModule, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    verify_course_access(module.course_id, current_user, db)

    completion = db.scalar(
        select(ModuleCompletion).where(
            ModuleCompletion.module_id == module_id,
            ModuleCompletion.student_id == current_user.id,
        )
    )
    return {
        "module_id": module.id,
        "is_completed": completion is not None,
        "completed_at": completion.completed_at if completion else None,
    }


@router.put("/modules/{module_id}", response_model=LearningModuleOut)
def update_module(
    module_id: int,
    module_data: LearningModuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update learning module. Course staff only."""
    module = db.get(LearningModule, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    verify_course_staff(module.course_id, current_user, db)

    module.title = module_data.title
    module.description = module_data.description
    module.order_index = module_data.order_index
    module.is_published = module_data.is_published
    module.unlock_date = module_data.unlock_date
    module.prerequisite_id = module_data.prerequisite_id

    db.commit()
    db.refresh(module)

    log_activity(
        db=db,
        user=current_user,
        action="UPDATE_LEARNING_MODULE",
        resource_type="module",
        resource_id=str(module_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"Staff {current_user.username} updated module #{module_id}.",
    )
    return serialize_module(module)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete learning module. Course staff only."""
    module = db.get(LearningModule, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    verify_course_staff(module.course_id, current_user, db)

    db.delete(module)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="DELETE_LEARNING_MODULE",
        resource_type="module",
        resource_id=str(module_id),
        outcome="ALLOW",
        http_status=status.HTTP_204_NO_CONTENT,
        detail=f"Staff {current_user.username} deleted module #{module_id}.",
    )
    return None


# ------------------- LESSONS -------------------

@router.post("/modules/{module_id}/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(
    module_id: int,
    lesson_data: LessonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new lesson inside a module. Course staff only."""
    module = db.get(LearningModule, module_id)
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    verify_course_staff(module.course_id, current_user, db)

    new_lesson = Lesson(
        module_id=module_id,
        title=lesson_data.title,
        content=lesson_data.content,
        order_index=lesson_data.order_index,
        is_published=lesson_data.is_published,
    )
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_LESSON",
        resource_type="lesson",
        resource_id=str(new_lesson.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"Staff {current_user.username} created lesson #{new_lesson.id} in module #{module_id}.",
    )
    return new_lesson


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(
    lesson_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View lesson content. Enforces module unlock and publication checks."""
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    module = lesson.module
    verify_course_access(module.course_id, current_user, db)
    course_role = get_user_course_role(module.course_id, current_user, db)

    if course_role not in ["admin", "professor", "ta"]:
        if not module.is_published or not lesson.is_published:
            log_activity(
                db=db,
                user=current_user,
                action="VIEW_LESSON",
                resource_type="lesson",
                resource_id=str(lesson_id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {current_user.username} blocked from unpublished lesson #{lesson_id}.",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This lesson is not published.")

        if not is_module_unlocked(module, request):
            log_activity(
                db=db,
                user=current_user,
                action="VIEW_LESSON",
                resource_type="lesson",
                resource_id=str(lesson_id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {current_user.username} blocked from locked lesson #{lesson_id} (module unlocks {module.unlock_date}).",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Module locked until {module.unlock_date}.")

    log_activity(
        db=db,
        user=current_user,
        action="VIEW_LESSON",
        resource_type="lesson",
        resource_id=str(lesson_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} viewed lesson #{lesson_id}.",
    )
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: int,
    lesson_data: LessonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update lesson. Course staff only."""
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    verify_course_staff(lesson.module.course_id, current_user, db)

    lesson.title = lesson_data.title
    lesson.content = lesson_data.content
    lesson.order_index = lesson_data.order_index
    lesson.is_published = lesson_data.is_published

    db.commit()
    db.refresh(lesson)

    log_activity(
        db=db,
        user=current_user,
        action="UPDATE_LESSON",
        resource_type="lesson",
        resource_id=str(lesson_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"Staff {current_user.username} updated lesson #{lesson_id}.",
    )
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete lesson. Course staff only."""
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    verify_course_staff(lesson.module.course_id, current_user, db)

    db.delete(lesson)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="DELETE_LESSON",
        resource_type="lesson",
        resource_id=str(lesson_id),
        outcome="ALLOW",
        http_status=status.HTTP_204_NO_CONTENT,
        detail=f"Staff {current_user.username} deleted lesson #{lesson_id}.",
    )
    return None
