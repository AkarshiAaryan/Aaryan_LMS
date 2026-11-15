from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, Enrollment, Assignment, Submission, Quiz, QuizAttempt
from ..schemas import GradeItem, StudentGradebookRow, PublishGradesRequest
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_publish_grades_access,
    get_user_course_role,
    log_activity,
)

router = APIRouter(tags=["Grades"])


def _build_gradebook(course_id: int, current_user: User, db: Session):
    course = verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    if course_role == "student":
        student_ids = [current_user.id]
    elif course_role in ["professor", "ta", "admin"]:
        enrollments = db.scalars(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.role == "student",
                Enrollment.status == "active",
            )
        ).all()
        student_ids = [e.user_id for e in enrollments]
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    assign_query = select(Assignment).where(
        Assignment.course_id == course_id,
        Assignment.is_archived == False,
    )
    quiz_query = select(Quiz).where(
        Quiz.course_id == course_id,
        Quiz.is_archived == False,
    )

    if course_role == "student":
        assign_query = assign_query.where(Assignment.is_published == True)
        quiz_query = quiz_query.where(Quiz.is_published == True)

    assignments = db.scalars(assign_query.order_by(Assignment.id)).all()
    quizzes = db.scalars(quiz_query.order_by(Quiz.id)).all()

    results: List[Dict[str, Any]] = []

    for sid in student_ids:
        student = db.get(User, sid)
        if not student:
            continue

        student_items: List[Dict[str, Any]] = []
        total_earned = 0
        total_possible = 0

        # Submissions
        for a in assignments:
            sub = db.scalar(
                select(Submission).where(
                    Submission.assignment_id == a.id,
                    Submission.student_id == sid,
                )
            )
            # If student is viewing, only show published grades
            score = None
            feedback = None
            if sub:
                if course_role in ["admin", "professor", "ta"] or sub.is_published:
                    score = sub.grade
                    feedback = sub.feedback

            status_text = sub.status if sub else "unsubmitted"
            if score is not None:
                total_earned += score
                total_possible += a.max_grade

            student_items.append(
                {
                    "submission_id": sub.id if sub else None,
                    "item_id": a.id,
                    "item_type": "assignment",
                    "title": a.title,
                    "score": score,
                    "max_score": a.max_grade,
                    "status": status_text,
                    "is_published": sub.is_published if sub else True,
                    "feedback": feedback,
                    "submitted_at": sub.submitted_at if sub else None,
                }
            )

        # Quizzes
        for q in quizzes:
            best_attempt = db.scalar(
                select(QuizAttempt)
                .where(QuizAttempt.quiz_id == q.id, QuizAttempt.student_id == sid)
                .order_by(QuizAttempt.score.desc().nullslast())
            )
            score = best_attempt.score if best_attempt else None
            status_text = best_attempt.status if best_attempt else "unattempted"
            if score is not None:
                total_earned += score
                total_possible += 100

            student_items.append(
                {
                    "submission_id": None,
                    "item_id": q.id,
                    "item_type": "quiz",
                    "title": q.title,
                    "score": score,
                    "max_score": 100,
                    "status": status_text,
                    "is_published": True,
                    "feedback": None,
                    "submitted_at": best_attempt.completed_at if best_attempt else None,
                }
            )

        percentage = round((total_earned / total_possible * 100), 1) if total_possible > 0 else 0.0

        results.append(
            {
                "id": student.id,
                "student_id": student.id,
                "student_name": student.full_name,
                "name": student.full_name,
                "username": student.username,
                "items": student_items,
                "grades": student_items,
                "total_score": total_earned,
                "max_total_score": total_possible,
                "percentage": percentage,
            }
        )

    return course, assignments, quizzes, results


@router.get("/grades/me")
def get_my_grades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve grades summary across all active enrolled courses for the current student."""
    enrollments = db.scalars(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.role == "student",
            Enrollment.status == "active",
        )
    ).all()

    response = []
    for enr in enrollments:
        course = enr.course
        if not course or course.is_archived:
            continue
        try:
            _, _, _, results = _build_gradebook(course.id, current_user, db)
            if results:
                response.append({
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_title": course.title,
                    "grade_data": results[0],
                })
        except Exception:
            continue

    return response


@router.get("/courses/{course_id}/grades")
@router.get("/grades/course/{course_id}")
def get_course_gradebook(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve course gradebook.
    - Students see ONLY their own row.
    - Staff (Professors and assigned TAs) see the full class gradebook.
    - TAs from other courses who are only students in this course see only their own row.
    """
    course, assignments, quizzes, results = _build_gradebook(course_id, current_user, db)

    log_activity(
        db=db,
        user=current_user,
        action="VIEW_GRADEBOOK",
        resource_type="gradebook",
        resource_id=str(course_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"User {current_user.username} viewed gradebook in course {course.code} (scope: {len(results)} rows).",
    )
    return {
        "course": {"id": course.id, "code": course.code, "title": course.title},
        "current_user_role": get_user_course_role(course_id, current_user, db),
        "assignments": [
            {"id": a.id, "title": a.title, "max_grade": a.max_grade}
            for a in assignments
        ],
        "quizzes": [
            {"id": q.id, "title": q.title, "max_attempts": q.max_attempts}
            for q in quizzes
        ],
        "students": results,
        "rows": results,
    }


@router.get("/courses/{course_id}/class-gradebook")
def get_class_wide_gradebook(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Staff-only class-wide gradebook endpoint.
    Explicitly denied to students.
    """
    course = verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    if course_role not in ["admin", "professor", "ta"]:
        log_activity(
            db=db,
            user=current_user,
            action="VIEW_CLASS_GRADEBOOK",
            resource_type="gradebook",
            resource_id=str(course_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {current_user.username} denied class-wide gradebook access in {course.code}.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: students cannot view class-wide gradebooks.",
        )

    _, _, _, results = _build_gradebook(course_id, current_user, db)
    return results


@router.get("/courses/{course_id}/students/{student_id}/grades")
def get_single_student_grade(
    course_id: int,
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve grades for a specific student.
    - Students can view only their own grade.
    - Viewing another student's grade is denied.
    """
    course = verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    if course_role == "student" and current_user.id != student_id:
        log_activity(
            db=db,
            user=current_user,
            action="VIEW_STUDENT_GRADE",
            resource_type="gradebook",
            resource_id=f"{course_id}/{student_id}",
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {current_user.username} attempted to view grades for student ID {student_id}.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: students can only view their own individual grades.",
        )

    _, _, _, results = _build_gradebook(course_id, current_user, db)
    for row in results:
        if row["student_id"] == student_id:
            return row

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student grades not found.")


@router.post("/courses/{course_id}/publish-grades")
def publish_course_grades(
    course_id: int,
    payload: PublishGradesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Publish final grades for a course.
    Allowed for Course Professor and Administrator.
    Forbidden for Teaching Assistants and Students.
    """
    course = verify_publish_grades_access(course_id, current_user, db)

    assignments = db.scalars(select(Assignment).where(Assignment.course_id == course_id)).all()
    for a in assignments:
        submissions = db.scalars(select(Submission).where(Submission.assignment_id == a.id)).all()
        for s in submissions:
            s.is_published = payload.is_published
            s.is_locked = True

    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="PUBLISH_GRADES",
        resource_type="gradebook",
        resource_id=str(course_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Published and locked final grades in course {course.code} by {current_user.username}.",
    )
    return {"message": f"Final grades published and locked for course {course.code}."}
