from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User
from ..schemas import UserOut
from ..auth import get_current_user
from ..permissions import require_admin, log_activity

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Return own profile."""
    return current_user


@router.get("", response_model=List[UserOut])
def read_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all users. Restricted to administrators only."""
    if current_user.role != "admin":
        log_activity(
            db=db,
            user=current_user,
            action="LIST_USERS",
            resource_type="users",
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} ({current_user.role}) denied access to global user roster.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Viewing all users is restricted to site administrators.",
        )

    users = db.scalars(select(User).order_by(User.id)).all()
    return users


@router.get("/{user_id}", response_model=UserOut)
def read_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View user by ID. Administrators can view any user; others can view only themselves."""
    if current_user.role != "admin" and current_user.id != user_id:
        log_activity(
            db=db,
            user=current_user,
            action="VIEW_USER",
            resource_type="user",
            resource_id=str(user_id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} tried to view profile of user ID {user_id}.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You may only view your own user profile.",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user
