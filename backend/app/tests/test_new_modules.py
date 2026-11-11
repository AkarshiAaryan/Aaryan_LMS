import pytest
from fastapi import status
from sqlalchemy import select

from ..models import (
    User, Course, DiscussionThread, DiscussionPost, LearningModule, Lesson,
    CourseFile, PeerReview, GradeAppeal, AttendanceRecord, Submission, Assignment
)


def get_user(db, username):
    return db.scalar(select(User).where(User.username == username))


def get_course(db, code):
    return db.scalar(select(Course).where(Course.code == code))


# ===================== DISCUSSION TESTS =====================

def test_discussion_thread_lifecycle_and_security(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    prof = get_user(db_session, "prof01")
    c301 = get_course(db_session, "CSE301")

    # 1. Student01 creates a private thread with staff
    s01_headers = auth_headers(s01.username, s01.role, s01.id)
    res = client.post(
        f"/courses/{c301.id}/discussions",
        headers=s01_headers,
        json={"title": "Private Grading Question", "content": "Can you review question 3?", "is_private": True},
    )
    assert res.status_code == status.HTTP_201_CREATED
    thread_id = res.json()["id"]

    # 2. Student01 (author) can view private thread
    res = client.get(f"/discussions/{thread_id}", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK

    # 3. Prof (staff) can view private thread
    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    res = client.get(f"/discussions/{thread_id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK

    # 4. Student02 (unrelated student) is blocked (403) from private thread
    s02_headers = auth_headers(s02.username, s02.role, s02.id)
    res = client.get(f"/discussions/{thread_id}", headers=s02_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 5. Lock thread by professor
    res = client.put(f"/discussions/{thread_id}/lock?locked=true", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_locked"] is True

    # 6. Student cannot reply to locked thread
    res = client.post(
        f"/discussions/{thread_id}/posts",
        headers=s01_headers,
        json={"content": "Another follow-up comment"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ===================== LEARNING MODULES TESTS =====================

def test_learning_modules_and_unlock_time(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    c301 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Prof creates a scheduled module unlocking on 2026-11-20T00:00:00Z
    res = client.post(
        f"/courses/{c301.id}/modules",
        headers=prof_headers,
        json={
            "title": "Advanced Distributed Systems",
            "description": "Consensus protocols",
            "order_index": 5,
            "is_published": True,
            "unlock_date": "2026-11-20T00:00:00Z",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    module_id = res.json()["id"]

    # 2. Prof creates a lesson in the module
    res = client.post(
        f"/modules/{module_id}/lessons",
        headers=prof_headers,
        json={"title": "Raft Implementation", "content": "Detailed Raft leader election algorithm..."},
    )
    assert res.status_code == status.HTTP_201_CREATED
    lesson_id = res.json()["id"]

    # 3. Before unlock date (e.g. simulation time 2026-11-10T10:00:00Z) -> Student blocked (403)
    time_headers_before = {**s01_headers, "X-Simulation-Time": "2026-11-10T10:00:00Z"}
    res = client.get(f"/modules/{module_id}", headers=time_headers_before)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    res = client.get(f"/lessons/{lesson_id}", headers=time_headers_before)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 4. Staff can access anytime
    res = client.get(f"/modules/{module_id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK

    # 5. After unlock date (e.g. simulation time 2026-11-25T10:00:00Z) -> Student allowed (200)
    time_headers_after = {**s01_headers, "X-Simulation-Time": "2026-11-25T10:00:00Z"}
    res = client.get(f"/modules/{module_id}", headers=time_headers_after)
    assert res.status_code == status.HTTP_200_OK

    res = client.get(f"/lessons/{lesson_id}", headers=time_headers_after)
    assert res.status_code == status.HTTP_200_OK
    assert "Raft leader election" in res.json()["content"]


# ===================== COURSE FILES TESTS =====================

def test_course_files_access_levels(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    c301 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)
    s02_headers = auth_headers(s02.username, s02.role, s02.id)

    # 1. Staff uploads staff-only exam draft
    res = client.post(
        f"/courses/{c301.id}/files",
        headers=prof_headers,
        json={
            "folder_path": "/exams",
            "filename": "midterm_master_key.pdf",
            "file_size_bytes": 45000,
            "access_level": "staff_only",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    staff_file_id = res.json()["id"]

    # 2. Student denied access to staff-only file
    res = client.get(f"/files/{staff_file_id}/download", headers=s01_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 3. Student uploads private study notes
    res = client.post(
        f"/courses/{c301.id}/files",
        headers=s01_headers,
        json={
            "folder_path": "/personal",
            "filename": "asha_revision_notes.txt",
            "access_level": "private",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    private_file_id = res.json()["id"]

    # 4. Student01 can download own private file
    res = client.get(f"/files/{private_file_id}/download", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK

    # 5. Student02 denied access to Student01's private file
    res = client.get(f"/files/{private_file_id}/download", headers=s02_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 6. Expired file check: Staff uploads file expiring on 2026-11-01
    res = client.post(
        f"/courses/{c301.id}/files",
        headers=prof_headers,
        json={
            "folder_path": "/slides",
            "filename": "temporary_slides.pdf",
            "access_level": "students",
            "expires_at": "2026-11-01T00:00:00Z",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    exp_file_id = res.json()["id"]

    # Student accessing at 2026-11-10 -> blocked because expired
    time_headers = {**s01_headers, "X-Simulation-Time": "2026-11-10T12:00:00Z"}
    res = client.get(f"/files/{exp_file_id}/download", headers=time_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ===================== PEER REVIEWS & APPEALS TESTS =====================

def test_peer_review_and_grade_appeal(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    prof = get_user(db_session, "prof01")
    c301 = get_course(db_session, "CSE301")

    # Find a graded submission belonging to student01
    submission = db_session.scalar(
        select(Submission).join(Assignment).where(
            Assignment.course_id == c301.id,
            Submission.student_id == s01.id,
            Submission.grade != None,
        )
    )
    assert submission is not None

    # Setup peer review: student02 reviews student01's submission (anonymous)
    existing_pr = db_session.scalar(
        select(PeerReview).where(
            PeerReview.submission_id == submission.id,
            PeerReview.reviewer_id == s02.id
        )
    )
    if existing_pr:
        db_session.delete(existing_pr)
        db_session.commit()

    peer_review = PeerReview(
        submission_id=submission.id,
        reviewer_id=s02.id,
        is_anonymous=True,
        review_text="Initial review text placeholder",
        score=85,
        status="submitted",
        deadline="2026-12-01T00:00:00Z",
    )
    db_session.add(peer_review)
    db_session.commit()
    db_session.refresh(peer_review)

    s01_headers = auth_headers(s01.username, s01.role, s01.id)
    s02_headers = auth_headers(s02.username, s02.role, s02.id)
    prof_headers = auth_headers(prof.username, prof.role, prof.id)

    # 1. Author (student01) views peer review -> reviewer_name must be 'Anonymous Reviewer', reviewer_id None
    res = client.get(f"/peer-reviews/{peer_review.id}", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["reviewer_id"] is None
    assert res.json()["reviewer_name"] == "Anonymous Reviewer"

    # 2. Staff views peer review -> sees reviewer identity
    res = client.get(f"/peer-reviews/{peer_review.id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["reviewer_id"] == s02.id

    # 3. Grade appeal: student01 files appeal on submission
    # First delete any existing appeal on this submission if present
    existing_appeal = db_session.scalar(select(GradeAppeal).where(GradeAppeal.submission_id == submission.id))
    if existing_appeal:
        db_session.delete(existing_appeal)
        db_session.commit()

    res = client.post(
        f"/submissions/{submission.id}/appeal",
        headers=s01_headers,
        json={"submission_id": submission.id, "reason": "My algorithm complexity was misunderstood in question 2."},
    )
    assert res.status_code == status.HTTP_201_CREATED
    appeal_id = res.json()["id"]

    # 4. Student02 cannot resolve appeal (403)
    res = client.put(
        f"/appeals/{appeal_id}/resolve",
        headers=s02_headers,
        json={"status": "approved", "resolution_notes": "Fake approval attempt"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 5. Prof resolves appeal
    res = client.put(
        f"/appeals/{appeal_id}/resolve",
        headers=prof_headers,
        json={"status": "approved", "resolution_notes": "Re-evaluated complexity; regraded accordingly."},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "approved"


# ===================== ATTENDANCE TESTS =====================

def test_attendance_and_session_locking(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    ta = get_user(db_session, "ta01")
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    c301 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    ta_headers = auth_headers(ta.username, ta.role, ta.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. TA records attendance for student01
    res = client.post(
        f"/courses/{c301.id}/attendance",
        headers=ta_headers,
        json={
            "student_id": s01.id,
            "session_date": "2026-11-05",
            "status": "absent",
            "notes": "Unexcused absence",
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    record_id = res.json()["id"]

    # 2. Student01 can view own attendance
    res = client.get(f"/courses/{c301.id}/attendance", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert all(r["student_id"] == s01.id for r in data)

    # 3. Student submits excuse request before lock
    res = client.post(
        f"/attendance/{record_id}/excuse?excuse_note=Medical%20appointment%20with%20clinic%20doctor",
        headers=s01_headers,
    )
    assert res.status_code == status.HTTP_200_OK
    assert "Medical appointment" in res.json()["notes"]

    # 4. Professor locks attendance record
    res = client.put(f"/attendance/{record_id}/lock?locked=true", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_locked"] is True

    # 5. Student cannot submit excuse on locked record (403)
    res = client.post(
        f"/attendance/{record_id}/excuse?excuse_note=Late%20excuse%20attempt",
        headers=s01_headers,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
