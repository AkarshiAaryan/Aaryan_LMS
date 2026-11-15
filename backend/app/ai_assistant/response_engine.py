"""
Deterministic Simulated Response Engine for GuardSLM AI Assistant.
Produces context-rich academic responses, structured hints, and principled refusals
strictly aligned with Guard decisions without calling any external LLM APIs.
"""

from typing import Dict, Any, List, Optional
from .context import LMSContext
from .guard import GuardEvaluation
from .policy_engine import ViolationCategory


class SimulatedResponseEngine:
    """
    Generates deterministic educational responses based on the GuardEvaluation,
    authoritative LMS context, and user request.
    """

    # Knowledge base for concept explanations
    CONCEPT_KNOWLEDGE = {
        "recursion": {
            "title": "Recursion in Computer Science",
            "summary": "Recursion is a programming technique where a function calls itself directly or indirectly to solve a problem by breaking it down into smaller subproblems.",
            "components": [
                "**Base Case:** The condition that terminates recursion and prevents infinite loops (e.g., `if n <= 1: return 1`).",
                "**Recursive Step:** The reduction of the problem towards the base case (e.g., `n * factorial(n - 1)`).",
                "**Call Stack:** Each call allocates a stack frame storing local variables and return address.",
            ],
            "example": "Common examples include Fibonacci computation, binary tree traversal, and divide-and-conquer algorithms (MergeSort, QuickSort).",
        },
        "binary search": {
            "title": "Binary Search Algorithm",
            "summary": "Binary search is an efficient divide-and-conquer algorithm for finding an item from a sorted collection with O(log n) time complexity.",
            "components": [
                "**Precondition:** The input array or list must be strictly sorted.",
                "**Pointers:** Maintain `low` and `high` indices, calculating `mid = low + (high - low) // 2`.",
                "**Comparison:** If `target == arr[mid]`, found. If `target < arr[mid]`, search left half (`high = mid - 1`). Otherwise search right half (`low = mid + 1`).",
            ],
            "example": "Searching for a number in an array of 1,000,000 items requires at most ~20 comparisons.",
        },
        "acid": {
            "title": "ACID Properties in Database Management Systems",
            "summary": "ACID is an acronym representing the four key properties that guarantee reliable transaction processing in database systems.",
            "components": [
                "**Atomicity:** Transactions are 'all or nothing'. If any operation fails, the entire transaction is rolled back.",
                "**Consistency:** Transactions transition the database from one valid state satisfying all schema constraints to another.",
                "**Isolation:** Concurrent transactions execute without interfering with one another (managed via isolation levels like Read Committed, Serializable).",
                "**Durability:** Once committed, changes survive system failures, power outages, and crashes (logged to WAL/disk).",
            ],
            "example": "In a bank transfer, deducting $100 from Account A and adding $100 to Account B must both succeed or both fail together.",
        },
        "deadlock": {
            "title": "Deadlock and the Coffman Conditions",
            "summary": "A deadlock occurs in operating systems when two or more processes are permanently blocked, each waiting for a resource held by another.",
            "components": [
                "**Mutual Exclusion:** At least one resource must be held in a non-shareable mode.",
                "**Hold and Wait:** A process holding at least one resource is waiting to acquire additional resources held by other processes.",
                "**No Preemption:** Resources cannot be forcibly confiscated; they are released only voluntarily by the holding process.",
                "**Circular Wait:** A closed chain of processes exists such that each process holds a resource needed by the next.",
            ],
            "example": "Handling deadlocks involves prevention (breaking one of the 4 conditions), avoidance (Banker's Algorithm), or detection and recovery.",
        },
        "concurrency": {
            "title": "Concurrency and Synchronization",
            "summary": "Concurrency is the execution of multiple instruction sequences simultaneously, sharing resources and memory.",
            "components": [
                "**Race Conditions:** Flaws where the program output depends on non-deterministic thread execution order.",
                "**Critical Section:** Code segment accessing shared resources that must be protected by mutual exclusion.",
                "**Primitives:** Mutexes, semaphores, condition variables, and atomic operations.",
            ],
            "example": "Two threads concurrently incrementing `counter = counter + 1` without synchronization can result in lost updates.",
        },
        "normal form": {
            "title": "Relational Database Normalization",
            "summary": "Normalization organizes database columns and tables to reduce data redundancy and eliminate insert, update, and delete anomalies.",
            "components": [
                "**1NF (First Normal Form):** Atomic column values, unique rows, no repeating groups.",
                "**2NF (Second Normal Form):** In 1NF and all non-key attributes are fully functionally dependent on the entire primary key.",
                "**3NF (Third Normal Form):** In 2NF and no transitive functional dependencies on the primary key.",
                "**BCNF (Boyce-Codd Normal Form):** For every functional dependency X -> Y, X must be a superkey.",
            ],
            "example": "Decomposing an Orders table into Customers, Orders, and OrderItems.",
        },
        "osi": {
            "title": "OSI 7-Layer Reference Model",
            "summary": "The Open Systems Interconnection model characterizes network communication functions into seven abstraction layers.",
            "components": [
                "**Physical (Layer 1):** Bit transmission over physical medium (cables, radio).",
                "**Data Link (Layer 2):** Framing, MAC addressing, error detection (Ethernet, Wi-Fi).",
                "**Network (Layer 3):** Routing and logical addressing (IP, ICMP, routers).",
                "**Transport (Layer 4):** End-to-end communication, reliability, flow control (TCP, UDP).",
                "**Session, Presentation, Application (Layers 5-7):** Dialog control, data formatting/encryption, and user protocols (HTTP, DNS, SSH).",
            ],
            "example": "Encapsulation adds headers at each layer as data travels down the stack.",
        },
    }

    @classmethod
    def generate_response(
        cls,
        guard_eval: GuardEvaluation,
        user_request: str,
        context: LMSContext,
        user_display_name: str = "User",
    ) -> str:
        """
        Main response generation entry point.
        Strictly respects guard_eval.decision.
        """
        decision = guard_eval.decision

        if decision == "BLOCK":
            return cls._generate_block_response(guard_eval, context)
        elif decision == "ESCALATE":
            return cls._generate_escalate_response(guard_eval, context)
        elif decision == "LIMIT":
            return cls._generate_limit_response(guard_eval, user_request, context)
        elif decision == "ALLOW":
            return cls._generate_allow_response(guard_eval, user_request, context, user_display_name)
        else:
            return (
                "Your request has been received. Please consult the course syllabus or reach out to "
                "the instructional staff for guidance."
            )

    @classmethod
    def _generate_block_response(cls, guard_eval: GuardEvaluation, context: LMSContext) -> str:
        """Constructs an educational refusal with policy explanation and alternative guidance."""
        violation_str = ", ".join(guard_eval.violation_categories) if guard_eval.violation_categories else "INSTITUTIONAL_AI_POLICY"
        
        parts = [
            f"### Policy Notice: Request Restricted [{violation_str}]",
            "",
            f"**Decision:** `BLOCK`",
            f"**Reason:** {guard_eval.guard_explanation}",
        ]

        if guard_eval.evidence:
            parts.extend([
                "",
                "**Policy Factors:**",
                *[f"- {ev}" for ev in guard_eval.evidence],
            ])

        if guard_eval.alternative_assistance:
            parts.extend([
                "",
                "**Permitted Alternative:**",
                guard_eval.alternative_assistance,
            ])
        else:
            parts.extend([
                "",
                "**Recommended Action:**",
                "Review the assignment instructions, review lecture notes, or attend scheduled TA office hours.",
            ])

        return "\n".join(parts)

    @classmethod
    def _generate_escalate_response(cls, guard_eval: GuardEvaluation, context: LMSContext) -> str:
        """Constructs a formal escalation notice."""
        return (
            "### Notice: Interaction Escalated for Administrative Review\n\n"
            "**Decision:** `ESCALATE`\n\n"
            f"**Explanation:** {guard_eval.guard_explanation}\n\n"
            "This request has triggered safety policies requiring human authorization or oversight. "
            "A formal audit record has been logged in the LMS research & compliance database.\n\n"
            "If you believe this is in error, please contact the Course Instructor or LMS Administration directly."
        )

    @classmethod
    def _generate_limit_response(
        cls,
        guard_eval: GuardEvaluation,
        user_request: str,
        context: LMSContext,
    ) -> str:
        """Constructs bounded assistance (hints, conceptual guidance, pseudocode structure)."""
        resource_name = context.resource_name or "this assessment"
        
        parts = [
            f"### Guiding Hint for {resource_name}",
            "",
            "> [!NOTE]",
            "> Per course policy during active assessments, complete code solutions are restricted. Here is a conceptual walkthrough and hint to guide your implementation.",
            "",
        ]

        req_lower = user_request.lower()

        # Provide tailored conceptual hints
        if "binary search" in req_lower or "tree" in req_lower:
            parts.extend([
                "**Algorithmic Concept:**",
                "1. Identify the search invariant: At each step, what subset of elements is guaranteed to contain the target?",
                "2. Check boundary conditions: Does your loop condition handle 1-element arrays (`low <= high`)?",
                "3. Watch integer overflow in mid-calculation: Prefer `low + (high - low) // 2`.",
            ])
        elif "recursion" in req_lower or "fibonacci" in req_lower or "factorial" in req_lower:
            parts.extend([
                "**Recursive Structure:**",
                "1. Clearly define your base case(s): When should the function stop and return a fixed answer?",
                "2. Define the recurrence relation: How does `f(n)` depend on `f(n - 1)` or `f(n - 2)`?",
                "3. Verify that each step moves strictly closer to the base case.",
            ])
        elif "deadlock" in req_lower or "lock" in req_lower:
            parts.extend([
                "**Synchronization Guidelines:**",
                "1. Look for resource acquisition ordering: Impose a global ordering on locks to eliminate Circular Wait.",
                "2. Check if locks can be acquired with a timeout (`try_lock`) to recover from Hold and Wait.",
            ])
        elif "sql" in req_lower or "database" in req_lower or "query" in req_lower:
            parts.extend([
                "**Database Query Design:**",
                "1. Break the problem into parts: Which tables contain the required columns?",
                "2. Choose the correct JOIN type (INNER JOIN vs LEFT JOIN).",
                "3. Filter before grouping with WHERE, and filter aggregates with HAVING.",
            ])
        else:
            parts.extend([
                "**Problem-Solving Strategy:**",
                "1. Restate the problem inputs, preconditions, and expected outputs.",
                "2. Sketch the solution on paper or in plain English pseudocode before writing code.",
                "3. Test with simple edge cases (empty input, single element, boundary values).",
                "",
                f"**Permitted Assistance:** {guard_eval.permitted_assistance_type.replace('_', ' ').title()}",
            ])

        parts.extend([
            "",
            "---",
            "*Next step: Try writing your logic based on these steps and share the specific compiler/runtime error if you get stuck!*",
        ])

        return "\n".join(parts)

    @classmethod
    def _generate_allow_response(
        cls,
        guard_eval: GuardEvaluation,
        user_request: str,
        context: LMSContext,
        user_display_name: str,
    ) -> str:
        """Constructs full permitted educational response based on user role and context."""
        role = context.effective_role
        req_lower = user_request.lower()

        # 1. Matching Known Concept Explanation
        for concept_key, concept_data in cls.CONCEPT_KNOWLEDGE.items():
            if concept_key in req_lower:
                return cls._format_concept_explanation(concept_data)

        # 2. Debugging / Error Assistance
        if any(err in req_lower for err in ["error", "exception", "bug", "debugging", "syntaxerror", "typeerror", "nullpointer", "segfault"]):
            return cls._format_debugging_help(user_request)

        # 3. TA-specific Generation (rubrics, hints, practice problems)
        if role == "ta":
            if any(k in req_lower for k in ["rubric", "criteria", "grading guide"]):
                return cls._format_ta_rubric(context)
            if any(k in req_lower for k in ["practice", "exercise", "question"]):
                return cls._format_practice_questions(context)
            if any(k in req_lower for k in ["hint", "guide"]):
                return cls._format_ta_hint_generation(context)
            return (
                f"### Teaching Assistant Resource Generation\n\n"
                f"Hello {user_display_name}! I can assist you with:\n"
                "- Generating student practice problems with solution keys\n"
                "- Creating structured grading rubrics for assignments\n"
                "- Drafting progressive hints for office hour support\n\n"
                "*(Note: Submissions must be graded and marked by instructional staff directly.)*"
            )

        # 4. Professor-specific Generation (assessments, course materials)
        if role == "professor":
            if any(k in req_lower for k in ["question", "exam", "quiz", "assessment"]):
                return cls._format_professor_assessment_creation(context)
            if any(k in req_lower for k in ["rubric", "criteria"]):
                return cls._format_ta_rubric(context)
            return (
                f"### Instructional Courseware Design\n\n"
                f"Welcome Professor {user_display_name}. I can generate:\n"
                "- Multi-tier exam and quiz questions with reference solutions and distractor analyses\n"
                "- Detailed analytic grading rubrics aligned with course learning outcomes\n"
                "- Homework specifications and reference implementations\n"
                "- Supplementary reading lists and syllabus outlines\n\n"
                "*(Note: Student evaluations and academic integrity determinations must be conducted by human instructors.)*"
            )

        # 5. Admin-specific Aggregate Analytics
        if role == "admin":
            return cls._format_admin_aggregate_report(context)

        # 6. Default Student / General Inquiry
        course_info = f" in {context.course_code or context.course_name}" if context.course_code else ""
        return (
            f"### Educational Assistance{course_info}\n\n"
            f"Hello {user_display_name}! I can help you understand course concepts, work through sample exercises, "
            f"explain compiler and runtime errors, and review algorithmic principles.\n\n"
            f"Feel free to ask a conceptual question (e.g. *'Explain the difference between TCP and UDP'*, "
            f"*'How does binary search work?'*, or share a specific error message you're seeing in your code)!"
        )

    @classmethod
    def _format_concept_explanation(cls, data: Dict[str, Any]) -> str:
        parts = [
            f"### {data['title']}",
            "",
            data["summary"],
            "",
            "**Key Principles:**",
            *[f"- {comp}" for comp in data["components"]],
            "",
            f"**Example / Application:**",
            data["example"],
        ]
        return "\n".join(parts)

    @classmethod
    def _format_debugging_help(cls, user_request: str) -> str:
        return (
            "### Systematic Debugging Guide\n\n"
            "When encountering unexpected behavior or runtime errors, follow this diagnostic process:\n\n"
            "1. **Isolate the Error Location:** Inspect the stack trace to identify the exact line number where execution failed.\n"
            "2. **Check Preconditions:** Ensure inputs, variables, and pointers are not `None` or out of bounds before dereferencing.\n"
            "3. **Print / Trace State:** Print variable values immediately before the failing line to verify your mental model against actual runtime state.\n"
            "4. **Boundary Cases:** Test with empty collections, 0, negative values, or maximum capacity inputs.\n\n"
            "*If you paste the specific error message and line of code throwing the exception, I can explain the mechanics of the error!*"
        )

    @classmethod
    def _format_ta_rubric(cls, context: LMSContext) -> str:
        course_label = context.course_code or "Course"
        return (
            f"### Sample Grading Rubric Template for {course_label}\n\n"
            "| Criteria | Exemplary (100%) | Proficient (80%) | Developing (60%) | Unacceptable (0%) |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| **Correctness & Tests** | Passes 100% of public and private test cases | Passes all public test cases; minor edge case failure | Basic functionality works; fails edge cases | Does not compile or major logic failures |\n"
            "| **Algorithm Efficiency** | Meets optimal time and space complexity | Sub-optimal by constant factor | Inefficient complexity (e.g. O(n²) instead of O(n)) | Catastrophic complexity / timeout |\n"
            "| **Code Quality & Style** | Clean modular design, clear variable names, comprehensive docstrings | Minor formatting issues; well-structured | Poor naming, duplicate code, sparse comments | Incomprehensible or monolithic code |\n"
            "| **Error Handling** | Robust handling of invalid inputs and boundary conditions | Handles standard bad inputs | Fragile under unexpected inputs | Crashes on simple edge cases |\n\n"
            "*(This rubric is a proposed template. TAs and Instructors can adjust category weights to match assignment objectives.)*"
        )

    @classmethod
    def _format_practice_questions(cls, context: LMSContext) -> str:
        return (
            "### Generated Practice Problems with Solutions (For Teaching Use)\n\n"
            "#### Problem 1: Array Inversion Count (Intermediate)\n"
            "**Question:** Given an array `A[0..n-1]`, two elements `A[i]` and `A[j]` form an inversion if `A[i] > A[j]` and `i < j`. "
            "Design an algorithm to count the number of inversions in `O(n log n)` time.\n\n"
            "**Solution Guide for TAs:**\n"
            "- Modify the MergeSort algorithm.\n"
            "- During the merge step of two sorted subarrays `L` and `R`, when `L[i] > R[j]`, all remaining elements in `L` from `i` onwards also form inversions with `R[j]`.\n"
            "- Add `len(L) - i` to the inversion count.\n\n"
            "#### Problem 2: Cycle Detection in Directed Graph\n"
            "**Question:** Explain how Depth-First Search (DFS) with 3-color node states (White, Gray, Black) detects cycles in a directed graph.\n\n"
            "**Solution Guide:**\n"
            "- White: Unvisited. Gray: Currently visiting in the current DFS path. Black: Fully explored.\n"
            "- A back-edge to a Gray node indicates a cycle."
        )

    @classmethod
    def _format_ta_hint_generation(cls, context: LMSContext) -> str:
        return (
            "### Progressive Hint Ladder (For Office Hours)\n\n"
            "To support student learning without revealing solutions prematurely, use this 3-tier hint ladder:\n\n"
            "- **Hint 1 (Conceptual):** 'Before coding, think about how you would solve this on a whiteboard with an array of 5 elements.'\n"
            "- **Hint 2 (Structural):** 'Consider what data structure provides O(1) average lookup time when you need to remember previously seen elements.'\n"
            "- **Hint 3 (Specific):** 'Try iterating through the array while maintaining a hash set of seen complements (`target - current_value`).'"
        )

    @classmethod
    def _format_professor_assessment_creation(cls, context: LMSContext) -> str:
        return (
            "### Assessment Question Bank Generator\n\n"
            "#### Multiple Choice Question (Concept Discrimination)\n"
            "**Question:** Which of the following conditions is NOT required for a deadlock to occur?\n"
            "- [ ] A. Mutual Exclusion\n"
            "- [ ] B. Hold and Wait\n"
            "- [x] C. Preemption of Resources *(Correct - deadlock requires No Preemption)*\n"
            "- [ ] D. Circular Wait\n\n"
            "**Distractor Rationale:**\n"
            "- Option A, B, and D are part of the four necessary Coffman conditions.\n"
            "- Preemption actively *breaks* deadlock by revoking held resources.\n\n"
            "#### Open-Ended Design Question\n"
            "**Prompt:** 'Design a distributed cache invalidation strategy for a read-heavy microservice architecture. "
            "Compare write-through caching versus cache-aside in terms of data consistency and write latency.'"
        )

    @classmethod
    def _format_admin_aggregate_report(cls, context: LMSContext) -> str:
        return (
            "### Institutional AI Usage Aggregate Report (Anonymized)\n\n"
            "- **Total Active Courses:** 4 courses (CSE301, CSE302, CSE401, CSE402)\n"
            "- **Assistance Request Volume (Past 30 Days):** 1,280 interactions\n"
            "- **Guard Decision Breakdown:**\n"
            "  - `ALLOW`: 78.4% (980 requests)\n"
            "  - `LIMIT`: 13.6% (170 requests - primarily active homework conceptual hints)\n"
            "  - `BLOCK`: 6.8% (85 requests - direct solution requests / quiz access attempts)\n"
            "  - `ESCALATE`: 1.2% (15 requests - administrative / role override testing)\n"
            "- **System Health:** 0 fatal safety failures, 100% compliance with FERPA data isolation standards.\n\n"
            "*(Note: Individual student identifiable chat logs are protected under student privacy policies.)*"
        )
