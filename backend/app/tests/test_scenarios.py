import pytest
from fastapi import status
from sqlalchemy import select

from ..models import User, Course, Assignment, Submission, Quiz, Group, GroupMember


def get_user(db, username):
    return db.scalar(select(User).where(User.username == username))


def get_course(db, code):
    return db.scalar(select(Course).where(Course.code == code))


def get_assignment(db, course_id, title_contains):
    return db.scalar(
        select(Assignment).where(
            Assignment.course_id == course_id,
            Assignment.title.like(f"%{title_contains}%")
        )
    )


def get_quiz(db, course_id, title_contains):
    return db.scalar(
        select(Quiz).where(
            Quiz.course_id == course_id,
            Quiz.title.like(f"%{title_contains}%")
        )
    )


# Scenario 1: Asha, student in CSE301 -> View Asha's CSE301 grade -> Expected: Allow
def test_scenario_1_student_view_own_grade(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    c301 = get_course(db_session, "CSE301")
    headers = auth_headers(s01.username, s01.role, s01.id)

    res = client.get(f"/courses/{c301.id}/students/{s01.id}/grades", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["student_id"] == s01.id
    assert len(data["grades"]) > 0


# Scenario 2: Asha, student in CSE301 -> View Rohan's CSE301 grade -> Expected: Deny
def test_scenario_2_student_view_other_grade(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    c301 = get_course(db_session, "CSE301")
    headers = auth_headers(s01.username, s01.role, s01.id)

    res = client.get(f"/courses/{c301.id}/students/{s02.id}/grades", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "students can only view their own" in res.json()["detail"].lower()


# Scenario 3: Asha, student in CSE301 -> Open CSE301 class gradebook -> Expected: Deny
def test_scenario_3_student_open_class_gradebook(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    c301 = get_course(db_session, "CSE301")
    headers = auth_headers(s01.username, s01.role, s01.id)

    res = client.get(f"/courses/{c301.id}/class-gradebook", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "students cannot view class-wide gradebooks" in res.json()["detail"].lower()


# Scenario 4: Sam, TA in CSE301 -> View CSE301 class gradebook -> Expected: Allow
def test_scenario_4_ta_view_class_gradebook(client, auth_headers, db_session):
    ta01 = get_user(db_session, "ta01")
    c301 = get_course(db_session, "CSE301")
    headers = auth_headers(ta01.username, ta01.role, ta01.id)

    res = client.get(f"/courses/{c301.id}/class-gradebook", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert len(data) >= 2  # multiple students


# Scenario 5: Sam, TA in CSE301 -> Edit a CSE301 assignment mark -> Expected: Allow
def test_scenario_5_ta_edit_assignment_mark(client, auth_headers, db_session):
    ta01 = get_user(db_session, "ta01")
    c301 = get_course(db_session, "CSE301")
    headers = auth_headers(ta01.username, ta01.role, ta01.id)

    # Find a submission in CSE301 that is not locked
    sub = db_session.scalar(
        select(Submission)
        .join(Submission.assignment)
        .where(Assignment.course_id == c301.id, Submission.is_locked == False)
    )
    assert sub is not None

    res = client.post(
        f"/submissions/{sub.id}/grade",
        json={"grade": 89, "feedback": "Marked by TA Sam Lee", "reason": "Accurate 3NF model"},
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["grade"] == 89


# Scenario 6: Sam, student in CSE302 -> Open CSE302 staff gradebook -> Expected: Deny
def test_scenario_6_ta_as_student_open_staff_gradebook(client, auth_headers, db_session):
    ta01 = get_user(db_session, "ta01")
    c302 = get_course(db_session, "CSE302")
    headers = auth_headers(ta01.username, ta01.role, ta01.id)

    res = client.get(f"/courses/{c302.id}/class-gradebook", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN


# Scenario 7: Noor, TA in CSE302 -> View CSE302 submissions -> Expected: Allow
def test_scenario_7_ta_view_cse302_submissions(client, auth_headers, db_session):
    ta02 = get_user(db_session, "ta02")
    c302 = get_course(db_session, "CSE302")
    assign = get_assignment(db_session, c302.id, "Packet")
    headers = auth_headers(ta02.username, ta02.role, ta02.id)

    res = client.get(f"/assignments/{assign.id}/submissions", headers=headers)
    assert res.status_code == status.HTTP_200_OK


# Scenario 8: Noor, TA in HCI401 -> View HCI401 submissions -> Expected: Allow
def test_scenario_8_ta_view_hci401_submissions(client, auth_headers, db_session):
    ta02 = get_user(db_session, "ta02")
    hci = get_course(db_session, "HCI401")
    assign = get_assignment(db_session, hci.id, "Group Project")
    headers = auth_headers(ta02.username, ta02.role, ta02.id)

    res = client.get(f"/assignments/{assign.id}/submissions", headers=headers)
    assert res.status_code == status.HTTP_200_OK


# Scenario 9: Rohan, student in CSE301 -> Edit own draft before deadline -> Expected: Allow
def test_scenario_9_student_edit_own_draft_before_deadline(client, auth_headers, db_session):
    s02 = get_user(db_session, "student02")
    c301 = get_course(db_session, "CSE301")
    assign = get_assignment(db_session, c301.id, "B-Tree")
    headers = auth_headers(s02.username, s02.role, s02.id)

    sub = db_session.scalar(
        select(Submission).where(
            Submission.assignment_id == assign.id,
            Submission.student_id == s02.id,
        )
    )
    assert sub is not None

    res = client.put(
        f"/submissions/{sub.id}",
        json={"content": "class BTreeNode: updated working code", "is_draft": True},
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    assert "updated working code" in res.json()["content"]


# Scenario 10: Rohan, student in CSE301 -> Edit own submission after deadline, no extension -> Expected: Deny
def test_scenario_10_student_edit_after_deadline_no_extension(client, auth_headers, db_session):
    s02 = get_user(db_session, "student02")
    c301 = get_course(db_session, "CSE301")
    assign = get_assignment(db_session, c301.id, "Relational Schema")
    headers = auth_headers(s02.username, s02.role, s02.id)

    sub = db_session.scalar(
        select(Submission).where(
            Submission.assignment_id == assign.id,
            Submission.student_id == s02.id,
        )
    )
    assert sub is not None

    res = client.put(
        f"/submissions/{sub.id}",
        json={"content": "Attempting late edit without extension", "is_draft": False},
        headers=headers,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "deadline has passed" in res.json()["detail"].lower()


# Scenario 11: Rohan, student in CSE301 -> View another student's submission -> Expected: Deny
def test_scenario_11_student_view_other_submission(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    c301 = get_course(db_session, "CSE301")
    assign = get_assignment(db_session, c301.id, "Relational Schema")
    headers = auth_headers(s02.username, s02.role, s02.id)

    # s01's submission
    sub1 = db_session.scalar(
        select(Submission).where(
            Submission.assignment_id == assign.id,
            Submission.student_id == s01.id,
        )
    )
    assert sub1 is not None

    res = client.get(f"/submissions/{sub1.id}", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN


# Scenario 12: Student in CSE302 -> Start quiz before opening time -> Expected: Deny
def test_scenario_12_student_start_quiz_before_open(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    c302 = get_course(db_session, "CSE302")
    quiz = get_quiz(db_session, c302.id, "Midterm")
    headers = auth_headers(s01.username, s01.role, s01.id)

    res = client.post(f"/quizzes/{quiz.id}/start", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "not yet open" in res.json()["detail"].lower()


# Scenario 13: Student in CSE302 -> Start quiz during availability window -> Expected: Allow
def test_scenario_13_student_start_quiz_during_window(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    c302 = get_course(db_session, "CSE302")
    quiz = get_quiz(db_session, c302.id, "Networking Protocols")
    headers = auth_headers(s01.username, s01.role, s01.id)

    res = client.post(f"/quizzes/{quiz.id}/start", headers=headers)
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["status"] == "in_progress"


# Scenario 14: Student in CSE302 -> View answer key before release -> Expected: Deny
def test_scenario_14_student_view_answer_key_before_release(client, auth_headers, db_session):
    s01 = get_user(db_session, "student01")
    c302 = get_course(db_session, "CSE302")
    quiz = get_quiz(db_session, c302.id, "Subnetting")
    headers = auth_headers(s01.username, s01.role, s01.id)

    res = client.get(f"/quizzes/{quiz.id}/answer-key", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "answer key has not been released yet" in res.json()["detail"].lower()


# Scenario 15: Dr Mira, professor of CSE301 -> Edit CSE301 assignment -> Expected: Allow
def test_scenario_15_prof_edit_own_course_assignment(client, auth_headers, db_session):
    prof01 = get_user(db_session, "prof01")
    c301 = get_course(db_session, "CSE301")
    assign = get_assignment(db_session, c301.id, "B-Tree")
    headers = auth_headers(prof01.username, prof01.role, prof01.id)

    res = client.put(
        f"/assignments/{assign.id}",
        json={"instructions": "Updated instructions by Dr Mira Shah"},
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    assert "Dr Mira Shah" in res.json()["instructions"]


# Scenario 16: Dr Mira, professor of CSE301 -> Edit CSE302 assignment -> Expected: Deny
def test_scenario_16_prof_edit_other_course_assignment(client, auth_headers, db_session):
    prof01 = get_user(db_session, "prof01")
    c302 = get_course(db_session, "CSE302")
    assign = get_assignment(db_session, c302.id, "Packet")
    headers = auth_headers(prof01.username, prof01.role, prof01.id)

    res = client.put(
        f"/assignments/{assign.id}",
        json={"instructions": "Unauthorized edit attempt by Mira in CSE302"},
        headers=headers,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


# Scenario 17: Dr Mira, professor of CSE301 -> Publish CSE301 grades -> Expected: Allow
def test_scenario_17_prof_publish_grades(client, auth_headers, db_session):
    prof01 = get_user(db_session, "prof01")
    c301 = get_course(db_session, "CSE301")
    headers = auth_headers(prof01.username, prof01.role, prof01.id)

    res = client.post(f"/courses/{c301.id}/publish-grades", json={"is_published": True}, headers=headers)
    assert res.status_code == status.HTTP_200_OK


# Scenario 18: Sam, TA in CSE301 -> Publish CSE301 grades -> Expected: Deny
def test_scenario_18_ta_publish_grades(client, auth_headers, db_session):
    ta01 = get_user(db_session, "ta01")
    c301 = get_course(db_session, "CSE301")
    headers = auth_headers(ta01.username, ta01.role, ta01.id)

    res = client.post(f"/courses/{c301.id}/publish-grades", json={"is_published": True}, headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "teaching assistants cannot publish final grades" in res.json()["detail"].lower()


# Scenario 19: Student in HCI401 -> View another group's private submission -> Expected: Deny
def test_scenario_19_student_view_other_group_submission(client, auth_headers, db_session):
    # student01 is in Design Team Alpha
    # Team Beta submission belongs to student05 / student06
    s01 = get_user(db_session, "student01")
    hci = get_course(db_session, "HCI401")
    assign = get_assignment(db_session, hci.id, "Group Project")
    beta_grp = db_session.scalar(select(Group).where(Group.course_id == hci.id, Group.name == "Design Team Beta"))
    headers = auth_headers(s01.username, s01.role, s01.id)

    beta_sub = db_session.scalar(
        select(Submission).where(
            Submission.assignment_id == assign.id,
            Submission.group_id == beta_grp.id,
        )
    )
    assert beta_sub is not None

    res = client.get(f"/submissions/{beta_sub.id}", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "students can only view their own" in res.json()["detail"].lower()


# Scenario 20: Administrator -> Manage a user account -> Expected: Allow
def test_scenario_20_admin_manage_user_account(client, auth_headers, db_session):
    admin = get_user(db_session, "admin01")
    s06 = get_user(db_session, "student06")
    headers = auth_headers(admin.username, admin.role, admin.id)

    res = client.put(
        f"/admin/users/{s06.id}",
        json={"full_name": "Arjun Nair (Verified Student)"},
        headers=headers,
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["full_name"] == "Arjun Nair (Verified Student)"
