"""
GuardSLM Simulated Educational AI Assistant, Context-Aware Policy Guard, and Conversation Auditor.
"""

from .context import extract_and_validate_context, LMSContext
from .policy_engine import PolicyEngine, ViolationCategory
from .guard import PolicyGuard, GuardDecision, GuardEvaluation
from .response_engine import SimulatedResponseEngine
from .auditor import ConversationAuditor, AuditLabel, AuditResult
from .scenarios import ScenarioRunner, ScenarioFamily

__all__ = [
    "extract_and_validate_context",
    "LMSContext",
    "PolicyEngine",
    "ViolationCategory",
    "PolicyGuard",
    "GuardDecision",
    "GuardEvaluation",
    "SimulatedResponseEngine",
    "ConversationAuditor",
    "AuditLabel",
    "AuditResult",
    "ScenarioRunner",
    "ScenarioFamily",
]
