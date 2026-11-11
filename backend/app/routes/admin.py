from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..database import get_db
from ..models import User, Course, Enrollment, Submission, QuizAttempt, ActivityLog
from ..schemas import (
    UserOut, UserCreate, UserUpdate, EnrollmentOut, EnrollmentCreate, AdminStatsOut
)
from ..auth import hash_password
from ..permissions import require_admin, log_activity

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/stats", response_model=AdminStatsOut)
def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve system metrics for administrator dashboard."""
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_students = db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
    total_teachers = db.scalar(select(func.count(User.id)).where(User.role == "teacher")) or 0
    total_courses = db.scalar(select(func.count(Course.id))) or 0
    total_enrollments = db.scalar(select(func.count(Enrollment.id))) or 0
    total_submissions = db.scalar(select(func.count(Submission.id))) or 0
    total_quiz_attempts = db.scalar(select(func.count(QuizAttempt.id))) or 0
    recent_activity_count = db.scalar(select(func.count(ActivityLog.id))) or 0

    return {
        "total_users": total_users,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "total_submissions": total_submissions,
        "total_quiz_attempts": total_quiz_attempts,
        "recent_activity_count": recent_activity_count,
    }


@router.get("/users", response_model=List[UserOut])
def admin_list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all user accounts."""
    users = db.scalars(select(User).order_by(User.id)).all()
    return users


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new user account with role."""
    existing_user = db.scalar(
        select(User).where((User.username == payload.username) | (User.email == payload.email))
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exists.",
        )

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_CREATE_USER",
        resource_type="user",
        resource_id=str(user.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"Admin created account {user.username} with role {user.role}.",
    )
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Modify user role, active status, or details."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(user)

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_UPDATE_USER",
        resource_type="user",
        resource_id=str(user.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Admin updated user {user.username} (role: {user.role}, active: {user.is_active}).",
    )
    return user


@router.get("/enrolments", response_model=List[EnrollmentOut])
def admin_list_enrollments(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all course enrolments."""
    enrollments = db.scalars(select(Enrollment).order_by(Enrollment.id)).all()
    results = []
    for e in enrollments:
        results.append(
            {
                "id": e.id,
                "course_id": e.course_id,
                "course_code": e.course.code if e.course else "",
                "course_title": e.course.title if e.course else "",
                "user_id": e.user_id,
                "username": e.user.username if e.user else "",
                "full_name": e.user.full_name if e.user else "",
                "role": e.role,
                "enrolled_at": e.enrolled_at,
            }
        )
    return results


@router.post("/enrolments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def admin_create_enrollment(
    payload: EnrollmentCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Enrol a student into a course."""
    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    existing = db.scalar(
        select(Enrollment).where(
            Enrollment.course_id == payload.course_id,
            Enrollment.user_id == payload.user_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {user.username} is already enrolled in {course.code}.",
        )

    enrollment = Enrollment(
        course_id=payload.course_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_ENROL",
        resource_type="enrolment",
        resource_id=str(enrollment.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"Enrolled {user.username} into {course.code}.",
    )
    return {
        "id": enrollment.id,
        "course_id": course.id,
        "course_code": course.code,
        "course_title": course.title,
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": enrollment.role,
        "enrolled_at": enrollment.enrolled_at,
    }


@router.delete("/enrolments/{enrolment_id}")
def admin_delete_enrollment(
    enrolment_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unenrol a user from a course."""
    enrollment = db.get(Enrollment, enrolment_id)
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrolment not found.")

    course_code = enrollment.course.code if enrollment.course else "Unknown"
    username = enrollment.user.username if enrollment.user else "Unknown"

    db.delete(enrollment)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_UNENROL",
        resource_type="enrolment",
        resource_id=str(enrolment_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Removed enrolment of {username} from {course_code}.",
    )
    return {"message": "Enrolment removed successfully."}
