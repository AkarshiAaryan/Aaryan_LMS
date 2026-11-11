"""
Scenario Families and Boundary Classifications for GuardSLM Benchmark V2.
"""

SCENARIO_FAMILIES = {
    "FAM01": {
        "id": "FAM01",
        "name": "Grades & Gradebook",
        "description": "Own grades, peer grades, class gradebooks, TA grading, and final grade publication.",
        "policy_key": "GRADE_PRIVACY",
    },
    "FAM02": {
        "id": "FAM02",
        "name": "Submissions & Deadlines",
        "description": "Assignment submissions, late penalties, locked revisions, and group hand-ins.",
        "policy_key": "SUBMISSION_INTEGRITY",
    },
    "FAM03": {
        "id": "FAM03",
        "name": "Quizzes & Examinations",
        "description": "Quiz attempts, quota limits, closed exam access, and answer key releases.",
        "policy_key": "QUIZ_CONDUCT",
    },
    "FAM04": {
        "id": "FAM04",
        "name": "Learning Modules & Lessons",
        "description": "Curricular lessons, scheduled future unlocks, and prerequisite progression.",
        "policy_key": "LEARNING_MODULES",
    },
    "FAM05": {
        "id": "FAM05",
        "name": "Course Files Repository",
        "description": "Public documents, staff-only answer keys, private student notes, and expired handouts.",
        "policy_key": "COURSE_FILES",
    },
    "FAM06": {
        "id": "FAM06",
        "name": "Discussion Forums",
        "description": "Public course forums, confidential private staff threads, and locked discussions.",
        "policy_key": "FORUM_CONDUCT",
    },
    "FAM07": {
        "id": "FAM07",
        "name": "Peer Reviews & Grade Appeals",
        "description": "Double-blind reviews, deadline checks, and student grade appeal workflow.",
        "policy_key": "PEER_REVIEW",
    },
    "FAM08": {
        "id": "FAM08",
        "name": "Attendance & Scheduling",
        "description": "Attendance rosters, instructor locks, absence excuses, and section meetings.",
        "policy_key": "ATTENDANCE_SCHEDULING",
    },
    "FAM09": {
        "id": "FAM09",
        "name": "Administrative & Institutional",
        "description": "Admin rosters, audit logs, department heads, and suspended/revoked accounts.",
        "policy_key": "ADMIN_ENROLLMENT",
    },
    "FAM10": {
        "id": "FAM10",
        "name": "Cross-Course & Cross-Section Isolation",
        "description": "Enforcing isolation between distinct courses and lecture/lab sections.",
        "policy_key": "SUBMISSION_INTEGRITY",
    },
    "FAM11": {
        "id": "FAM11",
        "name": "Multi-Step Sequential Workflows",
        "description": "Sequential steps where early steps are permitted but later steps violate policies.",
        "policy_key": "SUBMISSION_INTEGRITY",
    },
    "FAM12": {
        "id": "FAM12",
        "name": "Stale Token & Privilege Downgrade",
        "description": "Temporal privilege shifts where token says TA/student but enrollment was dropped.",
        "policy_key": "ADMIN_ENROLLMENT",
    },
    "FAM13": {
        "id": "FAM13",
        "name": "Adversarial & Guard-Bypassing Pretexts",
        "description": "Prompt injections, emergency overrides, and fake professor impersonation in user prompts.",
        "policy_key": "GRADE_PRIVACY",
    },
}

CONTRAST_DIMENSIONS = [
    "Identity",   # Valid role vs unauthorized role
    "Scope",      # Course member vs external non-member, SEC01 vs SEC02
    "Ownership",  # Own artifact vs peer artifact
    "Lifecycle",  # Open quiz vs closed quiz, draft vs finalized
    "Time",       # Before deadline vs after deadline, unreleased vs released
]

BOUNDARY_TYPES = [
    "Role-Based",
    "Ownership-Based",
    "Temporal-Based",
    "State-Based",
    "Scope-Based",
    "Adversarial-Bypass",
]
