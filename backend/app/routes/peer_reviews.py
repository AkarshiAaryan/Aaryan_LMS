from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, Assignment, Submission, PeerReview, GradeAppeal, GradeHistory, Enrollment
from ..schemas import (
    PeerReviewOut, PeerReviewSubmit, PeerReviewAssign, GradeAppealOut, GradeAppealCreate, GradeAppealResolve
)
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_staff,
    get_user_course_role,
    log_activity,
)
from ..clock import Clock

router = APIRouter(tags=["Peer Reviews & Appeals"])


def serialize_peer_review(review: PeerReview, redact_reviewer: bool = False) -> Dict[str, Any]:
    return {
        "id": review.id,
        "submission_id": review.submission_id,
        "assignment_title": review.submission.assignment.title if (review.submission and review.submission.assignment) else None,
        "reviewer_id": None if redact_reviewer else review.reviewer_id,
        "reviewer_name": "Anonymous Reviewer" if redact_reviewer else (review.reviewer.full_name if review.reviewer else "Unknown"),
        "is_anonymous": review.is_anonymous,
        "review_text": review.review_text,
        "score": review.score,
        "status": review.status,
        "deadline": review.deadline or "",
        "created_at": review.created_at,
    }


def serialize_grade_appeal(appeal: GradeAppeal) -> Dict[str, Any]:
    return {
        "id": appeal.id,
        "submission_id": appeal.submission_id,
        "assignment_title": appeal.submission.assignment.title if (appeal.submission and appeal.submission.assignment) else None,
        "student_id": appeal.student_id,
        "student_name": appeal.student.full_name if appeal.student else "Student",
        "reason": appeal.reason,
        "status": appeal.status,
        "reviewer_id": appeal.reviewer_id,
        "reviewer_name": appeal.reviewer.full_name if appeal.reviewer else None,
        "resolution_notes": appeal.resolution_notes or "",
        "created_at": appeal.created_at,
    }


# ===================== PEER REVIEWS =====================

@router.post("/assignments/{assignment_id}/peer-reviews/assign", response_model=PeerReviewOut, status_code=status.HTTP_201_CREATED)
def assign_peer_review(
    assignment_id: int,
    payload: PeerReviewAssign,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign a peer review to a student. Course staff only."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    verify_course_staff(assignment.course_id, current_user, db)

    submission = db.get(Submission, payload.submission_id)
    if not submission or submission.assignment_id != assignment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission does not belong to this assignment.")

    # Self-review prevention
    if submission.student_id == payload.reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-review is not permitted: reviewer cannot be the submission author.",
        )

    # Reviewer enrollment check
    reviewer_enr = db.scalar(
        select(Enrollment).where(
            Enrollment.course_id == assignment.course_id,
            Enrollment.user_id == payload.reviewer_id,
            Enrollment.status == "active",
        )
    )
    if not reviewer_enr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewer is not actively enrolled in this course.",
        )

    # Duplicate check
    existing = db.scalar(
        select(PeerReview).where(
            PeerReview.submission_id == payload.submission_id,
            PeerReview.reviewer_id == payload.reviewer_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewer is already assigned to this submission.",
        )

    review = PeerReview(
        submission_id=payload.submission_id,
        reviewer_id=payload.reviewer_id,
        is_anonymous=payload.is_anonymous,
        deadline=payload.deadline,
        status="assigned",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    log_activity(
        db=db,
        user=current_user,
        action="ASSIGN_PEER_REVIEW",
        resource_type="peer_review",
        resource_id=str(review.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"Staff {current_user.username} assigned user #{payload.reviewer_id} to review submission #{payload.submission_id}.",
    )
    return serialize_peer_review(review, redact_reviewer=False)


@router.get("/peer-reviews/assigned", response_model=List[PeerReviewOut])
def list_assigned_peer_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List peer reviews assigned to the current user."""
    reviews = db.scalars(
        select(PeerReview).where(PeerReview.reviewer_id == current_user.id)
    ).all()
    return [serialize_peer_review(r, redact_reviewer=False) for r in reviews]


@router.get("/peer-reviews/{review_id}", response_model=PeerReviewOut)
def get_peer_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get peer review details. Enforces double-blind anonymity for author."""
    review = db.get(PeerReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Peer review not found.")

    submission = review.submission
    assignment = submission.assignment
    course_role = get_user_course_role(assignment.course_id, current_user, db)

    is_staff = course_role in ["admin", "professor", "ta"]
    is_reviewer = review.reviewer_id == current_user.id
    is_author = submission.student_id == current_user.id

    if not (is_staff or is_reviewer or is_author):
        log_activity(
            db=db,
            user=current_user,
            action="VIEW_PEER_REVIEW",
            resource_type="peer_review",
            resource_id=str(review_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} denied access to peer review #{review_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: you are not authorized to view this peer review.")

    # If the author is viewing, the review must be submitted/moderated, and anonymity is enforced
    if is_author and not is_staff and not is_reviewer:
        if review.status == "assigned":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Peer review is still in progress by the reviewer.")
        redact = review.is_anonymous
        return serialize_peer_review(review, redact_reviewer=redact)

    return serialize_peer_review(review, redact_reviewer=False)


@router.put("/peer-reviews/{review_id}", response_model=PeerReviewOut)
def submit_peer_review(
    review_id: int,
    review_data: PeerReviewSubmit,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit or edit a peer review. Checks assigned reviewer and deadline."""
    review = db.get(PeerReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Peer review not found.")

    submission = review.submission
    assignment = submission.assignment
    course_role = get_user_course_role(assignment.course_id, current_user, db)

    is_staff = course_role in ["admin", "professor", "ta"]
    is_reviewer = review.reviewer_id == current_user.id

    if not (is_staff or is_reviewer):
        log_activity(
            db=db,
            user=current_user,
            action="SUBMIT_PEER_REVIEW",
            resource_type="peer_review",
            resource_id=str(review_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} unauthorized to submit peer review #{review_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: you are not assigned as reviewer for this submission.")

    if not is_staff:
        # Check if already moderated
        if review.status == "moderated":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This peer review has already been moderated and finalized by staff.")

        # Check deadline
        if review.deadline:
            try:
                deadline_dt = Clock.parse_iso_datetime(review.deadline)
                if Clock.get_time(request) > deadline_dt:
                    log_activity(
                        db=db,
                        user=current_user,
                        action="SUBMIT_PEER_REVIEW",
                        resource_type="peer_review",
                        resource_id=str(review_id),
                        outcome="BLOCK",
                        http_status=status.HTTP_403_FORBIDDEN,
                        detail=f"Reviewer {current_user.username} missed deadline {review.deadline} for review #{review_id}.",
                    )
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Peer review deadline has passed.")
            except HTTPException:
                raise
            except Exception:
                pass

    review.review_text = review_data.review_text
    review.score = review_data.score
    review.status = "submitted"

    db.commit()
    db.refresh(review)

    log_activity(
        db=db,
        user=current_user,
        action="SUBMIT_PEER_REVIEW",
        resource_type="peer_review",
        resource_id=str(review_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"Reviewer {current_user.username} submitted review #{review_id} with score {review.score}.",
    )
    return serialize_peer_review(review, redact_reviewer=False)


# ===================== GRADE APPEALS =====================

@router.post("/submissions/{submission_id}/appeal", response_model=GradeAppealOut, status_code=status.HTTP_201_CREATED)
def file_grade_appeal(
    submission_id: int,
    appeal_data: GradeAppealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """File a formal grade appeal on a graded submission. Owner only."""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    if submission.student_id != current_user.id:
        log_activity(
            db=db,
            user=current_user,
            action="FILE_GRADE_APPEAL",
            resource_type="grade_appeal",
            resource_id=f"sub:{submission_id}",
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} attempted to file appeal on submission #{submission_id} belonging to student #{submission.student_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: you can only appeal your own graded submissions.")

    if submission.grade is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot appeal an ungraded submission.")

    # Check for existing pending/under_review appeal
    existing = db.scalar(
        select(GradeAppeal).where(
            GradeAppeal.submission_id == submission_id,
            GradeAppeal.status.in_(["pending", "under_review"]),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An appeal is already active for this submission.")

    new_appeal = GradeAppeal(
        submission_id=submission_id,
        student_id=current_user.id,
        reason=appeal_data.reason,
        status="pending",
    )
    db.add(new_appeal)
    db.commit()
    db.refresh(new_appeal)

    log_activity(
        db=db,
        user=current_user,
        action="FILE_GRADE_APPEAL",
        resource_type="grade_appeal",
        resource_id=str(new_appeal.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"Student {current_user.username} filed grade appeal #{new_appeal.id} on submission #{submission_id}.",
    )
    return serialize_grade_appeal(new_appeal)


@router.get("/courses/{course_id}/appeals", response_model=List[GradeAppealOut])
def list_course_appeals(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List appeals for a course. Staff sees all; student sees only their own."""
    verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    query = select(GradeAppeal).join(Submission).join(Assignment).where(Assignment.course_id == course_id)

    if course_role not in ["admin", "professor", "ta"]:
        query = query.where(GradeAppeal.student_id == current_user.id)

    appeals = db.scalars(query.order_by(GradeAppeal.created_at.desc())).all()
    return [serialize_grade_appeal(a) for a in appeals]


@router.get("/appeals/{appeal_id}", response_model=GradeAppealOut)
def get_appeal(
    appeal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get single appeal details. Only appeal filer or course staff permitted."""
    appeal = db.get(GradeAppeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade appeal not found.")

    course_id = appeal.submission.assignment.course_id
    verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    is_staff = course_role in ["admin", "professor", "ta"]
    is_owner = appeal.student_id == current_user.id

    if not (is_staff or is_owner):
        log_activity(
            db=db,
            user=current_user,
            action="VIEW_GRADE_APPEAL",
            resource_type="grade_appeal",
            resource_id=str(appeal_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} denied access to grade appeal #{appeal_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: you cannot view this grade appeal.")

    return serialize_grade_appeal(appeal)


@router.put("/appeals/{appeal_id}/resolve", response_model=GradeAppealOut)
def resolve_appeal(
    appeal_id: int,
    resolution: GradeAppealResolve,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve a grade appeal. Course staff only."""
    appeal = db.get(GradeAppeal, appeal_id)
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade appeal not found.")

    course_id = appeal.submission.assignment.course_id
    verify_course_staff(course_id, current_user, db)

    appeal.status = resolution.status
    appeal.resolution_notes = resolution.resolution_notes
    appeal.reviewer_id = current_user.id

    if resolution.status == "approved" and resolution.adjusted_grade is not None:
        max_grade = appeal.submission.assignment.max_grade if appeal.submission.assignment else 100
        if resolution.adjusted_grade < 0 or resolution.adjusted_grade > max_grade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjusted grade must be between 0 and {max_grade}.",
            )
        prev_grade = appeal.submission.grade
        appeal.submission.grade = resolution.adjusted_grade

        history = GradeHistory(
            submission_id=appeal.submission_id,
            course_id=course_id,
            student_id=appeal.student_id,
            previous_grade=prev_grade,
            new_grade=resolution.adjusted_grade,
            changed_by_id=current_user.id,
            reason=f"Grade appeal #{appeal.id} approved: {resolution.resolution_notes}",
        )
        db.add(history)

    db.commit()
    db.refresh(appeal)

    log_activity(
        db=db,
        user=current_user,
        action="RESOLVE_GRADE_APPEAL",
        resource_type="grade_appeal",
        resource_id=str(appeal_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"Staff {current_user.username} resolved appeal #{appeal_id} to '{appeal.status}'.",
    )
    return serialize_grade_appeal(appeal)
