from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, CourseFile, GroupMember
from ..schemas import CourseFileOut, CourseFileCreate
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_staff,
    get_user_course_role,
    log_activity,
)
from ..clock import Clock

router = APIRouter(tags=["Files"])


def serialize_course_file(f: CourseFile) -> Dict[str, Any]:
    return {
        "id": f.id,
        "course_id": f.course_id,
        "folder_path": f.folder_path,
        "filename": f.filename,
        "file_size_bytes": f.file_size_bytes,
        "owner_id": f.owner_id,
        "owner_name": f.owner.full_name if f.owner else "System",
        "access_level": f.access_level,
        "group_id": f.group_id,
        "is_archived": f.is_archived,
        "expires_at": f.expires_at or "",
        "created_at": f.created_at,
    }


def verify_file_access(file: CourseFile, user: User, request: Request, db: Session, action: str = "DOWNLOAD_FILE") -> None:
    """Enforce access_level, expiration, and archive constraints on file access."""
    verify_course_access(file.course_id, user, db)
    course_role = get_user_course_role(file.course_id, user, db)

    # Course staff and Admin have universal access
    if course_role in ["admin", "professor", "ta"]:
        return

    # Check expiration relative to simulation clock
    if file.expires_at:
        try:
            exp_dt = Clock.parse_iso_datetime(file.expires_at)
            if Clock.get_time(request) > exp_dt:
                log_activity(
                    db=db,
                    user=user,
                    action=action,
                    resource_type="file",
                    resource_id=str(file.id),
                    outcome="BLOCK",
                    http_status=status.HTTP_403_FORBIDDEN,
                    detail=f"Student {user.username} blocked from expired file #{file.id} (expired {file.expires_at}).",
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This file has expired and is no longer available.")
        except HTTPException:
            raise
        except Exception:
            pass

    # Check archived
    if file.is_archived:
        log_activity(
            db=db,
            user=user,
            action=action,
            resource_type="file",
            resource_id=str(file.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} blocked from archived file #{file.id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This file has been archived by course staff.")

    # Check access level
    if file.access_level == "staff_only":
        log_activity(
            db=db,
            user=user,
            action=action,
            resource_type="file",
            resource_id=str(file.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} denied access to staff-only file #{file.id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: this file is restricted to course staff.")

    if file.access_level == "private" and file.owner_id != user.id:
        log_activity(
            db=db,
            user=user,
            action=action,
            resource_type="file",
            resource_id=str(file.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"Student {user.username} denied access to private file #{file.id} owned by user #{file.owner_id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: this is a private file.")

    if file.access_level == "group_only" and file.group_id:
        is_member = db.scalar(
            select(GroupMember).where(
                GroupMember.group_id == file.group_id,
                GroupMember.user_id == user.id,
            )
        )
        if not is_member:
            log_activity(
                db=db,
                user=user,
                action=action,
                resource_type="file",
                resource_id=str(file.id),
                outcome="BLOCK",
                http_status=status.HTTP_403_FORBIDDEN,
                detail=f"Student {user.username} denied access to group #{file.group_id} file #{file.id}.",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: you are not a member of the group that owns this file.")


@router.get("/courses/{course_id}/files", response_model=List[CourseFileOut])
def list_course_files(
    course_id: int,
    request: Request,
    folder: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List course files filtered by user authorization level."""
    verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    query = select(CourseFile).where(CourseFile.course_id == course_id)
    if folder:
        query = query.where(CourseFile.folder_path == folder)

    files = db.scalars(query.order_by(CourseFile.folder_path, CourseFile.filename)).all()

    visible_files = []
    for f in files:
        if course_role in ["admin", "professor", "ta"]:
            visible_files.append(serialize_course_file(f))
        else:
            # Check if file is expired or archived
            if f.is_archived:
                continue
            if f.expires_at:
                try:
                    exp_dt = Clock.parse_iso_datetime(f.expires_at)
                    if Clock.get_time(request) > exp_dt:
                        continue
                except Exception:
                    pass

            if f.access_level in ["public", "students"]:
                visible_files.append(serialize_course_file(f))
            elif f.access_level == "private" and f.owner_id == current_user.id:
                visible_files.append(serialize_course_file(f))
            elif f.access_level == "group_only" and f.group_id:
                is_member = db.scalar(
                    select(GroupMember).where(
                        GroupMember.group_id == f.group_id,
                        GroupMember.user_id == current_user.id,
                    )
                )
                if is_member:
                    visible_files.append(serialize_course_file(f))

    log_activity(
        db=db,
        user=current_user,
        action="LIST_COURSE_FILES",
        resource_type="file",
        resource_id=f"course:{course_id}",
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} listed {len(visible_files)} files in course #{course_id}.",
    )
    return visible_files


@router.post("/courses/{course_id}/files", response_model=CourseFileOut, status_code=status.HTTP_201_CREATED)
def create_course_file(
    course_id: int,
    file_data: CourseFileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload/register a file in the course repository."""
    verify_course_access(course_id, current_user, db)
    course_role = get_user_course_role(course_id, current_user, db)

    # Permission checks on access_level
    if file_data.access_level == "staff_only" and course_role not in ["admin", "professor", "ta"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course staff can create staff-only files.",
        )

    if file_data.access_level == "group_only":
        if not file_data.group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="group_id is required when access_level is group_only.",
            )
        if course_role not in ["admin", "professor", "ta"]:
            is_member = db.scalar(
                select(GroupMember).where(
                    GroupMember.group_id == file_data.group_id,
                    GroupMember.user_id == current_user.id,
                )
            )
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must be a member of the group to upload a group-only file.",
                )

    new_file = CourseFile(
        course_id=course_id,
        folder_path=file_data.folder_path,
        filename=file_data.filename,
        file_size_bytes=file_data.file_size_bytes,
        owner_id=current_user.id,
        access_level=file_data.access_level,
        group_id=file_data.group_id,
        expires_at=file_data.expires_at,
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    log_activity(
        db=db,
        user=current_user,
        action="UPLOAD_COURSE_FILE",
        resource_type="file",
        resource_id=str(new_file.id),
        outcome="ALLOW",
        http_status=status.HTTP_201_CREATED,
        detail=f"User {current_user.username} uploaded file '{new_file.filename}' (#{new_file.id}) to course #{course_id}.",
    )
    return serialize_course_file(new_file)


@router.get("/files/{file_id}", response_model=CourseFileOut)
def get_file_metadata(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get metadata for a specific file."""
    file = db.get(CourseFile, file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    verify_file_access(file, current_user, request, db, action="VIEW_FILE_METADATA")

    log_activity(
        db=db,
        user=current_user,
        action="VIEW_FILE_METADATA",
        resource_type="file",
        resource_id=str(file.id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} viewed file #{file.id} metadata.",
    )
    return serialize_course_file(file)


@router.get("/files/{file_id}/download")
def download_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download/stream file payload. Strictly enforces authorization and expiry."""
    file = db.get(CourseFile, file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    verify_file_access(file, current_user, request, db, action="DOWNLOAD_FILE")

    log_activity(
        db=db,
        user=current_user,
        action="DOWNLOAD_FILE",
        resource_type="file",
        resource_id=str(file.id),
        outcome="ALLOW",
        http_status=status.HTTP_200_OK,
        detail=f"User {current_user.username} downloaded file #{file.id} ('{file.filename}').",
    )
    # Return mock payload
    content = f"--- Content of {file.filename} (Size: {file.file_size_bytes} bytes) ---"
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
    )


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a course file. Only owner or course staff permitted."""
    file = db.get(CourseFile, file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    verify_course_access(file.course_id, current_user, db)
    course_role = get_user_course_role(file.course_id, current_user, db)

    is_staff = course_role in ["admin", "professor", "ta"]
    is_owner = file.owner_id == current_user.id

    if not (is_staff or is_owner):
        log_activity(
            db=db,
            user=current_user,
            action="DELETE_FILE",
            resource_type="file",
            resource_id=str(file.id),
            outcome="BLOCK",
            http_status=status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} denied permission to delete file #{file.id}.",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: you cannot delete this file.")

    db.delete(file)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="DELETE_FILE",
        resource_type="file",
        resource_id=str(file.id),
        outcome="ALLOW",
        http_status=status.HTTP_204_NO_CONTENT,
        detail=f"User {current_user.username} deleted file #{file.id}.",
    )
    return None
