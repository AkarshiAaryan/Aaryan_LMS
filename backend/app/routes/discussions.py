from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, DiscussionThread, DiscussionPost, GroupMember, Group
from ..schemas import (
    DiscussionThreadOut, DiscussionThreadCreate, DiscussionPostOut, DiscussionPostCreate
)
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_staff,
    get_user_course_role,
    log_activity,
)

router = APIRouter(tags=["Discussions"])


def serialize_thread(t: DiscussionThread, include_posts: bool = False) -> Dict[str, Any]:
    posts_data = []
    if include_posts and t.posts:
        for p in t.posts:
            posts_data.append({
                "id": p.id,
                "thread_id": p.thread_id,
                "author_id": p.author_id,
                "author_name": p.author.full_name if p.author else "Anonymous",
                "author_role": p.author.role if p.author else "user",
                "content": p.content,
                "is_flagged": p.is_flagged,
                "created_at": p.created_at,
            })

    return {
        "id": t.id,
        "course_id": t.course_id,
        "author_id": t.author_id,
        "author_name": t.author.full_name if t.author else "Anonymous",
        "author_role": t.author.role if t.author else "user",
        "title": t.title,
        "content": t.content,
        "is_pinned": t.is_pinned,
        "is_locked": t.is_locked,
        "is_private": t.is_private,
        "group_id": t.group_id,
        "post_count": len(t.posts) if t.posts else 0,
        "created_at": t.created_at,
        "posts": posts_data,
    }


def verify_thread_access(thread: DiscussionThread, user: User, db: Session) -> None:
    """Enforce private thread, group thread, and course access boundaries."""
    verify_course_access(thread.course_id, user, db)
    course_role = get_user_course_role(thread.course_id, user, db)

    # Course staff and Admin have universal access
    if course_role in ["admin", "professor", "ta"]:
        return

    # Student checks:
    # 1. Private thread: only author and staff can view
    if thread.is_private and thread.author_id != user.id:
        log_activity(
            db=db,
            user=user,
            action="VIEW_DISCUSSION_THREAD",
            resource_type="discussion",
            resource_id=str(thread.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} denied access to private thread #{thread.id}.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this is a confidential private staff-student thread.",
        )

    # 2. Group thread: only members of this specific group can view
    if thread.group_id:
        is_member = db.scalar(
            select(GroupMember).where(
                GroupMember.group_id == thread.group_id,
                GroupMember.user_id == user.id,
            )
        )
        if not is_member:
            log_activity(
                db=db,
                user=user,
                action="VIEW_DISCUSSION_THREAD",
                resource_type="discussion",
                resource_id=str(thread.id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {user.username} denied access to group #{thread.group_id} discussion thread.",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you are not a member of this discussion group.",
            )


@router.get("/courses/{course_id}/discussions", response_model=List[DiscussionThreadOut])
def list_course_threads(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve discussion threads for a course, filtered by role and group boundaries."""
    verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    stmt = select(DiscussionThread).where(DiscussionThread.course_id == course_id)
    if course_role == "student":
        # Students see non-private threads, or private threads they authored
        user_groups = select(GroupMember.group_id).where(GroupMember.user_id == current_user.id)
        stmt = stmt.where(
            (DiscussionThread.is_private == False) | (DiscussionThread.author_id == current_user.id)
        ).where(
            (DiscussionThread.group_id == None) | (DiscussionThread.group_id.in_(user_groups))
        )

    threads = db.scalars(stmt.order_by(DiscussionThread.is_pinned.desc(), DiscussionThread.id.desc())).all()
    return [serialize_thread(t, include_posts=False) for t in threads]


@router.post("/courses/{course_id}/discussions", response_model=DiscussionThreadOut, status_code=status.HTTP_201_CREATED)
def create_course_thread(
    course_id: int,
    payload: DiscussionThreadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new discussion thread."""
    verify_course_access(course_id, current_user, db)

    # Validate group if specified
    if payload.group_id:
        grp = db.get(Group, payload.group_id)
        if not grp or grp.course_id != course_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: invalid group association for this course.",
            )
        course_role = get_user_course_role(course_id, current_user, db)
        if course_role == "student":
            is_member = db.scalar(
                select(GroupMember).where(
                    GroupMember.group_id == payload.group_id,
                    GroupMember.user_id == current_user.id,
                )
            )
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: you can only start threads in groups you belong to.",
                )

    thread = DiscussionThread(
        course_id=course_id,
        author_id=current_user.id,
        title=payload.title,
        content=payload.content,
        is_private=payload.is_private,
        group_id=payload.group_id,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_DISCUSSION_THREAD",
        resource_type="discussion",
        resource_id=str(thread.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"User {current_user.username} created discussion thread '{thread.title}'.",
    )
    return serialize_thread(thread, include_posts=True)


@router.get("/discussions/{thread_id}", response_model=DiscussionThreadOut)
def get_thread_by_id(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve an individual discussion thread and its reply posts."""
    thread = db.get(DiscussionThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion thread not found.")

    verify_thread_access(thread, current_user, db)
    return serialize_thread(thread, include_posts=True)


@router.post("/discussions/{thread_id}/posts", response_model=DiscussionPostOut, status_code=status.HTTP_201_CREATED)
def reply_to_thread(
    thread_id: int,
    payload: DiscussionPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reply to a discussion thread. Enforces thread locking rules."""
    thread = db.get(DiscussionThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion thread not found.")

    verify_thread_access(thread, current_user, db)
    course_role = get_user_course_role(thread.course_id, current_user, db)

    # If thread is locked, only staff may post
    if thread.is_locked and course_role not in ["admin", "professor", "ta"]:
        log_activity(
            db=db,
            user=current_user,
            action="REPLY_DISCUSSION_POST",
            resource_type="discussion",
            resource_id=str(thread.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {current_user.username} attempted to reply to locked thread #{thread.id}.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: this discussion thread is locked for replies.",
        )

    post = DiscussionPost(
        thread_id=thread_id,
        author_id=current_user.id,
        content=payload.content,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "id": post.id,
        "thread_id": post.thread_id,
        "author_id": post.author_id,
        "author_name": current_user.full_name,
        "author_role": current_user.role,
        "content": post.content,
        "is_flagged": post.is_flagged,
        "created_at": post.created_at,
    }


@router.post("/discussions/{thread_id}/lock", response_model=DiscussionThreadOut)
@router.put("/discussions/{thread_id}/lock", response_model=DiscussionThreadOut)
def lock_thread(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lock thread (Course staff only)."""
    thread = db.get(DiscussionThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion thread not found.")

    verify_course_staff(thread.course_id, current_user, db)
    thread.is_locked = True
    db.commit()
    db.refresh(thread)

    log_activity(
        db=db,
        user=current_user,
        action="LOCK_DISCUSSION_THREAD",
        resource_type="discussion",
        resource_id=str(thread.id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"Staff {current_user.username} locked discussion thread #{thread.id}.",
    )
    return serialize_thread(thread, include_posts=True)
