from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..database import get_db
from ..models import User, Course, Assignment, Submission, GroupMember
from ..schemas import AssignmentOut, AssignmentCreate, AssignmentUpdate
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_professor_or_admin,
    get_user_course_role,
    log_activity,
)

router = APIRouter(tags=["Assignments"])


def serialize_assignment(
    assignment: Assignment,
    current_user: User,
    db: Session,
) -> Dict[str, Any]:
    submission_count = db.scalar(
        select(func.count(Submission.id)).where(Submission.assignment_id == assignment.id)
    ) or 0

    my_submission = None
    role = get_user_course_role(assignment.course_id, current_user, db)

    if role == "student":
        # Look for own submission or user's group submission
        sub = db.scalar(
            select(Submission).where(
                Submission.assignment_id == assignment.id,
                Submission.student_id == current_user.id,
            )
        )
        if not sub and assignment.is_group:
            # Check user group memberships
            user_groups = select(GroupMember.group_id).where(GroupMember.user_id == current_user.id)
            sub = db.scalar(
                select(Submission).where(
                    Submission.assignment_id == assignment.id,
                    Submission.group_id.in_(user_groups),
                )
            )

        if sub:
            my_submission = {
                "id": sub.id,
                "status": sub.status,
                "is_draft": sub.is_draft,
                "extension_granted": sub.extension_granted,
                "grade": sub.grade if sub.is_published else None,
                "max_grade": assignment.max_grade,
                "feedback": sub.feedback if sub.is_published else None,
                "submitted_at": sub.submitted_at,
                "content": sub.content,
            }

    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "course_code": assignment.course.code if assignment.course else "",
        "title": assignment.title,
        "description": assignment.description,
        "instructions": assignment.instructions,
        "due_date": assignment.due_date,
        "max_grade": assignment.max_grade,
        "submission_type": assignment.submission_type,
        "is_group": assignment.is_group,
        "allow_late": assignment.allow_late,
        "is_published": assignment.is_published,
        "created_at": assignment.created_at,
        "submission_count": submission_count,
        "my_submission": my_submission,
        "current_user_role": role,
    }


@router.get("/courses/{course_id}/assignments", response_model=List[AssignmentOut])
@router.get("/assignments/course/{course_id}", response_model=List[AssignmentOut])
def list_course_assignments(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all assignments for a course if user has access. Students see published only."""
    verify_course_access(course_id, current_user, db)
    role = get_user_course_role(course_id, current_user, db)

    stmt = select(Assignment).where(Assignment.course_id == course_id).order_by(Assignment.id)
    if role == "student":
        stmt = stmt.where(Assignment.is_published == True)

    assignments = db.scalars(stmt).all()
    return [serialize_assignment(a, current_user, db) for a in assignments]


@router.get("/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment_by_id(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve individual assignment details. Restricts unpublished assignments from students."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with ID {assignment_id} not found.",
        )

    verify_course_access(assignment.course_id, current_user, db)
    role = get_user_course_role(assignment.course_id, current_user, db)
    if role == "student" and not assignment.is_published:
        log_activity(
            db=db,
            user=current_user,
            action="VIEW_ASSIGNMENT",
            resource_type="assignment",
            resource_id=str(assignment.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {current_user.username} denied access to unpublished assignment '{assignment.title}'.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this assignment is unpublished.",
        )

    return serialize_assignment(assignment, current_user, db)


@router.post("/courses/{course_id}/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
@router.post("/assignments/course/{course_id}", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    course_id: int,
    payload: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an assignment in course (Assigned professor or Admin only)."""
    course = verify_course_professor_or_admin(course_id, current_user, db)

    assignment = Assignment(
        course_id=course_id,
        title=payload.title,
        description=payload.description,
        instructions=payload.instructions,
        due_date=payload.due_date,
        max_grade=payload.max_grade,
        submission_type=payload.submission_type,
        is_group=payload.is_group,
        allow_late=payload.allow_late,
        is_published=payload.is_published,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_ASSIGNMENT",
        resource_type="assignment",
        resource_id=str(assignment.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"Created assignment '{assignment.title}' in course {course.code}.",
    )
    return serialize_assignment(assignment, current_user, db)


@router.put("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an assignment (Assigned professor or Admin only)."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with ID {assignment_id} not found.",
        )

    # Enforce professor/admin ownership of assignment's course
    verify_course_professor_or_admin(assignment.course_id, current_user, db)

    if payload.title is not None:
        assignment.title = payload.title
    if payload.description is not None:
        assignment.description = payload.description
    if payload.instructions is not None:
        assignment.instructions = payload.instructions
    if payload.due_date is not None:
        assignment.due_date = payload.due_date
    if payload.max_grade is not None:
        assignment.max_grade = payload.max_grade
    if payload.submission_type is not None:
        assignment.submission_type = payload.submission_type
    if payload.is_group is not None:
        assignment.is_group = payload.is_group
    if payload.allow_late is not None:
        assignment.allow_late = payload.allow_late
    if payload.is_published is not None:
        assignment.is_published = payload.is_published

    db.commit()
    db.refresh(assignment)

    log_activity(
        db=db,
        user=current_user,
        action="UPDATE_ASSIGNMENT",
        resource_type="assignment",
        resource_id=str(assignment.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Updated assignment '{assignment.title}' in course ID {assignment.course_id}.",
    )
    return serialize_assignment(assignment, current_user, db)


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an assignment (Assigned professor or Admin only)."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    verify_course_professor_or_admin(assignment.course_id, current_user, db)

    db.delete(assignment)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="DELETE_ASSIGNMENT",
        resource_type="assignment",
        resource_id=str(assignment_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Deleted assignment ID {assignment_id}.",
    )
    return {"message": "Assignment deleted successfully."}
