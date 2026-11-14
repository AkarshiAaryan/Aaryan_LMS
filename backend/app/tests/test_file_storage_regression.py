import io
import pytest
from fastapi import status

from ..models import User, Course, Group
from ..storage import sanitize_filename, sanitize_folder_path
from .test_new_modules import get_user, get_course


def test_storage_path_sanitization():
    # Test path traversal attempts
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("../../../malicious.sh") == "malicious.sh"
    assert sanitize_filename("") != ""  # returns fallback

    assert sanitize_folder_path("../../../var/log") == "var/log"
    assert sanitize_folder_path("/root/secrets") == "root/secrets"
    assert sanitize_folder_path("lecture1/slides") == "lecture1/slides"


def test_multipart_file_upload_and_download_lifecycle(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Invalid access_level rejected with 400
    file_bytes = b"Hello, this is actual syllabus file content."
    res = client.post(
        f"/courses/{c101.id}/files/upload",
        headers=prof_headers,
        data={"access_level": "invalid_level", "folder_path": "/syllabus"},
        files={"file": ("syllabus.pdf", io.BytesIO(file_bytes), "application/pdf")},
    )
    assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY)

    # 2. Upload valid file with student access
    res = client.post(
        f"/courses/{c101.id}/files/upload",
        headers=prof_headers,
        data={"access_level": "students", "folder_path": "syllabus"},
        files={"file": ("syllabus.pdf", io.BytesIO(file_bytes), "application/pdf")},
    )
    assert res.status_code == status.HTTP_201_CREATED
    file_info = res.json()
    file_id = file_info["id"]
    assert file_info["filename"] == "syllabus.pdf"
    assert file_info["access_level"] == "students"

    # 3. Student can download the file
    res = client.get(f"/files/{file_id}/download", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.content == file_bytes

    # 4. Archive the file
    res = client.put(f"/files/{file_id}/archive", headers=prof_headers, json={"is_archived": True})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_archived"] is True

    # 5. Group-only validation: group not in course rejected with 400
    res = client.post(
        f"/courses/{c101.id}/files/upload",
        headers=prof_headers,
        data={"access_level": "group_only", "group_id": 99999},
        files={"file": ("group_doc.txt", io.BytesIO(b"group notes"), "text/plain")},
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    # 6. Delete file cleans up disk and database
    res = client.delete(f"/files/{file_id}", headers=prof_headers)
    assert res.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)

    # Download after delete returns 404
    res = client.get(f"/files/{file_id}/download", headers=s01_headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_resource_download_lifecycle(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. List resources for CSE301
    res = client.get(f"/courses/{c101.id}/resources", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    student_resources = res.json()
    assert len(student_resources) > 0
    target_res = student_resources[0]

    # 2. Student downloads public/student resource
    download_res = client.get(f"/resources/{target_res['id']}/download", headers=s01_headers)
    assert download_res.status_code == status.HTTP_200_OK
    assert "attachment" in download_res.headers.get("Content-Disposition", "")
    assert target_res["title"].encode() in download_res.content

    # 3. Prof lists all resources including staff-only
    res_prof = client.get(f"/courses/{c101.id}/resources", headers=prof_headers)
    staff_only_resources = [r for r in res_prof.json() if r["is_staff_only"]]
    assert len(staff_only_resources) > 0
    staff_target = staff_only_resources[0]

    # 4. Student blocked from downloading staff-only resource
    block_res = client.get(f"/resources/{staff_target['id']}/download", headers=s01_headers)
    assert block_res.status_code == status.HTTP_403_FORBIDDEN

    # 5. Prof can download staff-only resource
    allow_res = client.get(f"/resources/{staff_target['id']}/download", headers=prof_headers)
    assert allow_res.status_code == status.HTTP_200_OK
    assert staff_target["title"].encode() in allow_res.content

