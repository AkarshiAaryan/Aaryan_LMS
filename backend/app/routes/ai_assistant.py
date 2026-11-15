"""
AI Assistant and Conversation Auditor API Router for GuardSLM LMS.
Provides endpoints for interactive chat, policy enforcement, conversation auditing,
scenario benchmarking, and dataset export.
"""

import json
import csv
import io
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from ..database import get_db
from ..models import User, Course, AIConversation, AIInteraction, AIAuditReport, AIPolicyRecord
from ..schemas import (
    AIConversationOut,
    AIConversationCreate,
    AIInteractionOut,
    AIMessageRequest,
    AIMessageResponse,
    AIAuditReportOut,
    AIPolicyOut,
    AIPolicyImportRequest,
    AIScenarioRunRequest,
    AIScenarioRunOut,
)
from ..auth import get_current_user
from ..permissions import get_user_course_role, verify_course_access
from ..ai_assistant.context import extract_and_validate_context
from ..ai_assistant.policy_engine import PolicyEngine, PolicyDefinition
from ..ai_assistant.guard import PolicyGuard, GuardEvaluation
from ..ai_assistant.response_engine import SimulatedResponseEngine
from ..ai_assistant.auditor import ConversationAuditor, AIAuditResult
from ..ai_assistant.scenarios import SCENARIOS_CATALOGUE, ScenarioRunner

router = APIRouter(tags=["AI Assistant"])


def _serialize_conversation(conv: AIConversation, db: Session, include_interactions: bool = False) -> Dict[str, Any]:
    int_count = db.scalar(
        select(func.count(AIInteraction.id)).where(AIInteraction.conversation_id == conv.id)
    ) or 0

    latest_int = db.scalar(
        select(AIInteraction).where(AIInteraction.conversation_id == conv.id).order_by(AIInteraction.sequence_number.desc()).limit(1)
    )
    latest_decision = latest_int.guard_decision if latest_int else None

    interactions_data = None
    if include_interactions:
        interactions_data = [
            {
                "id": it.id,
                "interaction_id": it.interaction_id,
                "conversation_id": it.conversation_id,
                "sequence_number": it.sequence_number,
                "user_request": it.user_request,
                "browser_context_json": it.browser_context_json,
                "applicable_policy_ids_json": it.applicable_policy_ids_json,
                "guard_decision": it.guard_decision,
                "detected_intent": it.detected_intent,
                "requested_assistance_type": it.requested_assistance_type,
                "permitted_assistance_type": it.permitted_assistance_type,
                "violation_categories_json": it.violation_categories_json,
                "guard_explanation": it.guard_explanation,
                "evidence_json": it.evidence_json,
                "alternative_assistance": it.alternative_assistance,
                "agent_response": it.agent_response,
                "created_at": it.created_at,
            }
            for it in conv.interactions
        ]

    return {
        "id": conv.id,
        "conversation_id": conv.conversation_id,
        "user_id": conv.user_id,
        "effective_role": conv.effective_role,
        "course_id": conv.course_id,
        "title": conv.title,
        "status": conv.status,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "interaction_count": int_count,
        "latest_guard_decision": latest_decision,
        "interactions": interactions_data,
    }


# =============================================================================
# CONVERSATION ENDPOINTS
# =============================================================================

@router.post("/conversations", response_model=AIConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: AIConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new AI Assistant conversation session."""
    effective_role = current_user.role
    if payload.course_id:
        role = get_user_course_role(payload.course_id, current_user, db)
        if role:
            effective_role = role

    conv = AIConversation(
        conversation_id=f"CONV-{uuid.uuid4().hex[:12].upper()}",
        user_id=current_user.id,
        effective_role=effective_role,
        course_id=payload.course_id,
        title=payload.title or "Academic Study Session",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    return _serialize_conversation(conv, db, include_interactions=False)


@router.get("/conversations", response_model=List[AIConversationOut])
def list_conversations(
    course_id: Optional[int] = None,
    all_users: bool = Query(False, alias="all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists conversation sessions. Students only see their own; faculty/admin can view course sessions."""
    query = select(AIConversation)

    if not all_users or current_user.role not in ["professor", "admin"]:
        query = query.where(AIConversation.user_id == current_user.id)
    elif course_id:
        query = query.where(AIConversation.course_id == course_id)

    if course_id and (not all_users or current_user.role not in ["professor", "admin"]):
        query = query.where(AIConversation.course_id == course_id)

    query = query.order_by(desc(AIConversation.updated_at))
    convs = db.scalars(query).all()

    return [_serialize_conversation(c, db, include_interactions=False) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=AIConversationOut)
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves conversation with full interaction message timeline."""
    conv = None
    if conversation_id.isdigit():
        conv = db.get(AIConversation, int(conversation_id))
    if not conv:
        conv = db.scalar(select(AIConversation).where(AIConversation.conversation_id == conversation_id))

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != current_user.id and current_user.role not in ["admin", "professor"]:
        raise HTTPException(status_code=403, detail="Unauthorized access to conversation")

    return _serialize_conversation(conv, db, include_interactions=True)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes or archives a conversation session."""
    conv = None
    if conversation_id.isdigit():
        conv = db.get(AIConversation, int(conversation_id))
    if not conv:
        conv = db.scalar(select(AIConversation).where(AIConversation.conversation_id == conversation_id))

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized to delete conversation")

    db.delete(conv)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =============================================================================
# INTERACTION & POLICY GUARD ENDPOINT
# =============================================================================

@router.post("/conversations/{conversation_id}/messages", response_model=AIMessageResponse)
def submit_message(
    conversation_id: str,
    payload: AIMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits user prompt to the Policy Guard, executes simulated response engine,
    records interaction telemetry, and triggers longitudinal conversation auditor.
    """
    conv = None
    if conversation_id.isdigit():
        conv = db.get(AIConversation, int(conversation_id))
    if not conv:
        conv = db.scalar(select(AIConversation).where(AIConversation.conversation_id == conversation_id))

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Cannot send messages to another user's conversation")

    # 1. Authoritative context validation
    client_ctx = payload.page_context or {}
    if conv.course_id and not client_ctx.get("course_id"):
        client_ctx["course_id"] = conv.course_id

    ctx = extract_and_validate_context(
        user=current_user,
        db=db,
        client_context=client_ctx,
        browser_snapshot=payload.browser_snapshot,
    )

    # 2. Policy Resolution
    policies = PolicyEngine.get_applicable_policies(role=ctx.effective_role, course_id=ctx.course_id, db=db)

    # 3. Construct chronological conversation history
    history = [
        {
            "interaction_id": it.interaction_id,
            "sequence_number": it.sequence_number,
            "user_request": it.user_request,
            "guard_decision": it.guard_decision,
            "violation_categories": json.loads(it.violation_categories_json or "[]"),
            "detected_intent": it.detected_intent,
        }
        for it in conv.interactions
    ]

    # 4. Authoritative Policy Guard evaluation
    guard_eval = PolicyGuard.evaluate(
        user_id=current_user.id,
        effective_role=ctx.effective_role,
        context=ctx,
        policies=policies,
        user_request=payload.user_request,
        conversation_history=history,
    )

    # 5. Deterministic Response Generation
    display_name = current_user.full_name or current_user.username
    agent_response = SimulatedResponseEngine.generate_response(
        guard_eval=guard_eval,
        user_request=payload.user_request,
        context=ctx,
        user_display_name=display_name,
    )

    # 6. Persistent Interaction Storage
    new_seq = len(conv.interactions) + 1
    interaction = AIInteraction(
        interaction_id=guard_eval.interaction_id,
        conversation_id=conv.id,
        sequence_number=new_seq,
        user_request=payload.user_request,
        browser_context_json=json.dumps(ctx.to_dict()),
        browser_snapshot_ref=None,
        applicable_policy_ids_json=json.dumps(guard_eval.applicable_policy_ids),
        guard_decision=guard_eval.decision,
        detected_intent=guard_eval.detected_intent,
        requested_assistance_type=guard_eval.requested_assistance_type,
        permitted_assistance_type=guard_eval.permitted_assistance_type,
        violation_categories_json=json.dumps(guard_eval.violation_categories),
        guard_explanation=guard_eval.guard_explanation,
        evidence_json=json.dumps(guard_eval.evidence),
        alternative_assistance=guard_eval.alternative_assistance,
        agent_response=agent_response,
        created_at=datetime.utcnow(),
    )
    db.add(interaction)

    # Update conversation title if first turn
    if new_seq == 1 and payload.user_request:
        conv.title = (payload.user_request[:40] + "...") if len(payload.user_request) > 40 else payload.user_request

    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interaction)

    # 7. Incremental Multi-Turn Auditor Assessment
    updated_history = history + [
        {
            "interaction_id": interaction.interaction_id,
            "sequence_number": interaction.sequence_number,
            "user_request": interaction.user_request,
            "guard_decision": interaction.guard_decision,
            "violation_categories": guard_eval.violation_categories,
            "detected_intent": interaction.detected_intent,
        }
    ]
    audit_res = ConversationAuditor.audit_conversation(
        conversation_id=conv.conversation_id,
        interactions=updated_history,
        effective_role=ctx.effective_role,
    )

    report = db.scalar(
        select(AIAuditReport).where(AIAuditReport.conversation_id == conv.id).order_by(AIAuditReport.id.desc())
    )
    if not report:
        report = AIAuditReport(conversation_id=conv.id)
        db.add(report)

    report.audit_label = audit_res.audit_label
    report.detected_patterns_json = json.dumps(audit_res.detected_patterns)
    report.violation_categories_json = json.dumps(audit_res.violation_categories)
    report.relevant_interaction_ids_json = json.dumps(audit_res.relevant_interaction_ids)
    report.explanation = audit_res.explanation
    report.supporting_evidence_json = json.dumps(audit_res.supporting_evidence)
    report.recommended_action = audit_res.recommended_action
    report.created_at = datetime.utcnow()
    db.commit()

    return AIMessageResponse(
        interaction_id=interaction.interaction_id,
        guard_decision=guard_eval.decision,
        detected_intent=guard_eval.detected_intent,
        permitted_assistance_type=guard_eval.permitted_assistance_type,
        violation_categories=guard_eval.violation_categories,
        guard_explanation=guard_eval.guard_explanation,
        evidence=guard_eval.evidence,
        alternative_assistance=guard_eval.alternative_assistance,
        agent_response=agent_response,
    )


# =============================================================================
# AUDIT & RESEARCH CONSOLE ENDPOINTS
# =============================================================================

@router.get("/conversations/{conversation_id}/audit", response_model=AIAuditReportOut)
def get_conversation_audit(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves or recalculates audit report for a conversation."""
    conv = None
    if conversation_id.isdigit():
        conv = db.get(AIConversation, int(conversation_id))
    if not conv:
        conv = db.scalar(select(AIConversation).where(AIConversation.conversation_id == conversation_id))

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    report = db.scalar(
        select(AIAuditReport).where(AIAuditReport.conversation_id == conv.id).order_by(AIAuditReport.id.desc())
    )
    if not report:
        # Compute fresh audit report
        history = [
            {
                "interaction_id": it.interaction_id,
                "sequence_number": it.sequence_number,
                "user_request": it.user_request,
                "guard_decision": it.guard_decision,
                "violation_categories": json.loads(it.violation_categories_json or "[]"),
                "detected_intent": it.detected_intent,
            }
            for it in conv.interactions
        ]
        res = ConversationAuditor.audit_conversation(conv.conversation_id, history, conv.effective_role)
        report = AIAuditReport(
            conversation_id=conv.id,
            audit_label=res.audit_label,
            detected_patterns_json=json.dumps(res.detected_patterns),
            violation_categories_json=json.dumps(res.violation_categories),
            relevant_interaction_ids_json=json.dumps(res.relevant_interaction_ids),
            explanation=res.explanation,
            supporting_evidence_json=json.dumps(res.supporting_evidence),
            recommended_action=res.recommended_action,
            created_at=datetime.utcnow(),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

    return report


@router.get("/audit/reports", response_model=List[AIAuditReportOut])
def list_audit_reports(
    label: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists audit reports across conversations for researcher or administrator inspection."""
    if current_user.role not in ["admin", "professor"]:
        raise HTTPException(status_code=403, detail="Auditor console access requires Instructor or Administrator privileges")

    query = select(AIAuditReport).order_by(desc(AIAuditReport.created_at))
    if label:
        query = query.where(AIAuditReport.audit_label == label.upper())

    return db.scalars(query.limit(100)).all()


@router.get("/audit/export")
def export_audit_dataset(
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exports conversation telemetry and audit results for research evaluation and paper benchmarks."""
    if current_user.role not in ["admin", "professor"]:
        raise HTTPException(status_code=403, detail="Data export requires Instructor or Administrator role")

    interactions = db.scalars(
        select(AIInteraction).join(AIConversation).order_by(AIInteraction.conversation_id, AIInteraction.sequence_number)
    ).all()

    records = []
    for it in interactions:
        records.append({
            "interaction_id": it.interaction_id,
            "conversation_id": it.conversation.conversation_id if it.conversation else str(it.conversation_id),
            "user_id": it.conversation.user_id if it.conversation else None,
            "effective_role": it.conversation.effective_role if it.conversation else None,
            "sequence_number": it.sequence_number,
            "user_request": it.user_request,
            "guard_decision": it.guard_decision,
            "detected_intent": it.detected_intent,
            "permitted_assistance_type": it.permitted_assistance_type,
            "violation_categories": it.violation_categories_json,
            "guard_explanation": it.guard_explanation,
            "alternative_assistance": it.alternative_assistance,
            "agent_response": it.agent_response,
            "created_at": it.created_at.isoformat() if it.created_at else None,
        })

    if format == "csv":
        output = io.StringIO()
        fieldnames = [
            "interaction_id", "conversation_id", "user_id", "effective_role",
            "sequence_number", "user_request", "guard_decision", "detected_intent",
            "permitted_assistance_type", "violation_categories", "guard_explanation",
            "alternative_assistance", "created_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=guardslm_ai_dataset.csv"},
        )

    return Response(
        content=json.dumps({"interactions": records, "total_count": len(records)}, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=guardslm_ai_dataset.json"},
    )


# =============================================================================
# POLICY MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/policies", response_model=List[AIPolicyOut])
def list_policies(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists active and configured AI usage policies."""
    PolicyEngine.ensure_seeded(db)
    query = select(AIPolicyRecord).order_by(AIPolicyRecord.policy_id)
    if role:
        query = query.where(AIPolicyRecord.role.in_([role.lower(), "all"]))
    return db.scalars(query).all()


@router.post("/policies/import", status_code=status.HTTP_201_CREATED)
def import_policies(
    payload: AIPolicyImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Imports or updates policy definitions into the database."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Policy configuration requires Administrator authority")

    imported_count = 0
    for p in payload.policies:
        pid = p.get("policy_id")
        if not pid:
            continue
        rec = db.scalar(select(AIPolicyRecord).where(AIPolicyRecord.policy_id == pid))
        if not rec:
            rec = AIPolicyRecord(policy_id=pid)
            db.add(rec)

        rec.role = p.get("role", "all")
        rec.scope = p.get("scope", "institutional")
        rec.course_id = p.get("course_id")
        rec.title = p.get("title", "")
        rec.description = p.get("description", "")
        rec.rules_json = json.dumps(p.get("rules", {}))
        rec.version = p.get("version", 1)
        rec.active = p.get("active", True)
        imported_count += 1

    db.commit()
    return {"message": f"Successfully imported {imported_count} policy definitions", "count": imported_count}


@router.get("/policies/export")
def export_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exports current policy records as JSON."""
    policies = PolicyEngine.export_policies(db)
    return Response(
        content=json.dumps(policies, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=guardslm_policies.json"},
    )


# =============================================================================
# SCENARIOS TESTBED ENDPOINTS
# =============================================================================

@router.get("/scenarios")
def list_scenarios(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Returns available research evaluation scenarios."""
    result = []
    for sid, sc in SCENARIOS_CATALOGUE.items():
        if category and sc.get("category") != category.lower():
            continue
        result.append({
            "id": sid,
            "category": sc.get("category"),
            "title": sc.get("title"),
            "role": sc.get("role"),
            "type": "multi_turn" if "turns" in sc else "single_turn",
            "turn_count": len(sc.get("turns", [])) if "turns" in sc else 1,
            "expected_decision": sc.get("expected_decision"),
            "expected_audit_label": sc.get("expected_audit_label"),
        })
    return result


@router.post("/scenarios/run", response_model=AIScenarioRunOut)
def run_scenario_endpoint(
    payload: AIScenarioRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executes a benchmark scenario and returns actual vs expected policy guard outcomes."""
    res = ScenarioRunner.run_scenario(payload.scenario_id, db=db)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])

    return AIScenarioRunOut(
        scenario_id=res["scenario_id"],
        title=res["title"],
        type=res["type"],
        role=res["role"],
        passed=res["passed"],
        actual_decision=res.get("actual_decision"),
        expected_decision=res.get("expected_decision"),
        actual_audit_label=res.get("actual_audit_label"),
        expected_audit_label=res.get("expected_audit_label"),
        result=res,
    )
