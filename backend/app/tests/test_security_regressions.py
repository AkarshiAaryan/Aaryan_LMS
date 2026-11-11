import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.clock import Clock, override_clock, parse_iso_datetime
from app.models import User, Course, Assignment, Submission, Quiz, Resource, Group, GroupMember


def test_parse_iso_datetime_strict():
    """Verify parse_iso_datetime raises ValueError on invalid input and parses valid ISO-8601."""
    # Valid ISO strings
    dt1 = parse_iso_datetime("2026-12-15T10:00:00Z")
    assert dt1.year == 2026 and dt1.month == 12 and dt1.tzinfo is not None

    dt2 = parse_iso_datetime("2026-12-15")
    assert dt2.year == 2026 and dt2.month == 12

    # Invalid inputs must raise ValueError
    with pytest.raises(ValueError):
        parse_iso_datetime("not-a-valid-date")

    with pytest.raises(ValueError):
        parse_iso_datetime("")


def test_clock_simulation_override():
    """Verify Clock.now() responds deterministically to override_clock context manager."""
    simulated = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    with override_clock(simulated):
        assert Clock.now() == simulated

    # After exit, Clock returns real time
    assert (Clock.now() - datetime.now(timezone.utc)).total_seconds() < 2


def test_ta_cannot_start_student_quiz_attempt(client: TestClient, db_session: Session):
    """Verify that a TA cannot initiate a student quiz attempt in their assigned course."""
    # ta01 is TA in CSE301 (course_id=1). Quiz #4 is CSE301 Knowledge Assessment.
    login_res = client.post("/auth/login", json={"username": "ta01", "password": "GuardSLM2026!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Find quiz in CSE301
    quiz = db_session.scalar(select(Quiz).where(Quiz.title == "CSE301 Knowledge Assessment"))
    assert quiz is not None

    # Attempt to start quiz attempt as TA
    res = client.post(f"/quizzes/{quiz.id}/attempts", headers=headers)
    assert res.status_code == 403
    assert "only enrolled students" in res.json()["detail"].lower()


def test_ta_as_student_can_start_quiz_in_enrolled_course(client: TestClient, db_session: Session):
    """Verify ta01 (enrolled as student in CSE302) CAN start a quiz in CSE302 within window and quota."""
    login_res = client.post("/auth/login", json={"username": "ta01", "password": "GuardSLM2026!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Quiz #2 in CSE302: Networking Protocols Practice Quiz (Open, max 3)
    quiz = db_session.scalar(select(Quiz).where(Quiz.title == "Networking Protocols Practice Quiz"))
    assert quiz is not None

    res = client.post(f"/quizzes/{quiz.id}/attempts", headers=headers)
    assert res.status_code == 201
    assert res.json()["quiz_id"] == quiz.id


def test_student_cannot_access_unpublished_resource(client: TestClient, db_session: Session):
    """Verify student cannot retrieve an unpublished/hidden resource even by guessing its direct ID."""
    # Create an invisible resource in CSE301
    course = db_session.scalar(select(Course).where(Course.code == "CSE301"))
    prof = db_session.scalar(select(User).where(User.username == "prof01"))
    hidden_res = Resource(
        course_id=course.id,
        title="Draft Unpublished Syllabus Addendum",
        description="Confidential draft",
        resource_type="document",
        url_or_content="https://internal.test/addendum.pdf",
        owner_id=prof.id,
        is_visible=False,
        is_staff_only=False,
    )
    db_session.add(hidden_res)
    db_session.commit()
    db_session.refresh(hidden_res)

    # Login as student01 (enrolled in CSE301)
    login_res = client.post("/auth/login", json={"username": "student01", "password": "GuardSLM2026!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Direct access by ID
    res = client.get(f"/resources/{hidden_res.id}", headers=headers)
    assert res.status_code == 403
    assert "unpublished or hidden" in res.json()["detail"].lower()


def test_student_cannot_access_unpublished_assignment(client: TestClient, db_session: Session):
    """Verify student cannot view an unpublished assignment by direct ID."""
    course = db_session.scalar(select(Course).where(Course.code == "CSE301"))
    unpub_assign = Assignment(
        course_id=course.id,
        title="Future Surprise Assignment",
        description="Not published yet",
        instructions="Work in secret",
        due_date="2026-12-31T23:59:59Z",
        max_grade=100,
        is_published=False,
    )
    db_session.add(unpub_assign)
    db_session.commit()
    db_session.refresh(unpub_assign)

    login_res = client.post("/auth/login", json={"username": "student01", "password": "GuardSLM2026!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Should not appear in list
    list_res = client.get(f"/courses/{course.id}/assignments", headers=headers)
    assert unpub_assign.id not in [a["id"] for a in list_res.json()]

    # Direct ID access should be blocked
    direct_res = client.get(f"/assignments/{unpub_assign.id}", headers=headers)
    assert direct_res.status_code == 403
    assert "unpublished" in direct_res.json()["detail"].lower()


def test_student_cannot_access_unpublished_quiz(client: TestClient, db_session: Session):
    """Verify student cannot view or start an unpublished quiz by direct ID."""
    course = db_session.scalar(select(Course).where(Course.code == "CSE301"))
    unpub_quiz = Quiz(
        course_id=course.id,
        title="Unannounced Pop Quiz",
        description="Surprise assessment",
        open_date="2026-10-01T00:00:00Z",
        close_date="2026-12-31T23:59:59Z",
        answer_release_date="2026-12-31T23:59:59Z",
        time_limit_minutes=15,
        max_attempts=1,
        is_published=False,
    )
    db_session.add(unpub_quiz)
    db_session.commit()
    db_session.refresh(unpub_quiz)

    login_res = client.post("/auth/login", json={"username": "student01", "password": "GuardSLM2026!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List check
    list_res = client.get(f"/courses/{course.id}/quizzes", headers=headers)
    assert unpub_quiz.id not in [q["id"] for q in list_res.json()]

    # Direct detail access
    direct_res = client.get(f"/quizzes/{unpub_quiz.id}", headers=headers)
    assert direct_res.status_code == 403

    # Direct start attempt
    start_res = client.post(f"/quizzes/{unpub_quiz.id}/attempts", headers=headers)
    assert start_res.status_code == 403


def test_unenrolled_student_cannot_edit_submission(client: TestClient, db_session: Session):
    """Verify student14 (unenrolled in CSE301) cannot edit an assignment submission in CSE301."""
    # Find assignment in CSE301
    assign = db_session.scalar(select(Assignment).where(Assignment.title == "B-Tree Indexing Implementation"))
    assert assign is not None

    login_res = client.post("/auth/login", json={"username": "student14", "password": "GuardSLM2026!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sub_res = client.post(
        f"/assignments/{assign.id}/submit",
        headers=headers,
        json={"content": "Hacked submission attempt from unenrolled user", "is_draft": True},
    )
    assert sub_res.status_code == 403


def test_cross_course_group_submission_spoofing(client: TestClient, db_session: Session):
    """Verify a user cannot associate a group from HCI401 with an assignment in CSE301."""
    # Group in HCI401
    hci_group = db_session.scalar(select(Group).where(Group.name == "Design Team Alpha"))
    assert hci_group is not None

    # Assignment in CSE301 where student01 has not yet submitted
    cse_assign = db_session.scalar(select(Assignment).where(Assignment.title == "Query Execution Plan Optimization"))
    assert cse_assign is not None

    login_res = client.post("/auth/login", json={"username": "student01", "password": "GuardSLM2026!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        f"/assignments/{cse_assign.id}/submit",
        headers=headers,
        json={"content": "Spoofed group submission", "group_id": hci_group.id, "is_draft": True},
    )
    assert res.status_code == 403
    assert "invalid group" in res.json()["detail"].lower()
