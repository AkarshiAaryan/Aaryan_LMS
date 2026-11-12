import pytest
from fastapi import status

from ..models import User, Course, Announcement, Department
from .test_new_modules import get_user, get_course


def test_course_archival_and_announcement_lifecycle(client, auth_headers, db_session):
    admin = get_user(db_session, "admin01")
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    c101 = get_course(db_session, "CSE301")

    admin_headers = auth_headers(admin.username, admin.role, admin.id)
    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Student cannot archive course (403)
    res = client.put(f"/courses/{c101.id}/archive", headers=s01_headers, json={"is_archived": True})
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Prof archives course
    res = client.put(f"/courses/{c101.id}/archive", headers=prof_headers, json={"is_archived": True})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_archived"] is True

    # Prof unarchives course
    res = client.put(f"/courses/{c101.id}/archive", headers=prof_headers, json={"is_archived": False})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_archived"] is False

    # 3. Announcement lifecycle
    # Prof creates announcement
    res = client.post(
        f"/courses/{c101.id}/announcements",
        headers=prof_headers,
        json={"title": "Midterm Update", "content": "Exam will be next Friday."},
    )
    assert res.status_code == status.HTTP_201_CREATED
    ann_id = res.json()["id"]

    # Student cannot update announcement (403)
    res = client.put(
        f"/announcements/{ann_id}",
        headers=s01_headers,
        json={"title": "Hacked Title"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Prof updates announcement
    res = client.put(
        f"/announcements/{ann_id}",
        headers=prof_headers,
        json={"title": "Midterm Update: Finalized", "content": "Exam will be in Room 101."},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["title"] == "Midterm Update: Finalized"

    # Also test nested route PUT /courses/{id}/announcements/{ann_id}
    res = client.put(
        f"/courses/{c101.id}/announcements/{ann_id}",
        headers=prof_headers,
        json={"title": "Midterm Update: Revised"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["title"] == "Midterm Update: Revised"

    # Student cannot delete announcement (403)
    res = client.delete(f"/announcements/{ann_id}", headers=s01_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Prof deletes announcement
    res = client.delete(f"/announcements/{ann_id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK


def test_department_management_endpoints(client, auth_headers, db_session):
    admin = get_user(db_session, "admin01")
    s01 = get_user(db_session, "student01")

    admin_headers = auth_headers(admin.username, admin.role, admin.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Student cannot access department endpoints (403)
    res = client.get("/admin/departments", headers=s01_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Admin lists departments
    res = client.get("/admin/departments", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.json(), list)

    # 3. Admin creates new department
    res = client.post(
        "/admin/departments",
        headers=admin_headers,
        json={"code": "AI", "name": "Department of Artificial Intelligence", "description": "AI research"},
    )
    assert res.status_code == status.HTTP_201_CREATED
    dept_id = res.json()["id"]
    assert res.json()["code"] == "AI"

    # 4. Admin gets department details
    res = client.get(f"/admin/departments/{dept_id}", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["name"] == "Department of Artificial Intelligence"

    # 5. Admin updates department
    res = client.put(
        f"/admin/departments/{dept_id}",
        headers=admin_headers,
        json={"name": "Dept of Advanced AI"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["name"] == "Dept of Advanced AI"

    # 6. Admin deletes department
    res = client.delete(f"/admin/departments/{dept_id}", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK

    # 7. Admin lists all courses
    res = client.get("/admin/courses", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) > 0
