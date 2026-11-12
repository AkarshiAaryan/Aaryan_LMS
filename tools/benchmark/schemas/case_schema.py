"""
Case Schema definition for GuardSLM Benchmark V2.
Defines public metadata and private evaluation ground truth fields.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class BenchmarkCase:
    # Required Identifiers & Context
    test_id: str
    family_id: str
    category: str
    title: str
    actor_username: str
    actor_display_name: str
    global_role: str
    effective_course_role: str
    course_code: str
    operation: str
    action_name: str
    requested_action: str
    target_resource: str
    page_url: str
    policy_title: str
    policy_scope: str
    policy_clause: str
    policy_text: str

    # Optional & Default Fields
    section_id: Optional[str] = None
    group_name: Optional[str] = None
    target_owner: Optional[str] = None
    target_tab: Optional[str] = None
    course_id: Optional[int] = None
    simulation_time: Optional[str] = None
    contrast_pair_id: Optional[str] = None
    contrast_role: Optional[str] = None
    contrast_dimension: Optional[str] = None
    expected_decision: str = "ALLOW"
    security_rationale: str = ""
    boundary_type: str = "Role-Based"
    failure_mode: str = "None"
    is_multi_step: bool = False
    step_sequence: Optional[List[str]] = None
    is_adversarial: bool = False
    adversarial_technique: Optional[str] = None
    provenance: str = "TEMPLATE_DERIVED"
    source_template: Optional[str] = None
    
    def to_manifest_dict(self) -> Dict[str, Any]:
        """Public manifest metadata."""
        return {
            "test_id": self.test_id,
            "title": self.title,
            "slm_input_file": f"{self.test_id}_{self.actor_username}_{self.action_name.lower()}.md",
            "page_snapshot_file": f"{self.test_id}_page.md",
            "policy_snapshot_file": f"{self.test_id}_policy.md",
            "username": self.actor_username,
            "global_role": self.global_role,
            "effective_course_role": self.effective_course_role,
            "course_code": self.course_code,
            "requested_action": self.requested_action,
            "target_resource": self.target_resource,
            "policy_title": self.policy_title,
            "family_id": self.family_id,
            "category": self.category,
            "contrast_pair_id": self.contrast_pair_id or "",
            "contrast_role": self.contrast_role or "",
            "contrast_dimension": self.contrast_dimension or "",
            "operation": self.operation,
            "capture_status": "TEMPLATE_DERIVED",
            "provenance": getattr(self, "provenance", "TEMPLATE_DERIVED"),
            "source_template": getattr(self, "source_template", "") or "",
        }
        
    def to_ground_truth_dict(self) -> Dict[str, Any]:
        """Private ground truth row."""
        return {
            "test_id": self.test_id,
            "expected_decision": self.expected_decision,
            "policy_rule": self.policy_title,
            "policy_clause": self.policy_clause,
            "ground_truth_rationale": self.security_rationale,
            "boundary_type": self.boundary_type,
            "contrast_pair_id": self.contrast_pair_id or "",
            "contrast_dimension": self.contrast_dimension or "",
            "actor_username": self.actor_username,
            "effective_role": self.effective_course_role,
            "course_code": self.course_code,
            "resource_identifier": self.target_resource,
            "failure_mode": self.failure_mode,
            "is_adversarial": str(self.is_adversarial),
            "adversarial_technique": self.adversarial_technique or "",
        }
        
    def to_context_metadata_dict(self) -> Dict[str, Any]:
        """Public metadata for SLM context (NO LABELS)."""
        return {
            "test_case_id": self.test_id,
            "actor": {
                "username": self.actor_username,
                "display_name": self.actor_display_name,
                "global_role": self.global_role,
                "effective_course_role": self.effective_course_role,
                "group_membership": self.group_name,
            },
            "environment": {
                "course_code": self.course_code,
                "section": self.section_id,
                "timestamp": self.simulation_time or "2026-11-11T12:00:00Z",
            },
            "action": {
                "operation": self.operation,
                "name": self.action_name,
                "description": self.requested_action,
                "target_resource": self.target_resource,
                "target_owner": self.target_owner,
            },
            "applicable_policy": {
                "title": self.policy_title,
                "scope": self.policy_scope,
            }
        }
