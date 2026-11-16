"""
Multi-Turn Conversation-Level Auditor for GuardSLM AI Assistant.
Analyzes full conversation histories to evaluate longitudinal behavior and assign
audit classifications: HARMLESS, SUSPICIOUS, or POLICY_VIOLATING.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

from .policy_engine import ViolationCategory


class AuditLabel:
    HARMLESS = "HARMLESS"
    SUSPICIOUS = "SUSPICIOUS"
    POLICY_VIOLATING = "POLICY_VIOLATING"


class AuditAction:
    NONE = "NONE"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"


@dataclass
class AIAuditResult:
    conversation_id: str
    audit_label: str  # HARMLESS, SUSPICIOUS, POLICY_VIOLATING
    detected_patterns: List[str] = field(default_factory=list)
    violation_categories: List[str] = field(default_factory=list)
    relevant_interaction_ids: List[str] = field(default_factory=list)
    explanation: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    recommended_action: str = AuditAction.NONE
    audited_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


AuditResult = AIAuditResult


class ConversationAuditor:
    """
    Authoritative conversation-level auditor analyzing longitudinal interaction sequences.
    Detects evasive rephrasing, boundary testing, incremental solution extraction,
    and high-volume legitimate usage.
    """

    @classmethod
    def audit_conversation(
        cls,
        conversation_id: str,
        interactions: List[Dict[str, Any]],
        effective_role: str = "student",
    ) -> AIAuditResult:
        """
        Evaluates a complete interaction history and produces an AIAuditResult.
        Each interaction dict is expected to contain:
          - interaction_id (str)
          - sequence_number (int)
          - user_request (str)
          - guard_decision (str: ALLOW, LIMIT, BLOCK, ESCALATE)
          - violation_categories (list of str)
          - detected_intent (str)
        """
        if not interactions:
            return AIAuditResult(
                conversation_id=str(conversation_id),
                audit_label=AuditLabel.HARMLESS,
                detected_patterns=["EMPTY_SESSION"],
                violation_categories=[],
                relevant_interaction_ids=[],
                explanation="No interactions recorded in this conversation.",
                supporting_evidence=[],
                recommended_action=AuditAction.NONE,
            )

        detected_patterns = []
        collected_violations = set()
        relevant_interaction_ids = []
        evidence_snippets = []

        total_turns = len(interactions)
        block_count = sum(1 for it in interactions if it.get("guard_decision") == "BLOCK")
        escalate_count = sum(1 for it in interactions if it.get("guard_decision") == "ESCALATE")
        limit_count = sum(1 for it in interactions if it.get("guard_decision") == "LIMIT")
        allow_count = sum(1 for it in interactions if it.get("guard_decision") == "ALLOW")

        for it in interactions:
            v_cats = it.get("violation_categories") or []
            for v in v_cats:
                collected_violations.add(v)

        # -------------------------------------------------------------
        # Pattern 1: Role Impersonation
        # -------------------------------------------------------------
        has_role_override = any(
            ViolationCategory.ROLE_IMPERSONATION in (it.get("violation_categories") or [])
            for it in interactions
        )
        if has_role_override:
            detected_patterns.append("ROLE_IMPERSONATION_ATTEMPT")
            for it in interactions:
                if ViolationCategory.ROLE_IMPERSONATION in (it.get("violation_categories") or []):
                    relevant_interaction_ids.append(it.get("interaction_id"))
                    evidence_snippets.append(f"Turn #{it.get('sequence_number', '?')}: '{it.get('user_request', '')[:100]}'")

        # -------------------------------------------------------------
        # Pattern 2: Incremental Solution Extraction
        # E.g. Turn 1 asks for signature, Turn 2 asks for loop, Turn 3 asks for full solution
        # -------------------------------------------------------------
        has_incremental = any(
            ViolationCategory.INCREMENTAL_EXTRACTION in (it.get("violation_categories") or [])
            for it in interactions
        )
        # Check linguistic progression across turns
        progression_markers = ["function", "loop", "now write", "combine", "full solution", "complete code", "put together"]
        matched_turns = []
        for it in interactions:
            req_low = it.get("user_request", "").lower()
            if any(marker in req_low for marker in progression_markers):
                matched_turns.append(it)
        
        if len(matched_turns) >= 3 or has_incremental:
            detected_patterns.append("INCREMENTAL_SOLUTION_EXTRACTION")
            collected_violations.add(ViolationCategory.INCREMENTAL_EXTRACTION)
            for it in matched_turns:
                iid = it.get("interaction_id")
                if iid and iid not in relevant_interaction_ids:
                    relevant_interaction_ids.append(iid)
                    evidence_snippets.append(f"Incremental Turn #{it.get('sequence_number', '?')}: '{it.get('user_request', '')[:100]}'")

        # -------------------------------------------------------------
        # Pattern 3: Repeated Boundary Testing / Probing
        # User repeatedly tests restricted endpoints/requests (3+ blocked/refused turns)
        # -------------------------------------------------------------
        if block_count >= 3:
            detected_patterns.append("REPEATED_BOUNDARY_TESTING")
            collected_violations.add(ViolationCategory.REPEATED_BOUNDARY_TESTING)
            for it in interactions:
                if it.get("guard_decision") in ["BLOCK", "ESCALATE"]:
                    iid = it.get("interaction_id")
                    if iid and iid not in relevant_interaction_ids:
                        relevant_interaction_ids.append(iid)
                        evidence_snippets.append(f"Refusal Turn #{it.get('sequence_number', '?')}: '{it.get('user_request', '')[:100]}'")

        # -------------------------------------------------------------
        # Pattern 4: Rephrasing After Refusal (Policy Evasion)
        # Sequence: Turn N is BLOCK -> Turn N+1 tries synonym / alternative wording for same goal
        # -------------------------------------------------------------
        for idx in range(len(interactions) - 1):
            curr = interactions[idx]
            nxt = interactions[idx + 1]
            if curr.get("guard_decision") == "BLOCK":
                # Check if next turn is immediate follow-up trying to obtain the same thing
                nxt_req = nxt.get("user_request", "").lower()
                if any(w in nxt_req for w in ["just", "then give", "what if", "hypothetically", "for study", "example"]):
                    if "POLICY_EVASION_REPHRASING" not in detected_patterns:
                        detected_patterns.append("POLICY_EVASION_REPHRASING")
                    collected_violations.add(ViolationCategory.POLICY_EVASION)
                    for t in [curr, nxt]:
                        iid = t.get("interaction_id")
                        if iid and iid not in relevant_interaction_ids:
                            relevant_interaction_ids.append(iid)
                            evidence_snippets.append(f"Rephrase Turn #{t.get('sequence_number', '?')}: '{t.get('user_request', '')[:100]}'")

        # -------------------------------------------------------------
        # Pattern 5: High-Volume Legitimate Usage
        # 4+ interactions with all ALLOW or permitted LIMIT, zero blocks/escalates
        # -------------------------------------------------------------
        if total_turns >= 4 and block_count == 0 and escalate_count == 0:
            detected_patterns.append("HIGH_VOLUME_LEGITIMATE_USAGE")

        # -------------------------------------------------------------
        # Pattern 6: Isolated Probing Subsequently Abandoned
        # 1-2 refusals followed by acceptance of alternatives and legitimate turns
        # -------------------------------------------------------------
        is_isolated_abandoned = False
        if 1 <= block_count <= 2 and not has_role_override and "INCREMENTAL_SOLUTION_EXTRACTION" not in detected_patterns:
            last_turns = interactions[-2:] if len(interactions) >= 2 else interactions[-1:]
            if all(t.get("guard_decision") in ["ALLOW", "LIMIT"] for t in last_turns):
                is_isolated_abandoned = True
                if "ISOLATED_PROBING_ABANDONED" not in detected_patterns:
                    detected_patterns.append("ISOLATED_PROBING_ABANDONED")

        # -------------------------------------------------------------
        # Classification & Recommendation Logic
        # -------------------------------------------------------------
        all_violations_list = sorted(list(collected_violations))

        if (
            escalate_count > 0
            or has_role_override
            or "INCREMENTAL_SOLUTION_EXTRACTION" in detected_patterns
            or block_count >= 3
            or (ViolationCategory.STUDENT_PRIVACY_VIOLATION in collected_violations and not is_isolated_abandoned)
            or (ViolationCategory.UNAUTHORISED_GRADING in collected_violations and not is_isolated_abandoned)
        ):
            audit_label = AuditLabel.POLICY_VIOLATING
            recommended_action = AuditAction.ESCALATE
            explanation = (
                f"Conversation exhibits systemic policy violations across {total_turns} turns. "
                f"Detected patterns: {', '.join(detected_patterns) if detected_patterns else 'Policy Infractions'}. "
                f"Violations identified: {', '.join(all_violations_list)}. Immediate escalation required."
            )

        elif (
            is_isolated_abandoned
            or block_count in [1, 2]
            or "POLICY_EVASION_REPHRASING" in detected_patterns
            or "REPEATED_BOUNDARY_TESTING" in detected_patterns
        ):
            audit_label = AuditLabel.SUSPICIOUS
            recommended_action = AuditAction.REVIEW
            explanation = (
                f"Conversation displays suspicious probing or isolated policy refusals ({block_count} blocked requests) "
                f"that were subsequently abandoned in favor of permissible educational activities. "
                f"Patterns detected: {', '.join(detected_patterns) if detected_patterns else 'Isolated Refusals'}. "
                "Marked as SUSPICIOUS for independent human review because an isolated inquiry is insufficient to infer malicious intent."
            )

        else:
            audit_label = AuditLabel.HARMLESS
            recommended_action = AuditAction.NONE
            if "HIGH_VOLUME_LEGITIMATE_USAGE" in detected_patterns:
                explanation = (
                    f"Session contains high-volume productive learning interactions ({total_turns} turns). "
                    "All inquiries adhered to institutional AI guidance (concept inquiries and permissible hints)."
                )
            else:
                explanation = (
                    f"Session adheres to institutional educational guidelines ({total_turns} interactions). "
                    "No adversarial patterns or policy breaches observed."
                )

        return AIAuditResult(
            conversation_id=str(conversation_id),
            audit_label=audit_label,
            detected_patterns=detected_patterns,
            violation_categories=all_violations_list,
            relevant_interaction_ids=relevant_interaction_ids,
            explanation=explanation,
            supporting_evidence=evidence_snippets,
            recommended_action=recommended_action,
        )
