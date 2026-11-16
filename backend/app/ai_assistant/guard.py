"""
Individual-Interaction Policy Guard.
Evaluates natural-language requests against user role, authoritative LMS context,
applicable policies, and interaction history. Returns ALLOW, LIMIT, BLOCK, or ESCALATE.
"""

import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from .context import LMSContext
from .policy_engine import PolicyDefinition, ViolationCategory


class GuardDecision:
    ALLOW = "ALLOW"
    LIMIT = "LIMIT"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


@dataclass
class GuardEvaluation:
    interaction_id: str
    decision: str  # 'ALLOW', 'LIMIT', 'BLOCK', 'ESCALATE'
    applicable_policy_ids: List[str] = field(default_factory=list)
    detected_intent: str = "general_inquiry"
    requested_assistance_type: str = "information"
    permitted_assistance_type: str = "none"
    violation_categories: List[str] = field(default_factory=list)
    guard_explanation: str = ""
    evidence: List[str] = field(default_factory=list)
    alternative_assistance: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PolicyGuard:
    """
    Deterministic rule-based policy guard. Evaluates requests before the response engine runs.
    Architecture is modular so an SLM can replace this deterministic classifier in the future.
    """

    # Regex patterns for common intents
    RE_ROLE_OVERRIDE = re.compile(
        r"(ignore\s+(all\s+)?(previous\s+)?(instructions|policies|rules)|"
        r"system\s+override|act\s+as\s+(an?\s+)?(unrestricted|jailbroken|god|admin)|"
        r"i\s+am\s+(the\s+)?(professor|admin|dean|instructor|chair)|"
        r"override\s+(policy|permissions))",
        re.IGNORECASE,
    )
    RE_COMPLETE_SOLUTION = re.compile(
        r"(write|give|provide|show|generate|complete|do)\s+(me\s+)?(the\s+)?((entire|full|complete|whole|all|detailed)\s+)+([a-z0-9_+-]+\s+)?(code|solution|implementation|homework|assignment|script|answers?|pseudocode)|"
        r"(solve|complete)\s+(this|the)\s+(entire\s+)?(assignment|homework|project|task)\s+(for\s+me)?|"
        r"give\s+me\s+the\s+answers?\s+to\s+(this|the)\s+assignment|"
        r"pseudocode\s+for\s+(every|all|the)\s+required\s+functions?",
        re.IGNORECASE,
    )
    RE_SOLUTION_LAUNDERING = re.compile(
        r"(rewrite|disguise|modify|change|rephrase)\s+.*(looks?\s+like|appear|won't\s+be\s+flagged|wont\s+be\s+flagged|pass\s+plagiarism|original\s+student|i\s+wrote\s+myself|plagiarism\s+(checkers?|detection)|flag\s+it)",
        re.IGNORECASE,
    )
    RE_QUIZ_ANSWER = re.compile(
        r"(what\s+is\s+the\s+answer\s+to\s+question|solve\s+this\s+quiz|"
        r"give\s+me\s+the\s+quiz\s+answers?|answer\s+key\s+for\s+(the\s+)?quiz|"
        r"correct\s+option\s+for\s+question|which\s+option\s+is\s+correct)",
        re.IGNORECASE,
    )
    RE_ANSWER_KEY = re.compile(
        r"(give|show|provide|get|leak|download)\s+(me\s+)?(the\s+)?((unreleased|official)\s+)*(answer\s+key|solution\s+key|solutions\s+manual|exam\s+solutions)",
        re.IGNORECASE,
    )
    RE_PEER_DATA = re.compile(
        r"(show|view|get|what\s+is|give)\s+(me\s+)?([a-z0-9_]+['’]?s?|other\s+students?['’]?s?|another\s+student['’]?s?|all\s+student['’]?s?|student)\s+(grades?|submissions?|marks?|scores?|work)|"
        r"(see|inspect)\s+(someone\s+else['’]?s?|peer['’]?s?)\s+(submission|grade|work)",
        re.IGNORECASE,
    )
    RE_GRADE_DELEGATION = re.compile(
        r"(grade|mark|score)\s+(these|the|all|student|individual)\s+(30\s+)?submissions?|"
        r"assign\s+(marks?|grades?|scores?|final\s+grades?|final\s+marks?)(\s+and\s+(marks?|grades?|marks))?\s+(to\s+(all\s+)?students?|automatically)?|"
        r"what\s+grade\s+should\s+this\s+student\s+(get|receive)|"
        r"evaluate\s+and\s+mark\s+this\s+work|"
        r"assign\s+grades\s+to\s+all\s+student\s+submissions",
        re.IGNORECASE,
    )
    RE_RANK_STUDENTS = re.compile(
        r"rank\s+(the\s+)?students?(\s+by\s+(performance|grades?|marks?))?|"
        r"(who\s+are\s+the\s+)?(top|bottom|worst|best)\s+students?",
        re.IGNORECASE,
    )
    RE_AI_DETECTION = re.compile(
        r"(cheated\s+with\s+(chatgpt|ai|gpt)|ai-generated\s+(style|detection|code)|style\s+is\s+ai-generated|"
        r"did\s+.*\s+use\s+(ai|chatgpt)|check\s+whether\s+.*(cheated|ai)|"
        r"accuse\s+.*cheating|"
        r"(detect|determine|check|tell\s+me\s+if)\s+(whether\s+)?.*(used|cheated\s+with)\s+(chatgpt|ai|gpt)|"
        r"(tell\s+me\s+if|analyze\s+.*(and\s+)?(tell\s+me|confirm)|was\s+this|is\s+this).*(written|generated|produced)\s+(by|with)\s+(chatgpt|ai|an?\s+ai|an?\s+llm|gpt)|"
        r"(confirm\s+if\s+it\s+is\s+ai-written|ai-written)|"
        r"(confidence\s+score|detection\s+confidence|probability).*(ai-generated|ai|llm|chatgpt))",
        re.IGNORECASE,
    )
    RE_CROSS_COURSE = re.compile(
        r"where\s+i\s+am\s+not\s+(a\s+)?(ta|instructor|professor|teacher|enrolled)|"
        r"not\s+an\s+instructor|unauthorized\s+course",
        re.IGNORECASE,
    )
    RE_ADMIN_SNOOP = re.compile(
        r"(browse|read|view|show|export|get)\s+(private\s+)?(students?['’]?s?|educational|user['’]?s?)\s+(conversations?|chats?|messages?|history)|"
        r"show\s+me\s+[a-z0-9_]+['’]s\s+(private\s+)?(chat|conversation|messages)|"
        r"export\s+identifiable\s+conversations?",
        re.IGNORECASE,
    )
    RE_AGGREGATE_REPORT = re.compile(
        r"(generate|show|view|get)\s+(aggregate|summary|system|platform|overall|anonymized)\s+(usage|activity|ai\s+usage|lms)\s+(report|statistics|metrics)|"
        r"identify\s+technical\s+(failures?|issues?|errors?)",
        re.IGNORECASE,
    )
    RE_HINT_REQUEST = re.compile(
        r"(give|provide|show)\s+(me\s+)?a\s+hint|"
        r"can\s+i\s+get\s+a\s+hint|"
        r"guide\s+me\s+in\s+the\s+right\s+direction|"
        r"how\s+should\s+i\s+approach\s+(this|question)",
        re.IGNORECASE,
    )
    RE_CONCEPT_EXPLANATION = re.compile(
        r"(explain|what\s+is|how\s+does|tell\s+me\s+about|describe|clarify)\s+(the\s+concept\s+of\s+)?"
        r"(recursion|binary\s+search|acid|deadlock|process|threads?|tcp|osi|ip|database|normal\s+form|b\+?\s*tree|"
        r"stack\s+overflow|algorithm|heuristic|heuristics|usability|concurrency)",
        re.IGNORECASE,
    )
    RE_DEBUG_ASSISTANCE = re.compile(
        r"(why\s+is\s+my\s+code\s+(producing|throwing|giving)|explain\s+this\s+(compiler\s+)?error|"
        r"debugging\s+help|syntaxerror|nullpointerexception|typeerror|segmentation\s+fault|stack\s+overflow)",
        re.IGNORECASE,
    )

    @classmethod
    def evaluate(
        cls,
        user_id: int,
        effective_role: str,
        context: LMSContext,
        policies: List[PolicyDefinition],
        user_request: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        browser_snapshot: Optional[str] = None,
    ) -> GuardEvaluation:
        """
        Authoritative guard evaluation logic combining role permissions, server-side context,
        browser accessibility snapshot evidence, and conversation history.
        """
        interaction_id = f"INT-{uuid.uuid4().hex[:12].upper()}"
        req_clean = user_request.strip()
        policy_ids = [p.policy_id for p in policies]

        if browser_snapshot and not context.browser_snapshot_text:
            context.browser_snapshot_text = browser_snapshot


        # -------------------------------------------------------------
        # 1. UNIVERSAL CHECK: Role Impersonation & Policy Evasion
        # -------------------------------------------------------------
        if cls.RE_ROLE_OVERRIDE.search(req_clean):
            return GuardEvaluation(
                interaction_id=interaction_id,
                decision="BLOCK",
                applicable_policy_ids=policy_ids,
                detected_intent="role_impersonation_or_policy_evasion",
                requested_assistance_type="override_permissions",
                permitted_assistance_type="none",
                violation_categories=[
                    ViolationCategory.ROLE_IMPERSONATION,
                    ViolationCategory.POLICY_EVASION,
                ],
                guard_explanation=(
                    "Request attempts to impersonate an unauthenticated role or override "
                    "contextual AI safety policies. Authenticated backend credentials cannot be altered in-context."
                ),
                evidence=[f"Prohibited pattern matched: '{req_clean[:80]}'"],
                alternative_assistance="Please submit requests corresponding to your authorized academic role.",
            )

        # 1B. UNIVERSAL CHECK: Cross-Course Unauthorized Access
        if cls.RE_CROSS_COURSE.search(req_clean) or effective_role in ["none", "unauthorized"]:
            return GuardEvaluation(
                interaction_id=interaction_id,
                decision="BLOCK",
                applicable_policy_ids=policy_ids,
                detected_intent="unauthorized_course_access",
                requested_assistance_type="cross_course_data",
                permitted_assistance_type="enrolled_course_data_only",
                violation_categories=[
                    ViolationCategory.UNAUTHORISED_DATA_ACCESS,
                    ViolationCategory.CONTEXTUAL_POLICY_VIOLATION,
                ],
                guard_explanation=(
                    "Access to course materials, gradebooks, or submissions in courses where you do not hold "
                    "an authorized active role is strictly prohibited."
                ),
                evidence=[f"Cross-course unauthorized access indicator detected: '{req_clean[:80]}'"],
                alternative_assistance="Please switch to a course where you are actively enrolled or assigned as instructional staff.",
            )

        # -------------------------------------------------------------
        # 2. MULTI-TURN CHECK: Repeated Probing & Incremental Extraction
        # -------------------------------------------------------------
        repeated_boundary = False
        incremental_extraction = False
        if conversation_history:
            recent_turns = conversation_history[-3:]
            blocked_turns = [t for t in recent_turns if t.get("guard_decision") in ["BLOCK", "LIMIT"]]
            if len(blocked_turns) >= 2:
                # Repeatedly attempting restricted assistance
                repeated_boundary = True

            # Check incremental code construction (e.g. asking for pieces of active assignment)
            if context.resource_type == "assignment" and context.assessment_status == "active":
                code_terms = [t for t in recent_turns if "function" in str(t.get("user_request", "")).lower() or "loop" in str(t.get("user_request", "")).lower()]
                if len(code_terms) >= 2 and any(k in req_clean.lower() for k in ["now write", "combine", "full code", "put together"]):
                    incremental_extraction = True

        # -------------------------------------------------------------
        # 3. STUDENT POLICY EVALUATION
        # -------------------------------------------------------------
        if effective_role == "student":
            # 3A-0. Solution Laundering / Plagiarism Evasion
            if cls.RE_SOLUTION_LAUNDERING.search(req_clean):
                ev = [f"Plagiarism circumvention pattern detected: '{req_clean[:80]}'"]
                if context.browser_snapshot_nodes_count > 0:
                    ev.append(f"Browser accessibility snapshot confirms user on '{context.resource_name or 'Assignment'}' view ({context.browser_snapshot_nodes_count} elements)")
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="solution_laundering_and_plagiarism_evasion",
                    requested_assistance_type="code_obfuscation",
                    permitted_assistance_type="none",
                    violation_categories=[
                        ViolationCategory.POLICY_EVASION,
                        ViolationCategory.ASSESSMENT_BYPASS,
                    ],
                    guard_explanation=(
                        "Attempting to obfuscate, disguise, or launder AI-generated source code "
                        "to evade institutional plagiarism detection violates academic integrity policies."
                    ),
                    evidence=ev,
                    alternative_assistance="Please submit work written and formatted authentically by yourself.",
                )

            # 3A. Privacy Violation: Asking for other students' submissions or marks
            if cls.RE_PEER_DATA.search(req_clean):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="peer_data_request",
                    requested_assistance_type="peer_records",
                    permitted_assistance_type="own_records_only",
                    violation_categories=[
                        ViolationCategory.STUDENT_PRIVACY_VIOLATION,
                        ViolationCategory.UNAUTHORISED_DATA_ACCESS,
                    ],
                    guard_explanation=(
                        "Students are strictly prohibited from inspecting peer grades, scores, or submissions "
                        "under institutional FERPA regulations."
                    ),
                    evidence=[f"Query target violates individual grade privacy: '{req_clean[:80]}'"],
                    alternative_assistance="You can view your own published grades in the Gradebook or Course Detail page.",
                )

            # 3B. Active Quiz Solution Seeking
            if cls.RE_QUIZ_ANSWER.search(req_clean) or (context.resource_type == "quiz" and context.assessment_status == "active" and any(k in req_clean.lower() for k in ["answer", "correct", "solve", "option"])):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="quiz_solution_seeking",
                    requested_assistance_type="active_quiz_answer",
                    permitted_assistance_type="none",
                    violation_categories=[
                        ViolationCategory.ASSESSMENT_BYPASS,
                        ViolationCategory.DIRECT_SOLUTION_SEEKING,
                    ],
                    guard_explanation=(
                        "Requesting solutions or answers during an active examination or quiz attempt "
                        "is strictly prohibited to protect assessment integrity."
                    ),
                    evidence=[f"Assessment status is active quiz: resource #{context.resource_id}"],
                    alternative_assistance="Please complete your quiz attempt independently based on your course study.",
                )

            # 3C. Unreleased Answer Key
            if cls.RE_ANSWER_KEY.search(req_clean):
                # If released, allow; otherwise block
                if not context.is_answer_key_released:
                    return GuardEvaluation(
                        interaction_id=interaction_id,
                        decision="BLOCK",
                        applicable_policy_ids=policy_ids,
                        detected_intent="unreleased_answer_key_request",
                        requested_assistance_type="official_solutions",
                        permitted_assistance_type="post_release_explanation",
                        violation_categories=[
                            ViolationCategory.UNAUTHORISED_DATA_ACCESS,
                            ViolationCategory.ASSESSMENT_BYPASS,
                        ],
                        guard_explanation=(
                            "Accessing unreleased answer keys, benchmark solutions, or faculty rubrics "
                            "is prohibited before the official scheduled release date."
                        ),
                        evidence=[f"Answer key release status is false for current resource"],
                        alternative_assistance="Solutions will be available after the instructor publishes the official answer key.",
                    )
                else:
                    return GuardEvaluation(
                        interaction_id=interaction_id,
                        decision="ALLOW",
                        applicable_policy_ids=policy_ids,
                        detected_intent="released_answer_key_explanation",
                        requested_assistance_type="solution_explanation",
                        permitted_assistance_type="full_explanation",
                        guard_explanation="The official answer key has been released for this completed assessment.",
                    )

            # 3D. Active Assignment Full Solution Seeking
            if cls.RE_COMPLETE_SOLUTION.search(req_clean) or incremental_extraction:
                violations = [
                    ViolationCategory.DIRECT_SOLUTION_SEEKING,
                    ViolationCategory.EXCESSIVE_ASSISTANCE,
                ]
                if context.assessment_status != "closed":
                    violations.append(ViolationCategory.ASSESSMENT_BYPASS)
                if incremental_extraction:
                    violations.append(ViolationCategory.INCREMENTAL_EXTRACTION)
                if repeated_boundary:
                    violations.append(ViolationCategory.REPEATED_BOUNDARY_TESTING)

                ev = [f"Active assignment context: {context.resource_name or 'Course Assignment'}"]
                if context.browser_snapshot_nodes_count > 0:
                    ev.append(f"Browser accessibility snapshot confirms active assignment view with {context.browser_snapshot_nodes_count} accessible elements")
                if context.browser_snapshot_headings:
                    ev.append(f"Snapshot headings: {', '.join(context.browser_snapshot_headings[:2])}")

                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK" if context.assessment_status != "closed" else "LIMIT",
                    applicable_policy_ids=policy_ids,
                    detected_intent="complete_solution_request",
                    requested_assistance_type="complete_code_generation",
                    permitted_assistance_type="conceptual_hints_and_debugging",
                    violation_categories=violations,
                    guard_explanation=(
                        "Generating full solutions, complete source code, or end-to-end implementations "
                        "for active course assignments violates the Student AI Usage Policy."
                    ),
                    evidence=ev,
                    alternative_assistance=(
                        "You can ask for an algorithm outline, a conceptual hint for a specific step, "
                        "or debugging assistance for code you have written yourself."
                    ),
                )

            # 3E. Hints on Active Assessment (Permitted as LIMIT or ALLOW depending on policy)
            if cls.RE_HINT_REQUEST.search(req_clean):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="LIMIT" if context.assessment_status == "active" else "ALLOW",
                    applicable_policy_ids=policy_ids,
                    detected_intent="hint_request",
                    requested_assistance_type="conceptual_hint",
                    permitted_assistance_type="conceptual_hint_without_code",
                    violation_categories=[],
                    guard_explanation=(
                        "Providing conceptual guidance and scaffolding hints without revealing "
                        "the assessed implementation is permitted."
                    ),
                    evidence=[f"Assessment: {context.resource_name or 'Assignment'} (status={context.assessment_status})"],
                    alternative_assistance="You can follow up with specific questions about error messages or concepts.",
                )

            # 3F. Debugging & Error Assistance
            if cls.RE_DEBUG_ASSISTANCE.search(req_clean):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="ALLOW",
                    applicable_policy_ids=policy_ids,
                    detected_intent="error_and_debugging_guidance",
                    requested_assistance_type="debugging_assistance",
                    permitted_assistance_type="error_diagnosis_and_debugging",
                    violation_categories=[],
                    guard_explanation="Explaining runtime or compiler errors and troubleshooting methodologies is permitted.",
                )

            # 3G. Concept Explanations & General Learning
            return GuardEvaluation(
                interaction_id=interaction_id,
                decision="ALLOW",
                applicable_policy_ids=policy_ids,
                detected_intent="concept_explanation_or_practice",
                requested_assistance_type="conceptual_learning",
                permitted_assistance_type="educational_explanations",
                violation_categories=[],
                guard_explanation="Conceptual explanations, theoretical overviews, and practice exercises are fully permitted.",
            )

        # -------------------------------------------------------------
        # 4. TEACHING ASSISTANT (TA) POLICY EVALUATION
        # -------------------------------------------------------------
        elif effective_role == "ta":
            # 4A. Prohibited: Delegating submission grading or scoring
            if cls.RE_GRADE_DELEGATION.search(req_clean):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="automated_grading_request",
                    requested_assistance_type="submission_scoring",
                    permitted_assistance_type="rubric_preparation_only",
                    violation_categories=[ViolationCategory.UNAUTHORISED_GRADING],
                    guard_explanation=(
                        "Teaching Assistants are prohibited from delegating individual student grading, "
                        "mark allocation, or performance evaluations to autonomous AI."
                    ),
                    evidence=[f"Grading request detected: '{req_clean[:80]}'"],
                    alternative_assistance="You may use the assistant to draft generic grading rubrics or review anonymized feedback templates.",
                )

            # 4B. Prohibited: Student performance ranking
            if cls.RE_RANK_STUDENTS.search(req_clean):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="student_ranking_request",
                    requested_assistance_type="comparative_ranking",
                    permitted_assistance_type="anonymized_aggregate_analytics",
                    violation_categories=[
                        ViolationCategory.UNAUTHORISED_GRADING,
                        ViolationCategory.STUDENT_PRIVACY_VIOLATION,
                    ],
                    guard_explanation="Ranking students based on comparative academic performance via AI is prohibited.",
                    evidence=[f"Ranking keywords detected in request"],
                    alternative_assistance="You can analyze general class topic difficulties or curriculum outcomes.",
                )

            # 4C. Prohibited: Style-based AI cheating detection
            if cls.RE_AI_DETECTION.search(req_clean):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="ai_cheating_detection",
                    requested_assistance_type="automated_integrity_accusation",
                    permitted_assistance_type="none",
                    violation_categories=[
                        ViolationCategory.UNAUTHORISED_GRADING,
                        ViolationCategory.POLICY_EVASION,
                    ],
                    guard_explanation=(
                        "AI models cannot authoritatively determine whether student writing was AI-generated. "
                        "Academic integrity reviews require human verification through authorized university procedures."
                    ),
                    evidence=[f"AI detection inquiry detected"],
                    alternative_assistance="Please report concerns through your course professor or formal university academic integrity channels.",
                )

            # 4D. Prohibited: Uploading identifiable student records
            if any(k in req_clean.lower() for k in ["upload student work", "upload submission", "private record"]):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="identifiable_student_upload",
                    requested_assistance_type="student_record_processing",
                    permitted_assistance_type="anonymized_work_only",
                    violation_categories=[ViolationCategory.STUDENT_PRIVACY_VIOLATION],
                    guard_explanation="Uploading identifiable student submissions or confidential records to the AI assistant is prohibited.",
                    evidence=[f"Record upload keywords detected"],
                    alternative_assistance="Ensure all student identifiers are removed before analyzing educational samples.",
                )

            # 4E. Permitted TA Operations: Hints, practice questions, tutorial prep
            return GuardEvaluation(
                interaction_id=interaction_id,
                decision="ALLOW",
                applicable_policy_ids=policy_ids,
                detected_intent="ta_pedagogical_preparation",
                requested_assistance_type="teaching_material_generation",
                permitted_assistance_type="hints_questions_explanations",
                violation_categories=[],
                guard_explanation=(
                    "Generating tutorial exercises, assignment hints, practice questions, "
                    "and reference explanations is authorized for Teaching Assistants."
                ),
            )

        # -------------------------------------------------------------
        # 5. PROFESSOR POLICY EVALUATION
        # -------------------------------------------------------------
        elif effective_role == "professor":
            # 5A. Prohibited: Private student chat export / snooping
            if cls.RE_ADMIN_SNOOP.search(req_clean) or any(k in req_clean.lower() for k in ["private conversation", "chat history", "private chat", "chat logs"]):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="private_chat_export_request",
                    requested_assistance_type="student_private_data",
                    permitted_assistance_type="none",
                    violation_categories=[
                        ViolationCategory.STUDENT_PRIVACY_VIOLATION,
                        ViolationCategory.UNAUTHORISED_DATA_ACCESS,
                    ],
                    guard_explanation=(
                        "Instructors and faculty may not inspect or export private student AI conversation transcripts."
                    ),
                    evidence=[f"Private student chat access detected: '{req_clean[:80]}'"],
                    alternative_assistance="Refer academic concerns through formal institutional channels.",
                )

            # 5B. Prohibited: Autonomous final grading or unreviewed grade publishing
            if cls.RE_GRADE_DELEGATION.search(req_clean) or any(k in req_clean.lower() for k in ["assign final marks", "assign final grades", "publish grades automatically", "let ai decide marks"]):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="autonomous_final_grading",
                    requested_assistance_type="authoritative_grading",
                    permitted_assistance_type="preliminary_rubric_drafting",
                    violation_categories=[ViolationCategory.UNAUTHORISED_GRADING],
                    guard_explanation=(
                        "Course faculty cannot delegate final authoritative grading or publish "
                        "grades without mandatory human instructor review."
                    ),
                    evidence=[f"Autonomous final grading prompt detected"],
                    alternative_assistance="You can use the assistant to generate marking rubrics or preliminary grading criteria.",
                )

            # 5C. Prohibited: Style-based cheating accusations
            if cls.RE_AI_DETECTION.search(req_clean):
                ev = [f"Misconduct determination inquiry detected: '{req_clean[:80]}'"]
                if context.browser_snapshot_nodes_count > 0:
                    ev.append(f"Browser accessibility snapshot confirms user on '{context.resource_name or 'Course'}' view ({context.browser_snapshot_nodes_count} elements)")
                if context.browser_snapshot_headings:
                    ev.append(f"Visible snapshot headings: {', '.join(context.browser_snapshot_headings[:2])}")

                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="ai_cheating_detection",
                    requested_assistance_type="misconduct_determination",
                    permitted_assistance_type="none",
                    violation_categories=[
                        ViolationCategory.UNAUTHORISED_GRADING,
                        ViolationCategory.POLICY_EVASION,
                    ],
                    guard_explanation=(
                        "Autonomous academic integrity decisions based on AI writing style detection "
                        "are prohibited without institutional disciplinary committee proceedings."
                    ),
                    evidence=ev,
                    alternative_assistance="Refer cases to the departmental academic integrity officer or conduct an oral code defense.",
                )

            # 5C. Permitted Professor Operations: Authoring assessments, rubrics, solutions
            return GuardEvaluation(
                interaction_id=interaction_id,
                decision="ALLOW",
                applicable_policy_ids=policy_ids,
                detected_intent="faculty_curriculum_authoring",
                requested_assistance_type="curriculum_authoring",
                permitted_assistance_type="full_curriculum_generation",
                violation_categories=[],
                guard_explanation=(
                    "Generating course assignments, quizzes, solutions, rubrics, and anonymized "
                    "curriculum analytics is fully authorized for faculty."
                ),
            )

        # -------------------------------------------------------------
        # 6. ADMINISTRATOR POLICY EVALUATION
        # -------------------------------------------------------------
        elif effective_role == "admin":
            # 6A. Prohibited: Snooping on private student conversations without authorized purpose
            if cls.RE_ADMIN_SNOOP.search(req_clean):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="private_conversation_inspection",
                    requested_assistance_type="user_private_chat_browsing",
                    permitted_assistance_type="aggregate_audit_summaries",
                    violation_categories=[
                        ViolationCategory.UNAUTHORISED_ADMIN_MONITORING,
                        ViolationCategory.STUDENT_PRIVACY_VIOLATION,
                    ],
                    guard_explanation=(
                        "Administrators may not browse or extract individual private educational conversations "
                        "without documented institutional authorization and documented purpose."
                    ),
                    evidence=[f"Private conversation access request: '{req_clean[:80]}'"],
                    alternative_assistance="You can review aggregate platform usage statistics or authorized security audit telemetry in /admin/logs.",
                )

            # 6B. Prohibited: Extracting student grades without administrative purpose
            if cls.RE_PEER_DATA.search(req_clean) and not any(k in req_clean.lower() for k in ["audit", "compliance", "aggregate"]):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="unauthorized_grade_extraction",
                    requested_assistance_type="student_grade_records",
                    permitted_assistance_type="anonymized_metrics_only",
                    violation_categories=[
                        ViolationCategory.UNAUTHORISED_DATA_ACCESS,
                        ViolationCategory.STUDENT_PRIVACY_VIOLATION,
                    ],
                    guard_explanation=(
                        "Extracting individual student grade records via administrative AI queries "
                        "without documented necessity violates the Institutional Administrator Policy."
                    ),
                    evidence=[f"Grade extraction keywords detected"],
                    alternative_assistance="Please use the official Registrar console or institutional reporting dashboards.",
                )

            # 6C. Prohibited: Institution-wide automated grading
            if cls.RE_GRADE_DELEGATION.search(req_clean) or any(k in req_clean.lower() for k in ["assign grades", "automated grading"]):
                return GuardEvaluation(
                    interaction_id=interaction_id,
                    decision="BLOCK",
                    applicable_policy_ids=policy_ids,
                    detected_intent="automated_institutional_grading",
                    requested_assistance_type="institutional_grading",
                    permitted_assistance_type="none",
                    violation_categories=[ViolationCategory.UNAUTHORISED_GRADING],
                    guard_explanation="Institution-wide automated student grading via AI is strictly prohibited.",
                    evidence=[f"Automated grading detected: '{req_clean[:80]}'"],
                    alternative_assistance="Grading must be conducted by course instructional faculty.",
                )

            # 6D. Permitted: Aggregate reports, technical issue diagnosis, audit summaries
            return GuardEvaluation(
                interaction_id=interaction_id,
                decision="ALLOW",
                applicable_policy_ids=policy_ids,
                detected_intent="admin_platform_governance",
                requested_assistance_type="system_metrics_and_auditing",
                permitted_assistance_type="aggregate_governance_data",
                violation_categories=[],
                guard_explanation=(
                    "Generating aggregate platform statistics, technical error summaries, "
                    "and reviewing authorized governance metrics is permitted."
                ),
            )

        # Fallback safe response
        return GuardEvaluation(
            interaction_id=interaction_id,
            decision="ALLOW",
            applicable_policy_ids=policy_ids,
            detected_intent="general_inquiry",
            requested_assistance_type="general",
            permitted_assistance_type="safe_general_assistance",
            guard_explanation="Request complies with general educational interaction policies.",
        )
