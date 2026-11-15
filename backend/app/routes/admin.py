from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..database import get_db
from ..models import User, Course, Enrollment, Submission, QuizAttempt, ActivityLog, Department, CourseSection
from ..schemas import (
    UserOut, UserCreate, UserUpdate, CourseOut,
    EnrollmentOut, EnrollmentCreate, EnrollmentUpdate,
    DepartmentOut, DepartmentCreate, DepartmentUpdate,
    AdminStatsOut
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
                "status": e.status,
                "section_id": e.section_id,
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

    if payload.section_id is not None:
        section = db.get(CourseSection, payload.section_id)
        if not section or section.course_id != payload.course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section does not belong to this course or does not exist.",
            )

    enrollment = Enrollment(
        course_id=payload.course_id,
        user_id=payload.user_id,
        role=payload.role,
        status=payload.status,
        section_id=payload.section_id,
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
        detail=f"Enrolled {user.username} into {course.code} (status: {enrollment.status}).",
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
        "status": enrollment.status,
        "section_id": enrollment.section_id,
        "enrolled_at": enrollment.enrolled_at,
    }


@router.put("/enrolments/{enrolment_id}", response_model=EnrollmentOut)
def admin_update_enrollment(
    enrolment_id: int,
    payload: EnrollmentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Modify enrolment role, status, or section reassignment (Administrator only)."""
    enrollment = db.get(Enrollment, enrolment_id)
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrolment not found.")

    if payload.role is not None:
        enrollment.role = payload.role

    if payload.status is not None:
        enrollment.status = payload.status

    if payload.section_id is not None:
        section = db.get(CourseSection, payload.section_id)
        if not section or section.course_id != enrollment.course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section does not belong to this course or does not exist.",
            )
        enrollment.section_id = payload.section_id

    db.commit()
    db.refresh(enrollment)

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_UPDATE_ENROLMENT",
        resource_type="enrolment",
        resource_id=str(enrollment.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Admin updated enrolment {enrollment.id} (role: {enrollment.role}, status: {enrollment.status}, section: {enrollment.section_id}).",
    )
    return {
        "id": enrollment.id,
        "course_id": enrollment.course_id,
        "course_code": enrollment.course.code if enrollment.course else "",
        "course_title": enrollment.course.title if enrollment.course else "",
        "user_id": enrollment.user_id,
        "username": enrollment.user.username if enrollment.user else "",
        "full_name": enrollment.user.full_name if enrollment.user else "",
        "role": enrollment.role,
        "status": enrollment.status,
        "section_id": enrollment.section_id,
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


@router.get("/departments", response_model=List[DepartmentOut])
def admin_list_departments(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all academic departments (Administrator only)."""
    departments = db.scalars(select(Department).order_by(Department.id)).all()
    results = []
    for d in departments:
        results.append(
            DepartmentOut(
                id=d.id,
                code=d.code,
                name=d.name,
                description=d.description,
                head_id=d.head_id,
                head_name=d.head.full_name if d.head else None,
                created_at=d.created_at,
            )
        )
    return results


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def admin_create_department(
    payload: DepartmentCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new academic department (Administrator only)."""
    existing = db.scalar(select(Department).where(Department.code == payload.code))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with code {payload.code} already exists.",
        )

    if payload.head_id:
        head_user = db.get(User, payload.head_id)
        if not head_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department head user not found.")

    dept = Department(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        head_id=payload.head_id,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_CREATE_DEPARTMENT",
        resource_type="department",
        resource_id=str(dept.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"Created department {dept.code} - {dept.name}.",
    )
    return DepartmentOut(
        id=dept.id,
        code=dept.code,
        name=dept.name,
        description=dept.description,
        head_id=dept.head_id,
        head_name=dept.head.full_name if dept.head else None,
        created_at=dept.created_at,
    )


@router.get("/departments/{department_id}", response_model=DepartmentOut)
def admin_get_department(
    department_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get department details (Administrator only)."""
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    return DepartmentOut(
        id=dept.id,
        code=dept.code,
        name=dept.name,
        description=dept.description,
        head_id=dept.head_id,
        head_name=dept.head.full_name if dept.head else None,
        created_at=dept.created_at,
    )


@router.put("/departments/{department_id}", response_model=DepartmentOut)
def admin_update_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update department details (Administrator only)."""
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    if payload.code is not None:
        dept.code = payload.code
    if payload.name is not None:
        dept.name = payload.name
    if payload.description is not None:
        dept.description = payload.description
    if payload.head_id is not None:
        head_user = db.get(User, payload.head_id)
        if not head_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department head user not found.")
        dept.head_id = payload.head_id

    db.commit()
    db.refresh(dept)

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_UPDATE_DEPARTMENT",
        resource_type="department",
        resource_id=str(dept.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Updated department {dept.code}.",
    )
    return DepartmentOut(
        id=dept.id,
        code=dept.code,
        name=dept.name,
        description=dept.description,
        head_id=dept.head_id,
        head_name=dept.head.full_name if dept.head else None,
        created_at=dept.created_at,
    )


@router.delete("/departments/{department_id}")
def admin_delete_department(
    department_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a department (Administrator only)."""
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    db.delete(dept)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="ADMIN_DELETE_DEPARTMENT",
        resource_type="department",
        resource_id=str(department_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Deleted department {dept.code}.",
    )
    return {"message": "Department deleted successfully."}


@router.get("/courses", response_model=List[CourseOut])
def admin_list_courses(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all courses including archived ones (Administrator only)."""
    courses = db.scalars(select(Course).order_by(Course.id)).all()
    results = []
    for c in courses:
        student_count = db.scalar(
            select(func.count(Enrollment.id)).where(
                Enrollment.course_id == c.id,
                Enrollment.role == "student",
                Enrollment.status == "active",
            )
        ) or 0
        ta_enrollments = db.scalars(
            select(Enrollment).where(
                Enrollment.course_id == c.id,
                Enrollment.role == "ta",
                Enrollment.status == "active",
            )
        ).all()
        ta_names = [e.user.full_name for e in ta_enrollments if e.user]
        results.append(
            CourseOut(
                id=c.id,
                code=c.code,
                title=c.title,
                description=c.description,
                teacher_id=c.teacher_id,
                teacher_name=c.teacher.full_name if c.teacher else "Unassigned",
                student_count=student_count,
                current_user_role="admin",
                tas=ta_names,
                is_archived=getattr(c, "is_archived", False),
                created_at=c.created_at,
            )
        )
    return results
