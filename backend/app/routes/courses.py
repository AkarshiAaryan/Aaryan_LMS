from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..database import get_db
from ..models import User, Course, Enrollment, Assignment, Quiz, Resource, Announcement, CoursePolicy
from ..schemas import (
    CourseOut, CourseCreate, CourseUpdate, CourseArchive,
    AnnouncementOut, AnnouncementCreate, AnnouncementUpdate,
    CoursePolicyOut
)
from ..auth import get_current_user
from ..permissions import (
    require_admin,
    verify_course_access,
    verify_course_professor_or_admin,
    get_user_course_role,
    log_activity,
)

router = APIRouter(prefix="/courses", tags=["Courses"])
announcements_router = APIRouter(prefix="/announcements", tags=["Announcements"])


def serialize_course(course: Course, current_user: User, db: Session) -> Dict[str, Any]:
    student_count = db.scalar(
        select(func.count(Enrollment.id)).where(
            Enrollment.course_id == course.id,
            Enrollment.role == "student",
            Enrollment.status == "active",
        )
    ) or 0

    # Get active TAs
    ta_enrollments = db.scalars(
        select(Enrollment).where(
            Enrollment.course_id == course.id,
            Enrollment.role == "ta",
            Enrollment.status == "active",
        )
    ).all()
    ta_names = [e.user.full_name for e in ta_enrollments if e.user]

    role_in_course = get_user_course_role(course.id, current_user, db, include_suspended=True)

    return {
        "id": course.id,
        "code": course.code,
        "title": course.title,
        "description": course.description,
        "teacher_id": course.teacher_id,
        "teacher_name": course.teacher.full_name if course.teacher else "Unassigned",
        "student_count": student_count,
        "current_user_role": role_in_course,
        "tas": ta_names,
        "is_archived": getattr(course, "is_archived", False),
        "created_at": course.created_at,
    }


@router.get("", response_model=List[CourseOut])
def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List accessible courses based on authenticated user course memberships."""
    if current_user.role == "admin":
        courses = db.scalars(select(Course).order_by(Course.code)).all()
    else:
        # Courses where user is instructor OR enrolled (excluding revoked enrollments)
        enrolled_course_ids = select(Enrollment.course_id).where(
            Enrollment.user_id == current_user.id,
            Enrollment.status != "revoked",
        )
        courses = db.scalars(
            select(Course)
            .where(
                (Course.teacher_id == current_user.id) | (Course.id.in_(enrolled_course_ids))
            )
            .order_by(Course.code)
        ).all()

    return [serialize_course(c, current_user, db) for c in courses]


@router.get("/{course_id}", response_model=CourseOut)
def get_course_by_id(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve course details. Enforces enrollment / assignment boundaries."""
    course = verify_course_access(course_id, current_user, db)
    return serialize_course(course, current_user, db)


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new course (Administrator only)."""
    existing = db.scalar(select(Course).where(Course.code == payload.code))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course with code '{payload.code}' already exists.",
        )

    course = Course(
        code=payload.code,
        title=payload.title,
        description=payload.description,
        teacher_id=payload.teacher_id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_COURSE",
        resource_type="course",
        resource_id=str(course.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"Admin created course {course.code} ({course.title}).",
    )
    return serialize_course(course, current_user, db)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update course information (Assigned professor or Administrator only)."""
    course = verify_course_professor_or_admin(course_id, current_user, db)

    if payload.code is not None and payload.code != course.code:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: only site administrators can change the course code.",
            )
        course.code = payload.code

    if payload.title is not None:
        course.title = payload.title
    if payload.description is not None:
        course.description = payload.description
    if payload.teacher_id is not None:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: only site administrators can reassign course professors.",
            )
        course.teacher_id = payload.teacher_id

    db.commit()
    db.refresh(course)

    log_activity(
        db=db,
        user=current_user,
        action="UPDATE_COURSE",
        resource_type="course",
        resource_id=str(course.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Updated course {course.code}.",
    )
    return serialize_course(course, current_user, db)


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a course (Administrator only)."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    db.delete(course)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="DELETE_COURSE",
        resource_type="course",
        resource_id=str(course_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Admin deleted course {course.code}.",
    )
    return {"message": f"Course {course.code} deleted successfully."}


@router.get("/{course_id}/overview")
def get_course_overview(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get metrics, participants, and overview cards for an authorized course."""
    course = verify_course_access(course_id, current_user, db)

    assignment_count = db.scalar(
        select(func.count(Assignment.id)).where(Assignment.course_id == course_id)
    ) or 0
    quiz_count = db.scalar(
        select(func.count(Quiz.id)).where(Quiz.course_id == course_id)
    ) or 0
    resource_count = db.scalar(
        select(func.count(Resource.id)).where(Resource.course_id == course_id)
    ) or 0
    student_count = db.scalar(
        select(func.count(Enrollment.id)).where(
            Enrollment.course_id == course_id,
            Enrollment.role == "student",
            Enrollment.status == "active",
        )
    ) or 0

    announcements = db.scalars(
        select(Announcement)
        .where(Announcement.course_id == course_id)
        .order_by(Announcement.created_at.desc())
        .limit(5)
    ).all()

    # Active Participants
    enrollments = db.scalars(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.status == "active",
        )
    ).all()

    tas = [
        {"id": e.user.id, "name": e.user.full_name, "username": e.user.username, "role": "TA"}
        for e in enrollments if e.role == "ta" and e.user
    ]
    students = [
        {"id": e.user.id, "name": e.user.full_name, "username": e.user.username, "role": "Student"}
        for e in enrollments if e.role == "student" and e.user
    ]

    return {
        "course": serialize_course(course, current_user, db),
        "metrics": {
            "assignments": assignment_count,
            "quizzes": quiz_count,
            "resources": resource_count,
            "students": student_count,
        },
        "participants": {
            "professor": {
                "id": course.teacher.id if course.teacher else None,
                "name": course.teacher.full_name if course.teacher else "Unassigned",
                "username": course.teacher.username if course.teacher else "",
            },
            "tas": tas,
            "students": students,
        },
        "recent_announcements": [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "author": a.author.full_name if a.author else "System",
                "created_at": a.created_at,
            }
            for a in announcements
        ],
    }


@router.get("/{course_id}/policies", response_model=List[CoursePolicyOut])
def get_course_policies(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve course policies and assessment rules in readable text."""
    verify_course_access(course_id, current_user, db)
    policies = db.scalars(
        select(CoursePolicy)
        .where(CoursePolicy.course_id == course_id)
        .order_by(CoursePolicy.id)
    ).all()
    return policies


@router.get("/{course_id}/announcements", response_model=List[AnnouncementOut])
def get_course_announcements(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve announcements for an authorized course."""
    course = verify_course_access(course_id, current_user, db)
    announcements = db.scalars(
        select(Announcement)
        .where(Announcement.course_id == course_id)
        .order_by(Announcement.created_at.desc())
    ).all()

    return [
        AnnouncementOut(
            id=a.id,
            course_id=a.course_id,
            course_code=course.code,
            title=a.title,
            content=a.content,
            author_id=a.author_id,
            author_name=a.author.full_name if a.author else None,
            created_at=a.created_at,
        )
        for a in announcements
    ]


@router.post("/{course_id}/announcements", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def post_course_announcement(
    course_id: int,
    payload: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Post an announcement (Course Professor or Administrator only)."""
    course = verify_course_professor_or_admin(course_id, current_user, db)

    announcement = Announcement(
        course_id=course_id,
        title=payload.title,
        content=payload.content,
        author_id=current_user.id,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    return AnnouncementOut(
        id=announcement.id,
        course_id=announcement.course_id,
        course_code=course.code,
        title=announcement.title,
        content=announcement.content,
        author_id=announcement.author_id,
        author_name=current_user.full_name,
        created_at=announcement.created_at,
    )


@router.put("/{course_id}/archive", response_model=CourseOut)
def archive_course(
    course_id: int,
    payload: Optional[CourseArchive] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Archive or unarchive a course (Professor or Administrator only)."""
    course = verify_course_professor_or_admin(course_id, current_user, db)
    archive_status = payload.is_archived if payload is not None else True
    course.is_archived = archive_status
    db.commit()
    db.refresh(course)

    log_activity(
        db=db,
        user=current_user,
        action="ARCHIVE_COURSE",
        resource_type="course",
        resource_id=str(course.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Course {course.code} archive status set to {archive_status}.",
    )
    return serialize_course(course, current_user, db)


def _update_announcement_impl(
    announcement_id: int,
    payload: AnnouncementUpdate,
    course_id: Optional[int],
    current_user: User,
    db: Session,
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found.")

    if course_id is not None and announcement.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Announcement does not belong to this course.",
        )

    course = verify_course_professor_or_admin(announcement.course_id, current_user, db)

    if payload.title is not None:
        announcement.title = payload.title
    if payload.content is not None:
        announcement.content = payload.content

    db.commit()
    db.refresh(announcement)

    log_activity(
        db=db,
        user=current_user,
        action="UPDATE_ANNOUNCEMENT",
        resource_type="announcement",
        resource_id=str(announcement.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Updated announcement {announcement.id} in course {course.code}.",
    )
    return AnnouncementOut(
        id=announcement.id,
        course_id=announcement.course_id,
        course_code=course.code,
        title=announcement.title,
        content=announcement.content,
        author_id=announcement.author_id,
        author_name=announcement.author.full_name if announcement.author else None,
        created_at=announcement.created_at,
    )


def _delete_announcement_impl(
    announcement_id: int,
    course_id: Optional[int],
    current_user: User,
    db: Session,
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found.")

    if course_id is not None and announcement.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Announcement does not belong to this course.",
        )

    course = verify_course_professor_or_admin(announcement.course_id, current_user, db)

    db.delete(announcement)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="DELETE_ANNOUNCEMENT",
        resource_type="announcement",
        resource_id=str(announcement_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Deleted announcement {announcement_id} from course {course.code}.",
    )
    return {"message": "Announcement deleted successfully."}


@router.put("/announcements/{announcement_id}", response_model=AnnouncementOut)
@router.put("/{course_id}/announcements/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    course_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an announcement (Course Professor or Administrator only)."""
    return _update_announcement_impl(announcement_id, payload, course_id, current_user, db)


@announcements_router.put("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement_alias(
    announcement_id: int,
    payload: AnnouncementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _update_announcement_impl(announcement_id, payload, None, current_user, db)


@router.delete("/announcements/{announcement_id}")
@router.delete("/{course_id}/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    course_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an announcement (Course Professor or Administrator only)."""
    return _delete_announcement_impl(announcement_id, course_id, current_user, db)


@announcements_router.delete("/{announcement_id}")
def delete_announcement_alias(
    announcement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _delete_announcement_impl(announcement_id, None, current_user, db)
