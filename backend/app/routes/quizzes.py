import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..database import get_db
from ..models import User, Course, Quiz, QuizQuestion, QuizAttempt, QuizAnswer
from ..schemas import (
    QuizOut, QuizQuestionOut, QuizAttemptOut, QuizSubmitRequest
)
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_professor_or_admin,
    verify_course_student_enrollment,
    verify_quiz_start,
    verify_quiz_answer_key_access,
    get_user_course_role,
    log_activity,
)

router = APIRouter(tags=["Quizzes"])


def serialize_quiz(quiz: Quiz, current_user: User, db: Session) -> Dict[str, Any]:
    question_count = db.scalar(
        select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == quiz.id)
    ) or 0

    my_attempts_count = 0
    attempts_remaining = quiz.max_attempts
    role = get_user_course_role(quiz.course_id, current_user, db)

    if role == "student":
        my_attempts_count = db.scalar(
            select(func.count(QuizAttempt.id)).where(
                QuizAttempt.quiz_id == quiz.id,
                QuizAttempt.student_id == current_user.id,
            )
        ) or 0
        attempts_remaining = max(0, quiz.max_attempts - my_attempts_count)

    questions_out = []
    for q in quiz.questions:
        try:
            opts = json.loads(q.options_json)
        except Exception:
            opts = []
        questions_out.append(
            {
                "id": q.id,
                "quiz_id": q.quiz_id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": opts,
                "points": q.points,
            }
        )

    return {
        "id": quiz.id,
        "course_id": quiz.course_id,
        "course_code": quiz.course.code if quiz.course else "",
        "title": quiz.title,
        "description": quiz.description,
        "open_date": quiz.open_date,
        "close_date": quiz.close_date,
        "answer_release_date": quiz.answer_release_date,
        "time_limit_minutes": quiz.time_limit_minutes,
        "max_attempts": quiz.max_attempts,
        "is_published": quiz.is_published,
        "created_at": quiz.created_at,
        "question_count": question_count,
        "my_attempts_count": my_attempts_count,
        "attempts_remaining": attempts_remaining,
        "questions": questions_out,
    }


def serialize_attempt(attempt: QuizAttempt) -> Dict[str, Any]:
    quiz = attempt.quiz
    return {
        "id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "quiz_title": quiz.title if quiz else "",
        "course_code": quiz.course.code if quiz and quiz.course else "",
        "student_id": attempt.student_id,
        "student_name": attempt.student.full_name if attempt.student else f"Student #{attempt.student_id}",
        "attempt_number": attempt.attempt_number,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "score": attempt.score,
        "max_score": 100,
        "status": attempt.status,
    }


@router.get("/courses/{course_id}/quizzes", response_model=List[QuizOut])
def list_course_quizzes(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve quizzes for a course. Students see published quizzes only."""
    verify_course_access(course_id, current_user, db)
    role = get_user_course_role(course_id, current_user, db)

    stmt = select(Quiz).where(Quiz.course_id == course_id).order_by(Quiz.id)
    if role == "student":
        stmt = stmt.where(Quiz.is_published == True)

    quizzes = db.scalars(stmt).all()
    return [serialize_quiz(q, current_user, db) for a in quizzes for q in [a]]


@router.get("/quizzes/{quiz_id}", response_model=QuizOut)
def get_quiz_by_id(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a quiz and its questions. Restricts unpublished quizzes from students."""
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    verify_course_access(quiz.course_id, current_user, db)
    role = get_user_course_role(quiz.course_id, current_user, db)
    if role == "student" and not quiz.is_published:
        log_activity(
            db=db,
            user=current_user,
            action="VIEW_QUIZ",
            resource_type="quiz",
            resource_id=str(quiz.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {current_user.username} denied access to unpublished quiz '{quiz.title}'.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this quiz has not been published yet.",
        )

    return serialize_quiz(quiz, current_user, db)


@router.get("/quizzes/{quiz_id}/attempts", response_model=List[QuizAttemptOut])
def get_quiz_attempts(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve attempts for a quiz."""
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    verify_course_access(quiz.course_id, current_user, db)
    role = get_user_course_role(quiz.course_id, current_user, db)
    if role == "student":
        attempts = db.scalars(
            select(QuizAttempt).where(
                QuizAttempt.quiz_id == quiz.id,
                QuizAttempt.student_id == current_user.id
            ).order_by(QuizAttempt.attempt_number)
        ).all()
    else:
        attempts = db.scalars(
            select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id).order_by(QuizAttempt.attempt_number)
        ).all()
    return [serialize_attempt(a) for a in attempts]


@router.post("/quizzes/{quiz_id}/attempts", response_model=QuizAttemptOut, status_code=status.HTTP_201_CREATED)
@router.post("/quizzes/{quiz_id}/start", response_model=QuizAttemptOut, status_code=status.HTTP_201_CREATED)
def start_quiz_attempt(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a quiz attempt. Enforces opening window and attempt limits."""
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    verify_quiz_start(quiz, current_user, db)

    past_attempts = db.scalar(
        select(func.count(QuizAttempt.id)).where(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.student_id == current_user.id,
        )
    ) or 0

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=current_user.id,
        attempt_number=past_attempts + 1,
        started_at=datetime.now(timezone.utc),
        status="in_progress",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    log_activity(
        db=db,
        user=current_user,
        action="START_QUIZ_ATTEMPT",
        resource_type="quiz",
        resource_id=str(quiz.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"User {current_user.username} started attempt #{attempt.attempt_number} on quiz '{quiz.title}'.",
    )
    return serialize_attempt(attempt)


@router.get("/quizzes/{quiz_id}/answer-key")
def get_quiz_answer_key(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve quiz answer key.
    Enforces answer release date restriction for students.
    Staff and Admin may always view answer key.
    """
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    verify_quiz_answer_key_access(quiz, current_user, db)

    questions_answers = [
        {
            "question_id": q.id,
            "question_text": q.question_text,
            "correct_answer": q.correct_answer,
            "points": q.points,
        }
        for q in quiz.questions
    ]

    log_activity(
        db=db,
        user=current_user,
        action="VIEW_QUIZ_ANSWERS",
        resource_type="quiz",
        resource_id=str(quiz.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"User {current_user.username} viewed answer key for quiz '{quiz.title}'.",
    )
    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "answer_release_date": quiz.answer_release_date,
        "answers": questions_answers,
    }


@router.post("/quizzes/attempts/{attempt_id}/submit", response_model=QuizAttemptOut)
def submit_quiz_attempt(
    attempt_id: int,
    payload: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit responses for a quiz attempt and calculate score."""
    attempt = db.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found.")

    if attempt.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    quiz = attempt.quiz
    total_earned = 0
    total_possible = 0

    for ans in payload.answers:
        q = db.get(QuizQuestion, ans.question_id)
        if not q or q.quiz_id != quiz.id:
            continue
        total_possible += q.points
        is_corr = (ans.selected_option.strip() == q.correct_answer.strip())
        pts = q.points if is_corr else 0
        if is_corr:
            total_earned += pts

        answer_record = QuizAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            selected_option=ans.selected_option,
            is_correct=is_corr,
            points_awarded=pts,
        )
        db.add(answer_record)

    percentage = int((total_earned / total_possible * 100)) if total_possible > 0 else 100
    attempt.score = percentage
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.status = "finished"

    db.commit()
    db.refresh(attempt)

    log_activity(
        db=db,
        user=current_user,
        action="SUBMIT_QUIZ_ATTEMPT",
        resource_type="quiz",
        resource_id=str(quiz.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"User {current_user.username} submitted quiz '{quiz.title}' with score {attempt.score}%.",
    )
    return serialize_attempt(attempt)
