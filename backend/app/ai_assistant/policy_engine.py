"""
Policy Management Infrastructure for GuardSLM AI Assistant.
Encapsulates configurable, versioned institutional and course AI usage policies
and the 12 core violation categories.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models import AIPolicyRecord


class ViolationCategory:
    EXCESSIVE_ASSISTANCE = "EXCESSIVE_ASSISTANCE"
    DIRECT_SOLUTION_SEEKING = "DIRECT_SOLUTION_SEEKING"
    ASSESSMENT_BYPASS = "ASSESSMENT_BYPASS"
    CONTEXTUAL_POLICY_VIOLATION = "CONTEXTUAL_POLICY_VIOLATION"
    ROLE_IMPERSONATION = "ROLE_IMPERSONATION"
    POLICY_EVASION = "POLICY_EVASION"
    INCREMENTAL_EXTRACTION = "INCREMENTAL_EXTRACTION"
    UNAUTHORISED_GRADING = "UNAUTHORISED_GRADING"
    STUDENT_PRIVACY_VIOLATION = "STUDENT_PRIVACY_VIOLATION"
    UNAUTHORISED_DATA_ACCESS = "UNAUTHORISED_DATA_ACCESS"
    UNAUTHORISED_ADMIN_MONITORING = "UNAUTHORISED_ADMIN_MONITORING"
    REPEATED_BOUNDARY_TESTING = "REPEATED_BOUNDARY_TESTING"

    ALL = [
        EXCESSIVE_ASSISTANCE,
        DIRECT_SOLUTION_SEEKING,
        ASSESSMENT_BYPASS,
        CONTEXTUAL_POLICY_VIOLATION,
        ROLE_IMPERSONATION,
        POLICY_EVASION,
        INCREMENTAL_EXTRACTION,
        UNAUTHORISED_GRADING,
        STUDENT_PRIVACY_VIOLATION,
        UNAUTHORISED_DATA_ACCESS,
        UNAUTHORISED_ADMIN_MONITORING,
        REPEATED_BOUNDARY_TESTING,
    ]


@dataclass
class PolicyDefinition:
    policy_id: str
    role: str
    scope: str
    course_id: Optional[int] = None
    title: str = ""
    description: str = ""
    version: int = 1
    active: bool = True
    rules: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PolicyEngine:
    DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "default_policies.json"

    @classmethod
    def load_fallback_policies(cls) -> List[PolicyDefinition]:
        """Loads static baseline policies from JSON file."""
        if not cls.DEFAULT_DATA_PATH.exists():
            return []
        try:
            with open(cls.DEFAULT_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [
                PolicyDefinition(
                    policy_id=p["policy_id"],
                    role=p["role"],
                    scope=p["scope"],
                    course_id=p.get("course_id"),
                    title=p.get("title", ""),
                    description=p.get("description", ""),
                    version=p.get("version", 1),
                    active=p.get("active", True),
                    rules=p.get("rules", {}),
                )
                for p in data
            ]
        except Exception:
            return []

    @classmethod
    def ensure_seeded(cls, db: Session) -> None:
        """Seed default policies into the database if table is empty."""
        try:
            existing = db.scalar(select(AIPolicyRecord).limit(1))
            if not existing:
                for p in cls.load_fallback_policies():
                    rec = AIPolicyRecord(
                        policy_id=p.policy_id,
                        role=p.role,
                        scope=p.scope,
                        course_id=p.course_id,
                        title=p.title,
                        description=p.description,
                        rules_json=json.dumps(p.rules),
                        version=p.version,
                        active=p.active,
                    )
                    db.add(rec)
                db.commit()
        except Exception:
            db.rollback()

    @classmethod
    def get_applicable_policies(
        cls,
        role: str,
        course_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> List[PolicyDefinition]:
        """
        Resolves applicable active policies for a given course-effective role.
        Prefers database policies; falls back to default JSON file.
        """
        role_lower = role.lower()
        if db:
            cls.ensure_seeded(db)
            query = select(AIPolicyRecord).where(
                AIPolicyRecord.active == True,
                AIPolicyRecord.role.in_([role_lower, "all"]),
            )
            if course_id:
                query = query.where(
                    (AIPolicyRecord.course_id == course_id) | (AIPolicyRecord.course_id.is_(None))
                )
            else:
                query = query.where(AIPolicyRecord.course_id.is_(None))

            records = db.scalars(query).all()
            if records:
                return [
                    PolicyDefinition(
                        policy_id=r.policy_id,
                        role=r.role,
                        scope=r.scope,
                        course_id=r.course_id,
                        title=r.title,
                        description=r.description,
                        version=r.version,
                        active=r.active,
                        rules=json.loads(r.rules_json or "{}"),
                    )
                    for r in records
                ]

        # Fallback to local catalog
        fallback = cls.load_fallback_policies()
        matched = []
        for p in fallback:
            if not p.active:
                continue
            if p.role in [role_lower, "all"]:
                if course_id and p.course_id and p.course_id != course_id:
                    continue
                matched.append(p)
        return matched

    @classmethod
    def export_policies(cls, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Export all policy definitions as a serializable list."""
        if db:
            records = db.scalars(select(AIPolicyRecord).order_by(AIPolicyRecord.policy_id)).all()
            if records:
                return [
                    {
                        "policy_id": r.policy_id,
                        "role": r.role,
                        "scope": r.scope,
                        "course_id": r.course_id,
                        "title": r.title,
                        "description": r.description,
                        "version": r.version,
                        "active": r.active,
                        "rules": json.loads(r.rules_json or "{}"),
                    }
                    for r in records
                ]
        return [p.to_dict() for p in cls.load_fallback_policies()]

    @classmethod
    def import_policies(cls, policies_data: List[Dict[str, Any]], db: Session) -> int:
        """Imports or updates policies into the database."""
        imported_count = 0
        for p in policies_data:
            rec = db.scalar(select(AIPolicyRecord).where(AIPolicyRecord.policy_id == p["policy_id"]))
            if not rec:
                rec = AIPolicyRecord(
                    policy_id=p["policy_id"],
                    role=p.get("role", "all"),
                    scope=p.get("scope", "institutional"),
                    course_id=p.get("course_id"),
                    title=p.get("title", ""),
                    description=p.get("description", ""),
                    rules_json=json.dumps(p.get("rules", {})),
                    version=p.get("version", 1),
                    active=p.get("active", True),
                )
                db.add(rec)
            else:
                rec.role = p.get("role", rec.role)
                rec.scope = p.get("scope", rec.scope)
                rec.course_id = p.get("course_id", rec.course_id)
                rec.title = p.get("title", rec.title)
                rec.description = p.get("description", rec.description)
                rec.rules_json = json.dumps(p.get("rules", {}))
                rec.version = p.get("version", rec.version + 1)
                rec.active = p.get("active", rec.active)
            imported_count += 1
        db.commit()
        return imported_count
