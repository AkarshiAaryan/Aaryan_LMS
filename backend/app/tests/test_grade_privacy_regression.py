import pytest
from fastapi import status
from sqlalchemy import select

from ..models import User, Course, Assignment, Submission
from .test_new_modules import get_user, get_course


def test_unpublished_grade_redaction_and_privacy(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    ta = get_user(db_session, "ta01")
    s01 = get_user(db_session, "student01")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    ta_headers = auth_headers(ta.username, ta.role, ta.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Professor creates an assignment
    res = client.post(
        f"/assignments/course/{c101.id}",
        headers=prof_headers,
        json={
            "title": "Privacy Test Assignment",
            "description": "Testing unpublished grade visibility",
            "instructions": "Submit test content",
            "due_date": "2026-12-31T23:59:59",
            "max_grade": 100,
            "submission_type": "text",
            "is_published": True,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    assignment_id = res.json()["id"]

    # 2. Student01 submits
    res = client.post(
        f"/assignments/{assignment_id}/submit",
        headers=s01_headers,
        json={"content": "Here is my privacy homework solution."},
    )
    assert res.status_code == status.HTTP_201_CREATED
    submission_id = res.json()["id"]

    # 3. TA grades submission with is_published=False (draft grade)
    res = client.put(
        f"/submissions/{submission_id}/grade",
        headers=ta_headers,
        json={"grade": 92.5, "feedback": "Solid work, draft review.", "is_published": False},
    )
    assert res.status_code == status.HTTP_200_OK

    # 4. Student views their submission: grade and feedback must be redacted (None)
    res = client.get(f"/submissions/{submission_id}", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["grade"] is None
    assert data["feedback"] is None

    # Student views course assignments list: my_submission grade must also be redacted
    res = client.get(f"/assignments/course/{c101.id}", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    target_asgn = [a for a in res.json() if a["id"] == assignment_id][0]
    assert target_asgn["my_submission"]["grade"] is None

    # Student views student aggregate grades: unpublished assignment score must be redacted (None)
    res = client.get("/grades/me", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    course_grade = [c for c in res.json() if c["course_id"] == c101.id][0]
    asgn_items = [i for i in course_grade["grade_data"]["items"] if i.get("item_id") == assignment_id and i.get("item_type") == "assignment"]
    assert len(asgn_items) == 1
    assert asgn_items[0]["score"] is None

    # 5. TA and Professor CAN view the draft grade
    res = client.get(f"/submissions/{submission_id}", headers=ta_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["grade"] == 92.5
    assert res.json()["feedback"] == "Solid work, draft review."

    res = client.get(f"/submissions/{submission_id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["grade"] == 92.5

    # 6. TA publishes the grade
    res = client.put(
        f"/submissions/{submission_id}/grade",
        headers=ta_headers,
        json={"grade": 95.0, "feedback": "Final grade published.", "is_published": True},
    )
    assert res.status_code == status.HTTP_200_OK

    # 7. Student can now see the published grade
    res = client.get(f"/submissions/{submission_id}", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["grade"] == 95.0
    assert res.json()["feedback"] == "Final grade published."

    # Student aggregate also displays published grade
    res = client.get("/grades/me", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    course_grade = [c for c in res.json() if c["course_id"] == c101.id][0]
    asgn_items = [i for i in course_grade["grade_data"]["items"] if i.get("item_id") == assignment_id and i.get("item_type") == "assignment"]
    assert len(asgn_items) == 1
    assert asgn_items[0]["score"] == 95.0
