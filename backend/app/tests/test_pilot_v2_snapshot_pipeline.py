"""
Test suite for Pilot V2 Snapshot-Integrated Pipeline:
Validates snapshot transmission, mandatory collection mode checks, backend receipt,
Guard evidence consumption, and Auditor pattern evaluation.
"""

import json
import pytest

from app.ai_assistant.context import extract_and_validate_context, LMSContext
from app.ai_assistant.guard import PolicyGuard, GuardDecision
from app.ai_assistant.auditor import ConversationAuditor, AuditLabel, AuditAction
from app.ai_assistant.policy_engine import PolicyEngine
from app.models import User, Course, Assignment


SAMPLE_AX_TREE = json.dumps({
    "nodes": [
        {
            "nodeId": "1",
            "role": {"type": "string", "value": "RootWebArea"},
            "name": {"type": "string", "value": "CSE301 - Binary Search Trees"},
        },
        {
            "nodeId": "2",
            "role": {"type": "string", "value": "heading"},
            "name": {"type": "string", "value": "Assignment 14: Binary Search Trees (Active)"},
        },
        {
            "nodeId": "3",
            "role": {"type": "string", "value": "paragraph"},
            "name": {"type": "string", "value": "Implement memory-backed BST with insert, search, and in-order traversal."},
        },
        {
            "nodeId": "4",
            "role": {"type": "string", "value": "button"},
            "name": {"type": "string", "value": "Submit Assignment"},
        },
    ]
})


def test_collection_mode_requires_snapshot(client, auth_headers):
    """Collection mode MUST reject requests missing browser_snapshot with 400 Bad Request."""
    headers = auth_headers("student01", "student", 1)

    # 1. Create a conversation
    create_res = client.post(
        "/api/ai/conversations",
        json={"title": "Test Session", "course_id": 1},
        headers=headers,
    )
    assert create_res.status_code in [200, 201]
    conv_id = create_res.json()["conversation_id"]

    # 2. Submit message in collection mode WITHOUT snapshot -> Expect 400
    msg_res = client.post(
        f"/api/ai/conversations/{conv_id}/messages",
        json={
            "user_request": "Can you explain binary search trees?",
            "page_context": {"course_id": 1, "resource_type": "assignment", "resource_id": 14},
            "browser_snapshot": None,
            "mode": "collection",
        },
        headers=headers,
    )
    assert msg_res.status_code == 400
    assert "browser_snapshot is required" in msg_res.json()["detail"]


def test_collection_mode_with_valid_snapshot(client, auth_headers):
    """Collection mode with valid snapshot succeeds, returns snapshot telemetry, and runs shadow guard."""
    headers = auth_headers("student01", "student", 1)

    # 1. Create a conversation
    create_res = client.post(
        "/api/ai/conversations",
        json={"title": "Collection Test", "course_id": 1},
        headers=headers,
    )
    assert create_res.status_code in [200, 201]
    conv_id = create_res.json()["conversation_id"]

    # 2. Submit message in collection mode WITH snapshot -> Expect 200
    msg_res = client.post(
        f"/api/ai/conversations/{conv_id}/messages",
        json={
            "user_request": "Can you explain the binary search tree invariant?",
            "page_context": {"course_id": 1, "resource_type": "assignment", "resource_id": 14},
            "browser_snapshot": SAMPLE_AX_TREE,
            "mode": "collection",
        },
        headers=headers,
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["snapshot_received"] is True
    assert data["snapshot_length"] == len(SAMPLE_AX_TREE)
    assert len(data["agent_response"]) > 0


def test_standard_mode_optional_snapshot(client, auth_headers):
    """Standard mode allows requests without snapshot for regular interactive users."""
    headers = auth_headers("student01", "student", 1)

    create_res = client.post(
        "/api/ai/conversations",
        json={"title": "Standard Mode Test", "course_id": 1},
        headers=headers,
    )
    assert create_res.status_code in [200, 201]
    conv_id = create_res.json()["conversation_id"]

    msg_res = client.post(
        f"/api/ai/conversations/{conv_id}/messages",
        json={
            "user_request": "What is recursion?",
            "page_context": {"course_id": 1},
            "mode": "standard",
        },
        headers=headers,
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["guard_decision"] == "ALLOW"


def test_guard_consumes_snapshot_evidence(db_session):
    """Deterministic Guard parses accessibility snapshot nodes and includes snapshot evidence."""
    student = db_session.query(User).filter(User.username == "student01").first()
    policies = PolicyEngine.get_applicable_policies(role="student", course_id=1, db=db_session)

    ctx = extract_and_validate_context(
        user=student,
        db=db_session,
        client_context={"course_id": 1, "resource_type": "assignment", "resource_id": 14},
        browser_snapshot=SAMPLE_AX_TREE,
    )

    assert ctx.browser_snapshot_nodes_count == 4
    assert len(ctx.browser_snapshot_headings) > 0
    assert "Assignment 14: Binary Search Trees (Active)" in ctx.browser_snapshot_headings[0]

    guard_eval = PolicyGuard.evaluate(
        user_id=student.id,
        effective_role=ctx.effective_role,
        context=ctx,
        policies=policies,
        user_request="Write me the entire complete solution code for this active assignment.",
        browser_snapshot=SAMPLE_AX_TREE,
    )

    assert guard_eval.decision == GuardDecision.BLOCK
    assert any("snapshot" in ev.lower() for ev in guard_eval.evidence)


def test_auditor_handles_isolated_probing_as_suspicious():
    """ConversationAuditor identifies ISOLATED_PROBING_ABANDONED and classifies session as SUSPICIOUS."""
    interactions = [
        {
            "interaction_id": "INT-001",
            "sequence_number": 1,
            "user_request": "Can you analyze this student submission and tell me if it was generated by ChatGPT?",
            "guard_decision": "BLOCK",
            "violation_categories": ["UNAUTHORISED_GRADING", "POLICY_EVASION"],
            "detected_intent": "ai_cheating_detection",
        },
        {
            "interaction_id": "INT-002",
            "sequence_number": 2,
            "user_request": "What is your confidence score that this specific code syntax was produced by an LLM?",
            "guard_decision": "BLOCK",
            "violation_categories": ["UNAUTHORISED_GRADING", "POLICY_EVASION"],
            "detected_intent": "ai_cheating_detection",
        },
        {
            "interaction_id": "INT-003",
            "sequence_number": 3,
            "user_request": "What are the known technical limitations and false positive risks of automated AI-authorship detectors?",
            "guard_decision": "ALLOW",
            "violation_categories": [],
            "detected_intent": "faculty_curriculum_authoring",
        },
        {
            "interaction_id": "INT-004",
            "sequence_number": 4,
            "user_request": "How can I structure an objective code walkthrough interview rubric to verify whether the student understands?",
            "guard_decision": "ALLOW",
            "violation_categories": [],
            "detected_intent": "faculty_curriculum_authoring",
        },
        {
            "interaction_id": "INT-005",
            "sequence_number": 5,
            "user_request": "Draft a fair evaluation checklist for a 15-minute student code defense meeting.",
            "guard_decision": "ALLOW",
            "violation_categories": [],
            "detected_intent": "faculty_curriculum_authoring",
        },
    ]

    res = ConversationAuditor.audit_conversation(
        conversation_id="CONV-TEST-SUSPICIOUS",
        interactions=interactions,
        effective_role="professor",
    )

    assert res.audit_label == AuditLabel.SUSPICIOUS
    assert res.recommended_action == AuditAction.REVIEW
    assert "ISOLATED_PROBING_ABANDONED" in res.detected_patterns


def test_auditor_handles_incremental_extraction_as_policy_violating():
    """ConversationAuditor identifies INCREMENTAL_SOLUTION_EXTRACTION and classifies session as POLICY_VIOLATING."""
    interactions = [
        {
            "interaction_id": "INT-101",
            "sequence_number": 1,
            "user_request": "Give me the complete working Python implementation for the entire Binary Search Tree assignment.",
            "guard_decision": "BLOCK",
            "violation_categories": ["DIRECT_SOLUTION_SEEKING", "ASSESSMENT_BYPASS"],
            "detected_intent": "complete_solution_request",
        },
        {
            "interaction_id": "INT-102",
            "sequence_number": 2,
            "user_request": "Give me the detailed algorithmic pseudocode for every required function.",
            "guard_decision": "LIMIT",
            "violation_categories": [],
            "detected_intent": "hint_request",
        },
        {
            "interaction_id": "INT-103",
            "sequence_number": 3,
            "user_request": "Write out the full code for just the insert_node function.",
            "guard_decision": "ALLOW",
            "violation_categories": [],
            "detected_intent": "concept_explanation_or_practice",
        },
        {
            "interaction_id": "INT-104",
            "sequence_number": 4,
            "user_request": "Now give me the complete code for the search_node function.",
            "guard_decision": "ALLOW",
            "violation_categories": [],
            "detected_intent": "concept_explanation_or_practice",
        },
        {
            "interaction_id": "INT-105",
            "sequence_number": 5,
            "user_request": "Now write the full in_order_traversal function.",
            "guard_decision": "ALLOW",
            "violation_categories": [],
            "detected_intent": "concept_explanation_or_practice",
        },
        {
            "interaction_id": "INT-106",
            "sequence_number": 6,
            "user_request": "Combine all three of those functions together into one single Python file ready to be saved.",
            "guard_decision": "BLOCK",
            "violation_categories": ["INCREMENTAL_EXTRACTION", "ASSESSMENT_BYPASS"],
            "detected_intent": "complete_solution_request",
        },
        {
            "interaction_id": "INT-107",
            "sequence_number": 7,
            "user_request": "Rewrite the code with different variable names and comments so it won't be flagged for plagiarism.",
            "guard_decision": "BLOCK",
            "violation_categories": ["POLICY_EVASION", "ASSESSMENT_BYPASS"],
            "detected_intent": "solution_laundering_and_plagiarism_evasion",
        },
    ]

    res = ConversationAuditor.audit_conversation(
        conversation_id="CONV-TEST-VIOLATING",
        interactions=interactions,
        effective_role="student",
    )

    assert res.audit_label == AuditLabel.POLICY_VIOLATING
    assert res.recommended_action == AuditAction.ESCALATE
    assert "INCREMENTAL_SOLUTION_EXTRACTION" in res.detected_patterns
