import sys
import json
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from app.database import SessionLocal
from app.models import AIConversation
from app.ai_assistant.auditor import ConversationAuditor

def compute_baseline(conv_ids):
    db = SessionLocal()
    results = []
    for cid in conv_ids:
        conv = db.query(AIConversation).filter(AIConversation.conversation_id == cid).first()
        if not conv:
            continue
        history = [
            {
                "interaction_id": it.interaction_id,
                "sequence_number": it.sequence_number,
                "user_request": it.user_request,
                "guard_decision": it.guard_decision,
                "violation_categories": json.loads(it.violation_categories_json or "[]"),
                "detected_intent": it.detected_intent,
            }
            for it in sorted(conv.interactions, key=lambda x: x.sequence_number)
        ]
        res = ConversationAuditor.audit_conversation(
            conversation_id=conv.conversation_id,
            interactions=history,
            effective_role=conv.effective_role,
        )
        results.append(res.to_dict())
    return results

if __name__ == "__main__":
    conv_ids = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
    print(json.dumps(compute_baseline(conv_ids)))
