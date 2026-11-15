import pytest
from fastapi import status
from sqlalchemy import select

from ..models import User, Course, Assignment, Submission, GradeAppeal, GradeHistory
from .test_new_modules import get_user, get_course


def test_peer_review_assignment_constraints(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Create an assignment and submission
    res = client.post(
        f"/assignments/course/{c101.id}",
        headers=prof_headers,
        json={
            "title": "Peer Review Target Assignment",
            "description": "Peer review testing",
            "instructions": "Follow constraints",
            "due_date": "2026-12-31T23:59:59",
            "max_grade": 100,
            "submission_type": "text",
            "is_published": True,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    asgn_id = res.json()["id"]

    res = client.post(
        f"/assignments/{asgn_id}/submit",
        headers=s01_headers,
        json={"content": "Peer review homework solution by student01."},
    )
    assert res.status_code == status.HTTP_201_CREATED
    sub_id = res.json()["id"]

    # 2. Block self-review (assignee == reviewer)
    res = client.post(
        f"/assignments/{asgn_id}/peer-reviews/assign",
        headers=prof_headers,
        json={"submission_id": sub_id, "reviewer_id": s01.id},
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "self-review" in res.json()["detail"].lower() or "reviewer cannot be" in res.json()["detail"].lower()

    # 3. Valid assignment: s02 reviews s01's submission
    res = client.post(
        f"/assignments/{asgn_id}/peer-reviews/assign",
        headers=prof_headers,
        json={"submission_id": sub_id, "reviewer_id": s02.id},
    )
    assert res.status_code == status.HTTP_201_CREATED

    # 4. Block duplicate review assignment
    res = client.post(
        f"/assignments/{asgn_id}/peer-reviews/assign",
        headers=prof_headers,
        json={"submission_id": sub_id, "reviewer_id": s02.id},
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "already assigned" in res.json()["detail"].lower()


def test_grade_appeal_regrade_and_history_logging(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Create assignment & submission
    res = client.post(
        f"/assignments/course/{c101.id}",
        headers=prof_headers,
        json={
            "title": "Appeal Test Assignment",
            "description": "Grading appeal flow",
            "instructions": "Test instructions",
            "due_date": "2026-12-31T23:59:59",
            "max_grade": 100,
            "submission_type": "text",
            "is_published": True,
        },
    )
    asgn_id = res.json()["id"]

    res = client.post(
        f"/assignments/{asgn_id}/submit",
        headers=s01_headers,
        json={"content": "My appeal target submission"},
    )
    sub_id = res.json()["id"]

    # Initial grading by prof
    client.put(
        f"/submissions/{sub_id}/grade",
        headers=prof_headers,
        json={"grade": 70.0, "feedback": "Needs improvement", "is_published": True},
    )

    # 2. Student files grade appeal
    res = client.post(
        f"/submissions/{sub_id}/appeal",
        headers=s01_headers,
        json={"reason": "Question 2 was graded too harshly."},
    )
    assert res.status_code == status.HTTP_201_CREATED
    appeal_id = res.json()["id"]

    # 3. Prof resolves appeal with adjusted grade 85.0
    res = client.put(
        f"/appeals/{appeal_id}/resolve",
        headers=prof_headers,
        json={
            "status": "approved",
            "resolution_notes": "Regraded after review. Additional points awarded.",
            "adjusted_grade": 85.0,
        },
    )
    assert res.status_code == status.HTTP_200_OK

    # 4. Verify submission grade updated
    res = client.get(f"/submissions/{sub_id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["grade"] == 85.0

    # 5. Verify GradeHistory logged
    history_records = db_session.scalars(
        select(GradeHistory).where(GradeHistory.submission_id == sub_id)
    ).all()
    assert len(history_records) >= 1
    regrade_records = [h for h in history_records if "appeal" in (h.reason or "").lower()]
    assert len(regrade_records) >= 1
    assert regrade_records[0].new_grade == 85.0
