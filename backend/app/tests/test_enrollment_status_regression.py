import pytest
from fastapi import status
from sqlalchemy import select

from ..models import User, Course, Enrollment, Assignment
from .test_new_modules import get_user, get_course


def test_enrollment_status_lifecycle_and_enforcement(client, auth_headers, db_session):
    admin = get_user(db_session, "admin01")
    prof = get_user(db_session, "prof01")
    s03 = get_user(db_session, "student03")
    c101 = get_course(db_session, "CSE301")

    admin_headers = auth_headers(admin.username, admin.role, admin.id)
    s03_headers = auth_headers(s03.username, s03.role, s03.id)

    # 1. Verify student03 is actively enrolled in CS101 initially
    enrollment = db_session.scalar(
        select(Enrollment).where(
            Enrollment.course_id == c101.id,
            Enrollment.user_id == s03.id,
        )
    )
    assert enrollment is not None
    assert enrollment.status == "active"

    # Active student can access course
    res = client.get(f"/courses/{c101.id}", headers=s03_headers)
    assert res.status_code == status.HTTP_200_OK

    # 2. Admin suspends student03's enrollment
    res = client.put(
        f"/admin/enrolments/{enrollment.id}",
        headers=admin_headers,
        json={"status": "suspended"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "suspended"

    # Suspended student gets 403 when accessing course
    res = client.get(f"/courses/{c101.id}", headers=s03_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "suspended" in res.json()["detail"].lower()

    # Suspended student cannot list course assignments
    res = client.get(f"/assignments/course/{c101.id}", headers=s03_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Suspended student cannot list course quizzes
    res = client.get(f"/quizzes/course/{c101.id}", headers=s03_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 3. Admin revokes student03's enrollment
    res = client.put(
        f"/admin/enrolments/{enrollment.id}",
        headers=admin_headers,
        json={"status": "revoked"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "revoked"

    # Revoked student gets 403 when accessing course
    res = client.get(f"/courses/{c101.id}", headers=s03_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "revoked" in res.json()["detail"].lower()

    # Course list for student03 no longer contains CS101
    res = client.get("/courses", headers=s03_headers)
    assert res.status_code == status.HTTP_200_OK
    enrolled_course_ids = [c["id"] for c in res.json()]
    assert c101.id not in enrolled_course_ids

    # 4. Admin reactivates student03
    res = client.put(
        f"/admin/enrolments/{enrollment.id}",
        headers=admin_headers,
        json={"status": "active"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "active"

    # Reactivated student can access course again
    res = client.get(f"/courses/{c101.id}", headers=s03_headers)
    assert res.status_code == status.HTTP_200_OK


def test_suspended_student_excluded_from_active_gradebook(client, auth_headers, db_session):
    admin = get_user(db_session, "admin01")
    prof = get_user(db_session, "prof01")
    s04 = get_user(db_session, "student06")
    c101 = get_course(db_session, "CSE301")

    admin_headers = auth_headers(admin.username, admin.role, admin.id)
    prof_headers = auth_headers(prof.username, prof.role, prof.id)

    enrollment = db_session.scalar(
        select(Enrollment).where(
            Enrollment.course_id == c101.id,
            Enrollment.user_id == s04.id,
        )
    )
    assert enrollment is not None

    # Check professor gradebook initially contains student04
    res = client.get(f"/grades/course/{c101.id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    students = res.json()["students"]
    s04_entry = [s for s in students if s["id"] == s04.id]
    assert len(s04_entry) == 1

    # Suspend student04
    client.put(
        f"/admin/enrolments/{enrollment.id}",
        headers=admin_headers,
        json={"status": "suspended"},
    )

    # Suspended student should NOT appear in active students list of gradebook
    res = client.get(f"/grades/course/{c101.id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    students = res.json()["students"]
    s04_entry = [s for s in students if s["id"] == s04.id]
    assert len(s04_entry) == 0

    # Clean up: restore active
    client.put(
        f"/admin/enrolments/{enrollment.id}",
        headers=admin_headers,
        json={"status": "active"},
    )
