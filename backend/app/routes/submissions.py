from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, Assignment, Submission, GradeHistory, Group, GroupMember
from ..schemas import SubmissionOut, SubmissionCreate, SubmissionGrade, GradeHistoryOut
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_staff,
    verify_course_student_enrollment,
    verify_submission_access,
    verify_submission_edit,
    verify_submission_grading_access,
    get_user_course_role,
    parse_iso_datetime,
    utc_now,
    log_activity,
)
from ..clock import Clock

router = APIRouter(tags=["Submissions"])


def serialize_submission(
    submission: Submission,
    requesting_user: Optional[User] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    assignment = submission.assignment
    course = assignment.course if assignment else None
    course_id = course.id if course else (assignment.course_id if assignment else None)

    # Check if requesting user is authorized staff/admin
    is_staff = False
    if requesting_user and db and course_id:
        course_role = get_user_course_role(course_id, requesting_user, db)
        is_staff = course_role in ["admin", "professor", "ta"]

    show_grading = bool(submission.is_published or is_staff)

    grade_val = submission.grade if show_grading else None
    feedback_val = submission.feedback if show_grading else None
    graded_by_id_val = submission.graded_by_id if show_grading else None
    graded_by_name_val = (
        (submission.graded_by.full_name if submission.graded_by else None)
        if show_grading
        else None
    )
    graded_at_val = submission.graded_at if show_grading else None

    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": assignment.title if assignment else "",
        "course_id": course.id if course else None,
        "course_code": course.code if course else "",
        "student_id": submission.student_id,
        "student_name": submission.student.full_name if submission.student else f"Student #{submission.student_id}",
        "group_id": submission.group_id,
        "group_name": submission.group.name if submission.group else None,
        "content": submission.content,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
        "is_draft": submission.is_draft,
        "extension_granted": submission.extension_granted,
        "is_published": submission.is_published,
        "is_locked": submission.is_locked,
        "grade": grade_val,
        "max_grade": assignment.max_grade if assignment else 100,
        "feedback": feedback_val,
        "graded_by_id": graded_by_id_val,
        "graded_by_name": graded_by_name_val,
        "graded_at": graded_at_val,
    }


@router.get("/assignments/{assignment_id}/submissions", response_model=List[SubmissionOut])
def list_assignment_submissions(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all student submissions for an assignment (Assigned Professor, assigned TA, or Admin only)."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with ID {assignment_id} not found.",
        )

    # Enforce staff access (Professor or assigned TA in this course, or Admin)
    verify_course_staff(assignment.course_id, current_user, db)

    submissions = db.scalars(
        select(Submission).where(Submission.assignment_id == assignment_id).order_by(Submission.id)
    ).all()

    return [serialize_submission(s, current_user, db) for s in submissions]


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission_by_id(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve an individual submission. Enforces student ownership and course staff boundary."""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    verify_submission_access(submission, current_user, db)
    return serialize_submission(submission, current_user, db)


@router.post("/assignments/{assignment_id}/submit", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def submit_assignment(
    assignment_id: int,
    payload: SubmissionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit or save draft assignment response. Enforces student enrollment, deadlines, and group boundaries."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with ID {assignment_id} not found.",
        )

    # Only enrolled active students in this course may submit
    verify_course_student_enrollment(assignment.course_id, current_user, db)

    now = Clock.now(request)
    due_dt = parse_iso_datetime(assignment.due_date)

    # Validate group scoping if payload specifies group_id
    if payload.group_id is not None:
        grp = db.get(Group, payload.group_id)
        if not grp or grp.course_id != assignment.course_id:
            log_activity(
                db=db,
                user=current_user,
                action="SUBMIT_COURSE_WORK",
                resource_type="submission",
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {current_user.username} supplied cross-course or invalid group {payload.group_id} for assignment {assignment_id}.",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: invalid group association for this course assignment.",
            )

    if not assignment.is_group:
        # Individual assignment: client group_id must be null
        if payload.group_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group ID cannot be specified for individual assignments.",
            )
        group_id = None
        submission = db.scalar(
            select(Submission).where(
                Submission.assignment_id == assignment_id,
                Submission.student_id == current_user.id,
            )
        )
    else:
        # Group assignment: student must belong to active group in this course
        gm = db.scalar(
            select(GroupMember)
            .join(Group, GroupMember.group_id == Group.id)
            .where(
                GroupMember.user_id == current_user.id,
                Group.course_id == assignment.course_id,
            )
        )
        if not gm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you must belong to an approved project group in this course to submit group assignments.",
            )
        group_id = gm.group_id
        if payload.group_id is not None and payload.group_id != group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot submit for a group you do not belong to.",
            )

        # Single canonical submission per assignment and group
        submission = db.scalar(
            select(Submission).where(
                Submission.assignment_id == assignment_id,
                Submission.group_id == group_id,
            )
        )

    if submission:
        verify_submission_edit(submission, current_user, db)
        submission.content = payload.content
        submission.submitted_at = now
        submission.is_draft = payload.is_draft
        submission.status = "draft" if payload.is_draft else "submitted"
    else:
        # Check deadline for initial submission
        if now > due_dt and not assignment.allow_late:
            log_activity(
                db=db,
                user=current_user,
                action="SUBMIT_PAST_DEADLINE",
                resource_type="submission",
                resource_id=str(assignment_id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {current_user.username} attempted submission past deadline ({assignment.due_date}).",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: submission deadline has passed and no extension was granted.",
            )

        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            group_id=group_id,
            content=payload.content,
            is_draft=payload.is_draft,
            status="draft" if payload.is_draft else "submitted",
            submitted_at=now,
        )
        db.add(submission)

    db.commit()
    db.refresh(submission)

    log_activity(
        db=db,
        user=current_user,
        action="SUBMIT_WORK",
        resource_type="submission",
        resource_id=str(submission.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"Student submitted work for assignment '{assignment.title}' (draft={submission.is_draft}).",
    )
    return serialize_submission(submission, current_user, db)


@router.put("/submissions/{submission_id}", response_model=SubmissionOut)
def edit_submission(
    submission_id: int,
    payload: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit own submission before deadline (or with extension)."""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    verify_submission_edit(submission, current_user, db)

    submission.content = payload.content
    submission.is_draft = payload.is_draft
    submission.status = "draft" if payload.is_draft else "submitted"
    submission.submitted_at = utc_now()

    db.commit()
    db.refresh(submission)

    log_activity(
        db=db,
        user=current_user,
        action="EDIT_SUBMISSION",
        resource_type="submission",
        resource_id=str(submission.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Student {current_user.username} edited submission ID {submission.id}.",
    )
    return serialize_submission(submission, current_user, db)


@router.put("/grades/{submission_id}", response_model=SubmissionOut)
@router.put("/submissions/{submission_id}/grade", response_model=SubmissionOut)
@router.post("/submissions/{submission_id}/grade", response_model=SubmissionOut)
def grade_submission(
    submission_id: int,
    payload: SubmissionGrade,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Grade a submission (Assigned Professor, assigned TA, or Admin).
    Records grade change history with previous/new mark, editor, and timestamp.
    Accepts both canonical POST /submissions/{id}/grade and frontend PUT /grades/{id}.
    """
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    # Verify grading permission
    verify_submission_grading_access(submission, current_user, db)

    # Validate against assignment max_grade
    max_grade = submission.assignment.max_grade if submission.assignment else 100
    if payload.grade < 0 or payload.grade > max_grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Grade must be between 0 and {max_grade}.",
        )

    previous_grade = submission.grade

    submission.grade = payload.grade
    if payload.feedback is not None:
        submission.feedback = payload.feedback
    if payload.is_published is not None:
        submission.is_published = payload.is_published
    submission.status = "graded"
    submission.graded_by_id = current_user.id
    submission.graded_at = utc_now()

    # Record grade history audit
    history_entry = GradeHistory(
        submission_id=submission.id,
        course_id=submission.assignment.course_id,
        student_id=submission.student_id,
        previous_grade=previous_grade,
        new_grade=payload.grade,
        changed_by_id=current_user.id,
        changed_at=utc_now(),
        reason=payload.reason or "Evaluation mark update",
    )
    db.add(history_entry)

    db.commit()
    db.refresh(submission)

    log_activity(
        db=db,
        user=current_user,
        action="GRADE_SUBMISSION",
        resource_type="submission",
        resource_id=str(submission.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"User {current_user.username} graded submission ID {submission.id}: {previous_grade} -> {payload.grade}.",
    )
    return serialize_submission(submission, current_user, db)


@router.get("/submissions/{submission_id}/history", response_model=List[GradeHistoryOut])
def get_submission_grade_history(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit trail of grade changes for a submission (Course staff or Admin only)."""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    verify_course_staff(submission.assignment.course_id, current_user, db)

    history = db.scalars(
        select(GradeHistory).where(GradeHistory.submission_id == submission_id).order_by(GradeHistory.changed_at.desc())
    ).all()

    return [
        GradeHistoryOut(
            id=h.id,
            submission_id=h.submission_id,
            course_id=h.course_id,
            student_id=h.student_id,
            previous_grade=h.previous_grade,
            new_grade=h.new_grade,
            changed_by_id=h.changed_by_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else "System",
            changed_at=h.changed_at,
            reason=h.reason,
        )
        for h in history
    ]
