from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User
from ..schemas import UserLogin, TokenResponse, UserOut
from ..auth import verify_password, create_access_token, get_current_user
from ..permissions import log_activity

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate user with username and password, returning JWT access token."""
    username = None
    password = None

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username and password are required.",
        )

    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.password_hash):
        log_activity(
            db=db,
            user=user,
            action="LOGIN_FAILURE",
            resource_type="auth",
            resource_id=username,
            outcome="BLOCK",
            http_status=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed login attempt for username '{username}'.",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_activity(
            db=db,
            user=user,
            action="LOGIN_DEACTIVATED",
            resource_type="auth",
            resource_id=str(user.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Deactivated user '{username}' attempted login.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an administrator.",
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role, "id": user.id})

    log_activity(
        db=db,
        user=user,
        action="LOGIN_SUCCESS",
        resource_type="auth",
        resource_id=str(user.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"User {user.username} successfully authenticated.",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserOut)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve identity of currently authenticated user."""
    return current_user


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log out authenticated user session and record audit event."""
    log_activity(
        db=db,
        user=current_user,
        action="LOGOUT",
        resource_type="auth",
        resource_id=str(current_user.id),
        outcome="ALLOW",
        http_status=200,
        detail=f"User {current_user.username} logged out.",
    )
    return {"message": "Logged out successfully."}
