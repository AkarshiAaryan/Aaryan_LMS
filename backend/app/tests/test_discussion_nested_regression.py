import pytest
from fastapi import status

from ..models import User, Course, DiscussionThread, DiscussionPost
from .test_new_modules import get_user, get_course


def test_discussion_private_recipient_and_nested_replies(client, auth_headers, db_session):
    prof = get_user(db_session, "prof01")
    s01 = get_user(db_session, "student01")
    s02 = get_user(db_session, "student02")
    s03 = get_user(db_session, "student03")
    c101 = get_course(db_session, "CSE301")

    prof_headers = auth_headers(prof.username, prof.role, prof.id)
    s01_headers = auth_headers(s01.username, s01.role, s01.id)
    s02_headers = auth_headers(s02.username, s02.role, s02.id)
    s03_headers = auth_headers(s03.username, s03.role, s03.id)

    # 1. Student01 creates private thread directed to Student02
    res = client.post(
        f"/courses/{c101.id}/discussions",
        headers=s01_headers,
        json={
            "title": "Private Consultation",
            "content": "Can you check my code?",
            "is_private": True,
            "recipient_id": s02.id,
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    thread_id = res.json()["id"]
    assert res.json()["recipient_id"] == s02.id

    # Author (s01) can view
    res = client.get(f"/discussions/{thread_id}", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK

    # Recipient (s02) can view
    res = client.get(f"/discussions/{thread_id}", headers=s02_headers)
    assert res.status_code == status.HTTP_200_OK

    # Staff (prof) can view
    res = client.get(f"/discussions/{thread_id}", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK

    # Unrelated student (s03) is blocked (403)
    res = client.get(f"/discussions/{thread_id}", headers=s03_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # 2. Nested reply: s02 posts a top-level reply, then s01 replies directly to it
    res = client.post(
        f"/discussions/{thread_id}/posts",
        headers=s02_headers,
        json={"content": "Sure, here are my initial observations."},
    )
    assert res.status_code == status.HTTP_201_CREATED
    top_post_id = res.json()["id"]

    res = client.post(
        f"/discussions/{thread_id}/posts",
        headers=s01_headers,
        json={"content": "Thanks! Specifically check line 42.", "parent_post_id": top_post_id},
    )
    assert res.status_code == status.HTTP_201_CREATED
    reply_post_id = res.json()["id"]
    assert res.json()["parent_post_id"] == top_post_id

    # Verify posts in thread details
    res = client.get(f"/discussions/{thread_id}", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    posts = res.json()["posts"]
    assert len(posts) == 2
    reply_post = [p for p in posts if p["id"] == reply_post_id][0]
    assert reply_post["parent_post_id"] == top_post_id

    # 3. Edit post: author can edit, others cannot
    res = client.put(
        f"/discussions/posts/{reply_post_id}",
        headers=s03_headers,
        json={"content": "Attempting unauthorized edit"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN

    res = client.put(
        f"/discussions/posts/{reply_post_id}",
        headers=s01_headers,
        json={"content": "Thanks! Specifically check lines 42-45."},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["content"] == "Thanks! Specifically check lines 42-45."

    # 4. Pin thread: student cannot pin, instructor can
    res = client.put(f"/discussions/{thread_id}/pin", headers=s01_headers, json={"is_pinned": True})
    assert res.status_code == status.HTTP_403_FORBIDDEN

    res = client.put(f"/discussions/{thread_id}/pin", headers=prof_headers, json={"is_pinned": True})
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_pinned"] is True

    # 5. Flag / Unflag post
    res = client.post(f"/discussions/posts/{top_post_id}/flag", headers=s01_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_flagged"] is True

    res = client.post(f"/discussions/posts/{top_post_id}/unflag", headers=prof_headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["is_flagged"] is False

    # 6. Delete post: non-author student cannot delete, author can delete
    res = client.delete(f"/discussions/posts/{reply_post_id}", headers=s03_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    res = client.delete(f"/discussions/posts/{reply_post_id}", headers=s01_headers)
    assert res.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)
