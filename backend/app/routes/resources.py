from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, Course, Resource
from ..schemas import ResourceOut, ResourceCreate
from ..auth import get_current_user
from ..permissions import (
    verify_course_access,
    verify_course_professor_or_admin,
    verify_resource_access,
    get_user_course_role,
    log_activity,
)

router = APIRouter(tags=["Resources"])


def serialize_resource(r: Resource) -> Dict[str, Any]:
    return {
        "id": r.id,
        "course_id": r.course_id,
        "course_code": r.course.code if r.course else "",
        "title": r.title,
        "description": r.description,
        "resource_type": r.resource_type,
        "url_or_content": r.url_or_content,
        "owner_id": r.owner_id,
        "owner_name": r.owner.full_name if r.owner else "Instructor",
        "is_visible": r.is_visible,
        "is_staff_only": r.is_staff_only,
        "created_at": r.created_at,
    }


@router.get("/courses/{course_id}/resources", response_model=List[ResourceOut])
def list_course_resources(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve learning resources for an authorized course."""
    verify_course_access(course_id, current_user, db)
    role = get_user_course_role(course_id, current_user, db)

    stmt = select(Resource).where(Resource.course_id == course_id).order_by(Resource.id)
    if role == "student":
        # Students see only student-facing resources
        stmt = stmt.where(Resource.is_visible == True, Resource.is_staff_only == False)

    resources = db.scalars(stmt).all()
    return [serialize_resource(r) for r in resources]


@router.get("/resources/{resource_id}", response_model=ResourceOut)
def get_resource_by_id(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve individual resource. Enforces staff-only access boundary."""
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    verify_resource_access(resource, current_user, db)
    return serialize_resource(resource)


@router.post("/courses/{course_id}/resources", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(
    course_id: int,
    payload: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a learning resource (Assigned professor or Admin only)."""
    course = verify_course_professor_or_admin(course_id, current_user, db)

    resource = Resource(
        course_id=course_id,
        title=payload.title,
        description=payload.description,
        resource_type=payload.resource_type,
        url_or_content=payload.url_or_content,
        owner_id=current_user.id,
        is_visible=payload.is_visible,
        is_staff_only=payload.is_staff_only,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    log_activity(
        db=db,
        user=current_user,
        action="CREATE_RESOURCE",
        resource_type="resource",
        resource_id=str(resource.id),
        outcome="ALLOW",
        http_status=201,
        detail=f"Added resource '{resource.title}' (staff_only={resource.is_staff_only}) to course {course.code}.",
    )
    return serialize_resource(resource)


@router.delete("/resources/{resource_id}")
def delete_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a resource (Assigned professor or Admin only)."""
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    verify_course_professor_or_admin(resource.course_id, current_user, db)

    db.delete(resource)
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="DELETE_RESOURCE",
        resource_type="resource",
        resource_id=str(resource_id),
        outcome="ALLOW",
        http_status=200,
        detail=f"Deleted resource ID {resource_id}.",
    )
    return {"message": "Resource deleted successfully."}
