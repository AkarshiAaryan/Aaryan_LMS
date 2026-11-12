from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, CourseSection, AttendanceRecord, AttendanceSession, Enrollment
from ..schemas import (
    AttendanceRecordOut, AttendanceRecordCreate, CourseSectionOut, CourseSectionCreate,
    AttendanceSessionOut, AttendanceSessionCreate
)
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_staff,
    get_user_course_role,
    log_activity,
)

router = APIRouter(tags=["Attendance & Sections"])


def serialize_section(s: CourseSection) -> Dict[str, Any]:
    return {
        "id": s.id,
        "course_id": s.course_id,
        "section_number": s.section_number,
        "title": s.title,
        "room": getattr(s, "room", ""),
        "meeting_times": getattr(s, "meeting_times", ""),
        "capacity": getattr(s, "capacity", 30),
        "instructor_id": s.instructor_id,
        "instructor_name": s.instructor.full_name if s.instructor else None,
        "created_at": s.created_at,
    }


def serialize_attendance_session(sess: AttendanceSession) -> Dict[str, Any]:
    return {
        "id": sess.id,
        "course_id": sess.course_id,
        "section_id": sess.section_id,
        "session_date": sess.session_date,
        "title": sess.title,
        "created_by_id": sess.created_by_id,
        "created_at": sess.created_at,
    }


def serialize_attendance(r: AttendanceRecord) -> Dict[str, Any]:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "section_id": r.section_id,
        "session_id": getattr(r, "session_id", None),
        "student_id": r.student_id,
        "student_name": r.student.full_name if r.student else "Student",
        "session_date": r.session_date,
        "status": r.status,
        "is_locked": r.is_locked,
        "recorded_by_id": r.recorded_by_id,
        "recorded_by_name": r.recorded_by.full_name if r.recorded_by else None,
        "notes": r.notes or "",
        "created_at": r.created_at,
    }


# ===================== COURSE SECTIONS =====================

@router.get("/courses/{course_id}/sections", response_model=List[CourseSectionOut])
def list_course_sections(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List sections for a course."""
    verify_course_access(course_id, current_user, db)
    sections = db.scalars(
        select(CourseSection).where(CourseSection.course_id == course_id).order_by(CourseSection.section_number)
    ).all()
    return [serialize_section(s) for s in sections]


@router.post("/courses/{course_id}/sections", response_model=CourseSectionOut, status_code=status.HTTP_201_CREATED)
def create_course_section(
    course_id: int,
    section_data: CourseSectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new course section. Course staff only."""
    verify_course_staff(course_id, current_user, db)

    existing = db.scalar(
        select(CourseSection).where(
            CourseSection.course_id == course_id,
            CourseSection.section_number == section_data.section_number,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section '{section_data.section_number}' already exists in this course.",
        )

    new_section = CourseSection(
        course_id=course_id,
        section_number=section_data.section_number,
        title=section_data.title,
        room=section_data.room,
        meeting_times=section_data.meeting_times,
        capacity=section_data.capacity,
        instructor_id=section_data.instructor_id,
    )
    db.add(new_section)
    db.commit()
    db.refresh(new_section)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_COURSE_SECTION",
        resource_type="section",
        resource_id=str(new_section.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"Staff {current_user.username} created section '{new_section.section_number}' for course #{course_id}.",
    )
    return serialize_section(new_section)


# ===================== ATTENDANCE SESSIONS =====================

@router.get("/courses/{course_id}/attendance/sessions", response_model=List[AttendanceSessionOut])
def list_attendance_sessions(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List attendance sessions for a course."""
    verify_course_access(course_id, current_user, db)
    sessions = db.scalars(
        select(AttendanceSession).where(AttendanceSession.course_id == course_id).order_by(AttendanceSession.session_date.desc())
    ).all()
    return [serialize_attendance_session(s) for s in sessions]


@router.post("/courses/{course_id}/attendance/sessions", response_model=AttendanceSessionOut, status_code=status.HTTP_201_CREATED)
def create_attendance_session(
    course_id: int,
    payload: AttendanceSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new attendance session. Course staff only."""
    verify_course_staff(course_id, current_user, db)

    if payload.section_id:
        sec = db.get(CourseSection, payload.section_id)
        if not sec or sec.course_id != course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section does not belong to this course.",
            )

    session = AttendanceSession(
        course_id=course_id,
        section_id=payload.section_id,
        session_date=payload.session_date,
        title=payload.title,
        created_by_id=current_user.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_ATTENDANCE_SESSION",
        resource_type="attendance_session",
        resource_id=str(session.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"Staff {current_user.username} created attendance session '{session.title}' on {session.session_date}.",
    )
    return serialize_attendance_session(session)


# ===================== ATTENDANCE RECORDS =====================

@router.get("/courses/{course_id}/attendance", response_model=List[AttendanceRecordOut])
def list_course_attendance(
    course_id: int,
    section_id: Optional[int] = None,
    student_id: Optional[int] = None,
    session_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List attendance records. Staff sees all; student only sees their own."""
    verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    query = select(AttendanceRecord).where(AttendanceRecord.course_id == course_id)

    if course_role not in ["admin", "professor", "ta"]:
        # Enforce student scoping
        query = query.where(AttendanceRecord.student_id == current_user.id)
    else:
        if student_id:
            query = query.where(AttendanceRecord.student_id == student_id)

    if section_id:
        query = query.where(AttendanceRecord.section_id == section_id)
    if session_date:
        query = query.where(AttendanceRecord.session_date == session_date)

    records = db.scalars(query.order_by(AttendanceRecord.session_date.desc())).all()

    log_activity(
        db=db,
        user=current_user,
        action="VIEW_ATTENDANCE",
        resource_type="attendance",
        resource_id=f"course:{course_id}",
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} viewed {len(records)} attendance records in course #{course_id}.",
    )
    return [serialize_attendance(r) for r in records]


@router.post("/courses/{course_id}/attendance", response_model=AttendanceRecordOut, status_code=status.HTTP_201_CREATED)
def record_attendance(
    course_id: int,
    attendance_data: AttendanceRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record student attendance for a session. Course staff only."""
    verify_course_staff(course_id, current_user, db)

    # Validate student is enrolled in this course
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == attendance_data.student_id,
        )
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User #{attendance_data.student_id} is not enrolled in course #{course_id}.",
        )

    # Check for existing record for same date
    existing = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.course_id == course_id,
            AttendanceRecord.student_id == attendance_data.student_id,
            AttendanceRecord.session_date == attendance_data.session_date,
        )
    )
    if existing:
        if existing.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Attendance record for this session is locked and cannot be overwritten.",
            )
        # Update existing
        existing.status = attendance_data.status
        existing.section_id = attendance_data.section_id
        if attendance_data.session_id:
            existing.session_id = attendance_data.session_id
        existing.notes = attendance_data.notes
        existing.recorded_by_id = current_user.id
        db.commit()
        db.refresh(existing)
        return serialize_attendance(existing)

    new_record = AttendanceRecord(
        course_id=course_id,
        section_id=attendance_data.section_id,
        session_id=attendance_data.session_id,
        student_id=attendance_data.student_id,
        session_date=attendance_data.session_date,
        status=attendance_data.status,
        notes=attendance_data.notes,
        recorded_by_id=current_user.id,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    log_activity(
        db=db,
        user=current_user,
        action="RECORD_ATTENDANCE",
        resource_type="attendance",
        resource_id=str(new_record.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"Staff {current_user.username} recorded attendance for student #{attendance_data.student_id} on {attendance_data.session_date}.",
    )
    return serialize_attendance(new_record)


@router.put("/attendance/{record_id}/lock", response_model=AttendanceRecordOut)
def lock_attendance_record(
    record_id: int,
    locked: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lock or unlock attendance record. Professor or Admin only."""
    record = db.get(AttendanceRecord, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found.")

    course_role = get_user_course_role(record.course_id, current_user, db)
    if course_role not in ["admin", "professor"]:
        log_activity(
            db=db,
            user=current_user,
            action="LOCK_ATTENDANCE",
            resource_type="attendance",
            resource_id=str(record_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} ({course_role}) attempted to modify lock state on record #{record_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only professors or administrators can lock/unlock attendance records.")

    record.is_locked = locked
    db.commit()
    db.refresh(record)

    log_activity(
        db=db,
        user=current_user,
        action="LOCK_ATTENDANCE",
        resource_type="attendance",
        resource_id=str(record_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} set lock={locked} on attendance record #{record_id}.",
    )
    return serialize_attendance(record)


@router.post("/attendance/{record_id}/excuse", response_model=AttendanceRecordOut)
def submit_attendance_excuse(
    record_id: int,
    excuse_note: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Student submits an excuse request for an absence. Record must not be locked."""
    record = db.get(AttendanceRecord, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found.")

    if record.student_id != current_user.id:
        log_activity(
            db=db,
            user=current_user,
            action="SUBMIT_ATTENDANCE_EXCUSE",
            resource_type="attendance",
            resource_id=str(record_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} attempted to submit excuse for student #{record.student_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: you can only submit excuse requests for your own records.")

    if record.is_locked:
        log_activity(
            db=db,
            user=current_user,
            action="SUBMIT_ATTENDANCE_EXCUSE",
            resource_type="attendance",
            resource_id=str(record_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {current_user.username} attempted to submit excuse for locked record #{record_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This attendance record is finalized and locked against edits.")

    record.notes = (record.notes + f" | Excuse request: {excuse_note}").strip(" | ")
    db.commit()
    db.refresh(record)

    log_activity(
        db=db,
        user=current_user,
        action="SUBMIT_ATTENDANCE_EXCUSE",
        resource_type="attendance",
        resource_id=str(record_id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"Student {current_user.username} submitted excuse on attendance record #{record_id}.",
    )
    return serialize_attendance(record)
