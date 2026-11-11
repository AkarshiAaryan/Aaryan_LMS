from typing import Optional
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .database import get_db
from .auth import get_current_user
from .clock import Clock, parse_iso_datetime
from .models import (
    User, Course, Enrollment, Group, GroupMember, Assignment, Submission, Quiz, QuizAttempt,
    Resource, ActivityLog
)


def utc_now() -> datetime:
    """Return current effective time from deterministic Clock."""
    return Clock.now()


def log_activity(
    db: Session,
    user: Optional[User],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    outcome: str = "ALLOW",
    http_status: int = 200,
    detail: str = "",
) -> None:
    """Helper to record audit log for research experiments."""
    try:
        log_entry = ActivityLog(
            user_id=user.id if user else None,
            username=user.username if user else "anonymous",
            role=user.role if user else "unknown",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            outcome=outcome,
            http_status=http_status,
            detail=detail,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()


# ===================== COURSE-SPECIFIC ROLE EVALUATION =====================

def get_user_course_role(course_id: int, user: User, db: Session) -> Optional[str]:
    """
    Determine the user's role specifically in the context of the requested course.
    Returns: 'admin', 'professor', 'ta', 'student', or None.
    Course role comes from course assignment/enrollment, NOT global label alone.
    """
    if user.role == "admin":
        return "admin"

    course = db.get(Course, course_id)
    if not course:
        return None

    # Check direct instructor designation
    if course.teacher_id == user.id:
        return "professor"

    # Check course enrollment/membership record
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user.id,
        )
    )
    if enrollment:
        role = enrollment.role.lower()
        if role in ["professor", "teacher"]:
            return "professor"
        return role

    return None


# ===================== BASE ROLE CHECKS =====================

def require_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure request is from an authenticated active user."""
    return current_user


def require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Ensure user is an institutional administrator."""
    if current_user.role != "admin":
        log_activity(
            db=db,
            user=current_user,
            action="ADMIN_ACCESS",
            resource_type="admin",
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} with role '{current_user.role}' denied administrator operation.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: institutional administrator privileges required.",
        )
    return current_user


# ===================== RESOURCE ACCESS GUARDS =====================

def verify_course_access(course_id: int, user: User, db: Session) -> Course:
    """Verify that user is authorized to access course (Admin, Professor, TA, or Student)."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} does not exist.",
        )

    course_role = get_user_course_role(course_id, user, db)
    if course_role in ["admin", "professor", "ta", "student"]:
        return course

    log_activity(
        db=db,
        user=user,
        action="VIEW_COURSE",
        resource_type="course",
        resource_id=str(course_id),
        outcome="BLOCK",
        http_status=status.HTTP_403_FORBIDDEN,
        detail=f"User {user.username} denied access to course {course.code} (no membership).",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: you do not have permission to access this course.",
    )


def verify_course_professor_or_admin(course_id: int, user: User, db: Session) -> Course:
    """
    Verify that user is the assigned professor for this course or an admin.
    TAs, students, and professors of OTHER courses are denied.
    """
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} does not exist.",
        )

    course_role = get_user_course_role(course_id, user, db)
    if course_role in ["admin", "professor"]:
        return course

    log_activity(
        db=db,
        user=user,
        action="MANAGE_COURSE",
        resource_type="course",
        resource_id=str(course_id),
        outcome="BLOCK",
        http_status=status.HTTP_403_FORBIDDEN,
        detail=f"User {user.username} (course role: {course_role}) denied professor/admin management for {course.code}.",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: only the assigned course professor or site administrator may manage this course.",
    )


def verify_course_staff(course_id: int, user: User, db: Session) -> Course:
    """Verify that user is course staff (Admin, assigned Professor, or assigned TA)."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} does not exist.",
        )

    course_role = get_user_course_role(course_id, user, db)
    if course_role in ["admin", "professor", "ta"]:
        return course

    log_activity(
        db=db,
        user=user,
        action="COURSE_STAFF_ACTION",
        resource_type="course",
        resource_id=str(course_id),
        outcome="BLOCK",
        http_status=status.HTTP_403_FORBIDDEN,
        detail=f"User {user.username} (course role: {course_role}) denied staff action for {course.code}.",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: only course staff (professors and assigned TAs) may perform this action.",
    )


def verify_course_student_enrollment(course_id: int, user: User, db: Session) -> Course:
    """Verify that user is enrolled as a student in this specific course."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    course_role = get_user_course_role(course_id, user, db)
    if course_role == "student":
        return course

    log_activity(
        db=db,
        user=user,
        action="SUBMIT_COURSE_WORK",
        resource_type="course",
        resource_id=str(course_id),
        outcome="BLOCK",
        http_status=status.HTTP_403_FORBIDDEN,
        detail=f"User {user.username} is not enrolled as a student in {course.code} (role: {course_role}).",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: you must be enrolled as a student in this course to submit work.",
    )


def verify_resource_access(resource: Resource, user: User, db: Session) -> Resource:
    """Verify access to course resource. Enforces visibility and staff-only boundaries."""
    verify_course_access(resource.course_id, user, db)
    course_role = get_user_course_role(resource.course_id, user, db)

    # 1. Staff-only protection
    if resource.is_staff_only and course_role not in ["admin", "professor", "ta"]:
        log_activity(
            db=db,
            user=user,
            action="VIEW_STAFF_RESOURCE",
            resource_type="resource",
            resource_id=str(resource.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} attempted to view staff-only resource '{resource.title}'.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this resource is restricted to course staff.",
        )

    # 2. Unpublished / hidden resource protection for students
    if not resource.is_visible and course_role not in ["admin", "professor", "ta"]:
        log_activity(
            db=db,
            user=user,
            action="VIEW_UNPUBLISHED_RESOURCE",
            resource_type="resource",
            resource_id=str(resource.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} attempted to view unpublished/hidden resource '{resource.title}'.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this resource is currently unpublished or hidden.",
        )

    return resource


def verify_submission_access(submission: Submission, user: User, db: Session) -> Submission:
    """
    Verify access to view a submission.
    - Admin: can view all submissions.
    - Professor / TA in this course: can view all submissions in this course.
    - Student: can view only own submission, or submissions for their assigned group.
    """
    assignment = submission.assignment
    course_id = assignment.course_id if assignment else None
    if not course_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    course_role = get_user_course_role(course_id, user, db)

    # 1. Staff access
    if course_role in ["admin", "professor", "ta"]:
        return submission

    # 2. Student access
    if course_role == "student":
        # Own individual submission
        if submission.student_id == user.id:
            return submission

        # Group submission check
        if submission.group_id:
            grp = db.get(Group, submission.group_id)
            if grp and grp.course_id == course_id:
                is_group_member = db.scalar(
                    select(GroupMember).where(
                        GroupMember.group_id == submission.group_id,
                        GroupMember.user_id == user.id,
                    )
                )
                if is_group_member:
                    return submission

        log_activity(
            db=db,
            user=user,
            action="VIEW_SUBMISSION",
            resource_type="submission",
            resource_id=str(submission.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} attempted to view another student's or group's submission (ID: {submission.id}).",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: students can only view their own individual or group submissions.",
        )

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def verify_submission_edit(submission: Submission, user: User, db: Session) -> None:
    """
    Verify that student is allowed to edit/submit work:
    - Actively enrolled as a student in this course.
    - Own submission or legitimate group member in this course.
    - Not locked.
    - Before deadline (unless extension is granted).
    """
    assignment = submission.assignment
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    # 1. Enforce active student role in this specific course
    course_role = get_user_course_role(assignment.course_id, user, db)
    if course_role != "student":
        log_activity(
            db=db,
            user=user,
            action="EDIT_SUBMISSION",
            resource_type="submission",
            resource_id=str(submission.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {user.username} (course role: {course_role}) is not enrolled as a student in course {assignment.course_id}.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you must be actively enrolled as a student in this course to edit submissions.",
        )

    # 2. Lock check
    if submission.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this submission is locked and cannot be edited.",
        )

    # 3. Ownership and group boundary check
    if submission.group_id:
        grp = db.get(Group, submission.group_id)
        if not grp or grp.course_id != assignment.course_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: invalid group association for this course assignment.",
            )
        is_member = db.scalar(
            select(GroupMember).where(
                GroupMember.group_id == submission.group_id,
                GroupMember.user_id == user.id,
            )
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you are not a member of this submission's group.",
            )
    else:
        if submission.student_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot edit another student's submission.",
            )

    # 4. Deadline check
    due_dt = parse_iso_datetime(assignment.due_date)
    now = utc_now()
    if now > due_dt and not submission.extension_granted:
        log_activity(
            db=db,
            user=user,
            action="EDIT_PAST_DEADLINE",
            resource_type="submission",
            resource_id=str(submission.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} attempted to edit submission after deadline {assignment.due_date} without extension.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: submission deadline has passed and no extension was granted.",
        )


def verify_submission_grading_access(submission: Submission, user: User, db: Session) -> Submission:
    """Verify permission to grade a submission (Assigned Professor, assigned TA, or Admin)."""
    assignment = submission.assignment
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    course_role = get_user_course_role(assignment.course_id, user, db)
    if course_role in ["admin", "professor", "ta"]:
        if submission.is_locked and course_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: grades for this submission are locked and require administrator approval to modify.",
            )
        return submission

    log_activity(
        db=db,
        user=user,
        action="GRADE_SUBMISSION",
        resource_type="submission",
        resource_id=str(submission.id),
        outcome="BLOCK",
        http_status=status.HTTP_403_FORBIDDEN,
        detail=f"User {user.username} (course role: {course_role}) denied grading access in course {assignment.course_id}.",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: only assigned professors and teaching assistants may grade submissions in this course.",
    )


def verify_publish_grades_access(course_id: int, user: User, db: Session) -> Course:
    """
    Verify permission to publish final grades.
    Only professors of that course and site administrators may publish.
    Teaching Assistants are explicitly forbidden from publishing final grades.
    """
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    course_role = get_user_course_role(course_id, user, db)
    if course_role in ["admin", "professor"]:
        return course

    if course_role == "ta":
        log_activity(
            db=db,
            user=user,
            action="PUBLISH_GRADES",
            resource_type="gradebook",
            resource_id=str(course_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"TA {user.username} attempted to publish final grades in course {course.code}.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Teaching Assistants cannot publish final grades.",
        )

    log_activity(
        db=db,
        user=user,
        action="PUBLISH_GRADES",
        resource_type="gradebook",
        resource_id=str(course_id),
        outcome="BLOCK",
        http_status=status.HTTP_403_FORBIDDEN,
        detail=f"User {user.username} denied final grade publishing permission for {course.code}.",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: only the assigned course professor or site administrator can publish final grades.",
    )


def verify_quiz_start(quiz: Quiz, user: User, db: Session) -> None:
    """Verify that a student can start a quiz attempt (enrolled student, published, window open, quota remains)."""
    course_role = get_user_course_role(quiz.course_id, user, db)
    if not course_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you are not enrolled in this course.",
        )

    if course_role != "student":
        log_activity(
            db=db,
            user=user,
            action="START_QUIZ",
            resource_type="quiz",
            resource_id=str(quiz.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {user.username} (course role: {course_role}) attempted to initiate a student quiz attempt.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only enrolled students may initiate student quiz attempts.",
        )

    if not quiz.is_published:
        log_activity(
            db=db,
            user=user,
            action="START_QUIZ",
            resource_type="quiz",
            resource_id=str(quiz.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} attempted to start unpublished quiz '{quiz.title}'.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: quiz is not published.",
        )

    now = utc_now()
    open_dt = parse_iso_datetime(quiz.open_date)
    close_dt = parse_iso_datetime(quiz.close_date)

    if now < open_dt:
        log_activity(
            db=db,
            user=user,
            action="START_QUIZ",
            resource_type="quiz",
            resource_id=str(quiz.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {user.username} attempted to start quiz '{quiz.title}' before opening time ({quiz.open_date}).",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: quiz is not yet open for attempts.",
        )

    if now > close_dt:
        log_activity(
            db=db,
            user=user,
            action="START_QUIZ",
            resource_type="quiz",
            resource_id=str(quiz.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {user.username} attempted to start quiz '{quiz.title}' after closing time ({quiz.close_date}).",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: quiz availability window has closed.",
        )

    attempts_count = db.scalar(
        select(func.count(QuizAttempt.id)).where(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.student_id == user.id,
        )
    ) or 0

    if attempts_count >= quiz.max_attempts:
        log_activity(
            db=db,
            user=user,
            action="START_QUIZ",
            resource_type="quiz",
            resource_id=str(quiz.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {user.username} reached max attempt limit ({quiz.max_attempts}) for quiz '{quiz.title}'.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: maximum quiz attempt limit ({quiz.max_attempts}) reached.",
        )


def verify_quiz_answer_key_access(quiz: Quiz, user: User, db: Session) -> None:
    """Verify access to view quiz answers or answer key."""
    course_role = get_user_course_role(quiz.course_id, user, db)
    if course_role in ["admin", "professor", "ta"]:
        return

    if course_role == "student":
        now = utc_now()
        release_dt = parse_iso_datetime(quiz.answer_release_date)
        if now < release_dt:
            log_activity(
                db=db,
                user=user,
                action="VIEW_QUIZ_ANSWERS",
                resource_type="quiz",
                resource_id=str(quiz.id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {user.username} attempted to view answer key for quiz '{quiz.title}' before release ({quiz.answer_release_date}).",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: quiz answer key has not been released yet.",
            )
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
