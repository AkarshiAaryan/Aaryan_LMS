import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status
from sqlalchemy import select

from ..models import User, Course, Quiz, QuizQuestion, QuizAttempt
from .test_new_modules import get_user, get_course


def test_quiz_scoring_and_boundary_integrity(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)

    # 1. Create a quiz with 2 questions
    now = datetime.now(timezone.utc)
    res = client.post(
        f"/quizzes/course/{c101.id}",
        headers=prof_headers,
        json={
            "title": "Integrity Test Quiz",
            "description": "Comprehensive quiz integrity test",
            "open_date": (now - timedelta(hours=1)).isoformat(),
            "close_date": (now + timedelta(hours=2)).isoformat(),
            "time_limit_minutes": 15,
            "max_attempts": 3,
            "is_published": True,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    quiz_id = res.json()["id"]

    # Add Question 1
    res = client.post(
        f"/quizzes/{quiz_id}/questions",
        headers=prof_headers,
        json={
            "question_text": "What is 2 + 2?",
            "question_type": "multiple_choice",
            "options": ["2", "3", "4", "5"],
            "correct_answer": "4",
            "points": 5,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    q1_id = res.json()["id"]

    # Add Question 2
    res = client.post(
        f"/quizzes/{quiz_id}/questions",
        headers=prof_headers,
        json={
            "question_text": "Is Python an interpreted language?",
            "question_type": "true_false",
            "options": ["True", "False"],
            "correct_answer": "True",
            "points": 5,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    q2_id = res.json()["id"]

    # 2. Student starts quiz attempt
    res = client.post(f"/quizzes/{quiz_id}/start", headers=s01_headers)
    assert res.status_code == status.HTTP_201_CREATED
    attempt_id = res.json()["id"]

    # Verify attempt fetch contract via both endpoints
    res1 = client.get(f"/quizzes/attempts/{attempt_id}", headers=s01_headers)
    assert res1.status_code == status.HTTP_200_OK
    res2 = client.get(f"/attempts/{attempt_id}", headers=s01_headers)
    assert res2.status_code == status.HTTP_200_OK
    assert res1.json()["id"] == res2.json()["id"]

    # 3. Test duplicate question rejection (400)
    res = client.post(
        f"/quizzes/attempts/{attempt_id}/submit",
        headers=s01_headers,
        json={
            "answers": [
                {"question_id": q1_id, "selected_answer": "4"},
                {"question_id": q1_id, "selected_answer": "3"},
            ]
        },
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "duplicate" in res.json()["detail"].lower()

    # 4. Test foreign question rejection (400)
    res = client.post(
        f"/quizzes/attempts/{attempt_id}/submit",
        headers=s01_headers,
        json={
            "answers": [
                {"question_id": 99999, "selected_answer": "XYZ"},
            ]
        },
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "not belong" in res.json()["detail"].lower()

    # 5. Test empty answer scoring (must score 0 out of 10, not 0 out of 0 / not 100%)
    res = client.post(
        f"/quizzes/attempts/{attempt_id}/submit",
        headers=s01_headers,
        json={"answers": []},
    )
    assert res.status_code == status.HTTP_200_OK
    result = res.json()
    assert result["score"] == 0.0
    assert result["status"] in ("finished", "submitted")

    # 6. Test resubmission of finished attempt (must be rejected 400)
    res = client.post(
        f"/quizzes/attempts/{attempt_id}/submit",
        headers=s01_headers,
        json={"answers": [{"question_id": q1_id, "selected_answer": "4"}]},
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "not in progress" in res.json()["detail"].lower()


def test_quiz_time_limit_and_expiration(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s02 = get_user(db_session, "student02")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s02_headers = auth_headers(s02.username, s02.role, s02.id)

    # Create an expired quiz (closed 1 hour ago)
    now = datetime.now(timezone.utc)
    res = client.post(
        f"/quizzes/course/{c101.id}",
        headers=prof_headers,
        json={
            "title": "Expired Quiz",
            "description": "Already past due date",
            "open_date": (now - timedelta(days=2)).isoformat(),
            "close_date": (now - timedelta(hours=1)).isoformat(),
            "time_limit_minutes": 10,
            "max_attempts": 1,
            "is_published": True,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    expired_quiz_id = res.json()["id"]

    # Student attempts to start closed quiz -> rejected 403 or 400
    res = client.post(f"/quizzes/{expired_quiz_id}/start", headers=s02_headers)
    assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN)
    assert "closed" in res.json()["detail"].lower()
