from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..database import get_db
from ..models import User, ActivityLog
from ..schemas import ActivityLogOut
from ..permissions import require_admin

router = APIRouter(prefix="/admin/logs", tags=["Audit Logs"])


@router.get("", response_model=List[ActivityLogOut])
def get_activity_logs(
    outcome: Optional[str] = Query(None, description="Filter by ALLOW or BLOCK"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve research activity logs. Accessible only to administrators."""
    stmt = select(ActivityLog).order_by(ActivityLog.timestamp.desc())

    if outcome:
        stmt = stmt.where(ActivityLog.outcome == outcome.upper())
    if resource_type:
        stmt = stmt.where(ActivityLog.resource_type == resource_type)

    stmt = stmt.limit(limit)
    logs = db.scalars(stmt).all()
    return logs
