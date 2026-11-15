"""
Browser-context extraction and server-side validation layer.
Constructs authoritative LMSContext for AI Assistant interactions.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models import User, Course, Assignment, Submission, Quiz, QuizAttempt, LearningModule
from ..permissions import get_user_course_role
from ..clock import Clock


@dataclass
class LMSContext:
    page_type: str = "general"
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    resource_type: Optional[str] = None  # 'assignment', 'quiz', 'submission', 'gradebook', 'module', 'discussion', 'file'
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    assessment_status: str = "none"  # 'active', 'upcoming', 'closed', 'graded', 'none'
    deadline_status: str = "none"    # 'open', 'passed', 'extended', 'none'
    effective_role: str = "student"  # 'student', 'ta', 'professor', 'admin'
    is_answer_key_released: bool = False
    max_attempts: int = 1
    attempts_used: int = 0
    available_context: List[str] = field(default_factory=list)
    browser_snapshot_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_and_validate_context(
    user: User,
    db: Session,
    client_context: Optional[Dict[str, Any]] = None,
    browser_snapshot: Optional[str] = None,
) -> LMSContext:
    """
    Constructs an authoritative LMS context by combining client-reported state
    with server-side database truth and permissions. Never trusts client role claims.
    """
    raw = client_context or {}
    ctx = LMSContext()
    ctx.page_type = str(raw.get("page_type") or "general")
    if raw.get("assessment_status"):
        ctx.assessment_status = str(raw.get("assessment_status"))
    ctx.browser_snapshot_text = browser_snapshot or raw.get("browser_snapshot_text")

    # 1. Resolve Course and Effective Role
    course_id_raw = raw.get("course_id")
    course = None
    if course_id_raw:
        try:
            cid = int(course_id_raw)
            course = db.get(Course, cid)
            if not course:
                # Try finding course by code if passed
                course = db.scalar(select(Course).where(Course.code == str(course_id_raw)))
        except (ValueError, TypeError):
            course = db.scalar(select(Course).where(Course.code == str(course_id_raw)))

    if course:
        ctx.course_id = course.id
        ctx.course_code = course.code
        ctx.course_name = course.title
        effective_role = get_user_course_role(course.id, user, db) or user.role
        ctx.effective_role = effective_role
    else:
        ctx.effective_role = user.role

    now = Clock.now()

    # 2. Resolve Assessment Context (Assignment, Quiz, Submission)
    res_type = raw.get("resource_type")
    res_id_raw = raw.get("resource_id")
    res_id = None
    if res_id_raw is not None:
        try:
            res_id = int(res_id_raw)
        except (ValueError, TypeError):
            pass

    ctx.resource_type = res_type
    ctx.resource_id = res_id

    if res_type == "assignment" and res_id:
        assignment = db.get(Assignment, res_id)
        if assignment:
            ctx.resource_name = assignment.title
            ctx.course_id = assignment.course_id
            if not course:
                course = assignment.course
                ctx.course_code = course.code if course else None
                ctx.course_name = course.title if course else None
                ctx.effective_role = get_user_course_role(assignment.course_id, user, db) or user.role

            # Evaluate deadline status
            try:
                due_dt = Clock.parse_iso_datetime(assignment.due_date)
                if now <= due_dt:
                    ctx.deadline_status = "open"
                    ctx.assessment_status = "active"
                else:
                    ctx.deadline_status = "passed"
                    ctx.assessment_status = "closed"
            except Exception:
                ctx.deadline_status = "open"
                ctx.assessment_status = "active"

            # Check if student has a submission
            if ctx.effective_role == "student":
                sub = db.scalar(
                    select(Submission).where(
                        Submission.assignment_id == assignment.id,
                        Submission.student_id == user.id,
                    )
                )
                if sub and sub.status in ["graded", "submitted"]:
                    ctx.available_context.append(f"Submission status: {sub.status}")

    elif res_type == "quiz" and res_id:
        quiz = db.get(Quiz, res_id)
        if quiz:
            ctx.resource_name = quiz.title
            ctx.course_id = quiz.course_id
            ctx.max_attempts = quiz.max_attempts
            if not course:
                course = quiz.course
                ctx.course_code = course.code if course else None
                ctx.course_name = course.title if course else None
                ctx.effective_role = get_user_course_role(quiz.course_id, user, db) or user.role

            # Evaluate open/close window
            try:
                open_dt = Clock.parse_iso_datetime(quiz.open_date)
                close_dt = Clock.parse_iso_datetime(quiz.close_date)
                if now < open_dt:
                    ctx.assessment_status = "upcoming"
                    ctx.deadline_status = "none"
                elif now <= close_dt:
                    ctx.assessment_status = "active"
                    ctx.deadline_status = "open"
                else:
                    ctx.assessment_status = "closed"
                    ctx.deadline_status = "passed"
            except Exception:
                ctx.assessment_status = "active"
                ctx.deadline_status = "open"

            # Check answer release date
            try:
                rel_dt = Clock.parse_iso_datetime(quiz.answer_release_date)
                ctx.is_answer_key_released = (now >= rel_dt)
            except Exception:
                ctx.is_answer_key_released = False

            # Check student attempt count
            if ctx.effective_role == "student":
                attempts = db.scalars(
                    select(QuizAttempt).where(
                        QuizAttempt.quiz_id == quiz.id,
                        QuizAttempt.student_id == user.id,
                    )
                ).all()
                ctx.attempts_used = len(attempts)

    elif res_type == "module" and res_id:
        mod = db.get(LearningModule, res_id)
        if mod:
            ctx.resource_name = mod.title
            ctx.course_id = mod.course_id
            if mod.unlock_date:
                try:
                    unlock_dt = Clock.parse_iso_datetime(mod.unlock_date)
                    ctx.assessment_status = "active" if now >= unlock_dt else "upcoming"
                except Exception:
                    ctx.assessment_status = "active"
            else:
                ctx.assessment_status = "active"

    # 3. Augment with Browser Snapshot Insights
    if ctx.browser_snapshot_text:
        snapshot_lower = ctx.browser_snapshot_text.lower()
        if "active quiz" in snapshot_lower or "question 1 of" in snapshot_lower:
            ctx.page_type = "quiz_attempt"
            ctx.assessment_status = "active"
        elif "gradebook" in snapshot_lower:
            ctx.page_type = "gradebook"
        elif "submit assignment" in snapshot_lower:
            ctx.page_type = "assignment_detail"

    # Summary tags
    ctx.available_context.append(f"Effective Role: {ctx.effective_role}")
    if ctx.course_code:
        ctx.available_context.append(f"Course: {ctx.course_code}")
    if ctx.resource_name:
        ctx.available_context.append(f"Resource: {ctx.resource_name} ({ctx.resource_type})")
    ctx.available_context.append(f"Assessment Status: {ctx.assessment_status}")

    return ctx
