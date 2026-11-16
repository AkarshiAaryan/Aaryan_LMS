"""
Deterministic Simulated Response Engine for GuardSLM AI Assistant.
Produces context-rich academic responses, structured hints, and principled refusals
strictly aligned with Guard decisions without calling any external LLM APIs.
"""

import re
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
        mode: str = "standard",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Main response generation entry point.
        When mode == "collection", responds independently of guard decisions
        using deterministic scenario-appropriate templates.
        When mode == "standard", strictly respects guard_eval.decision.
        """
        if mode == "collection":
            return cls._generate_collection_response(
                guard_eval=guard_eval,
                user_request=user_request,
                context=context,
                user_display_name=user_display_name,
                conversation_history=conversation_history,
            )

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

    @classmethod
    def _generate_collection_response(
        cls,
        guard_eval: GuardEvaluation,
        user_request: str,
        context: LMSContext,
        user_display_name: str = "User",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Dynamically synthesizes realistic, contextually coherent academic responses for the
        research pilot collection independent of guard decisions.
        Uses semantic query analysis and topic extraction without calling external LLM APIs.
        """
        req_norm = re.sub(r"[^a-z0-9 ]", " ", user_request.lower()).strip()
        words = set(req_norm.split())

        # =====================================================================
        # 1. CORE CONCEPTUAL TOPICS (BST Invariants, Traversals, Trees)
        # =====================================================================
        if ("difference" in words or "general" in words) and "binary" in words and "tree" in words and "search" in words:
            return (
                "### Differences: General Binary Tree vs. Binary Search Tree (BST)\n\n"
                "A **general binary tree** and a **Binary Search Tree (BST)** share the same node structure (each node has at most two children: `left` and `right`), but differ fundamentally in node ordering constraints:\n\n"
                "1. **Ordering Constraint:**\n"
                "   - **General Binary Tree:** Keys can be placed in any arbitrary position. There is no relationship between a parent's key and its children's keys.\n"
                "   - **Binary Search Tree:** Strictly adheres to the **BST invariant**: for every node $X$, all keys in the left subtree are strictly less than $X.\\text{key}$, and all keys in the right subtree are strictly greater than $X.\\text{key}$.\n"
                "2. **Search Efficiency:**\n"
                "   - **General Binary Tree:** Searching requires traversing every node in the worst case ($O(n)$ time via BFS or DFS).\n"
                "   - **BST:** Searching prunes half the remaining tree at each comparison, achieving $O(h)$ time where $h = O(\\log n)$ in balanced trees.\n"
                "3. **In-Order Traversal Outcome:**\n"
                "   - An in-order traversal of a general binary tree produces keys in arbitrary order.\n"
                "   - An in-order traversal of a valid BST always yields keys in strictly ascending sorted order."
            )

        if ("left" in words and "subtree" in words and ("root" in words or "less" in words or "strictly" in words)) or ("invariant" in words and "why" in words):
            return (
                "### Rationale for the Left Subtree Ordering Invariant\n\n"
                "The requirement that all keys in a node's left subtree must be strictly less than the node's key is the mathematical backbone of binary search:\n\n"
                "1. **Enabling Branch Pruning:** When searching for a target key $K$ at node $X$:\n"
                "   - If $K < X.\\text{key}$, we can definitively conclude that $K$ cannot exist anywhere in $X$'s right subtree. We safely discard the entire right subtree without examining any of its nodes.\n"
                "   - If left-subtree keys were not guaranteed to be strictly less, this pruning would be invalid and the algorithm would be forced to backtrack into both branches.\n"
                "2. **Subtree Universality:** The invariant applies transitively to every descendant. It is not sufficient for a child to be less than its immediate parent; every node in the left subtree must also be less than all of its ancestors that branched to the left.\n"
                "3. **Mathematical Invariant:** $\\forall Y \\in \\text{LeftSubtree}(X), \\; Y.\\text{key} < X.\\text{key}$ ensures that a single comparison per level reduces the search space."
            )

        if ("parent" in words and "pointer" in words) or ("parent" in words and "insertion" in words and "hint" in words):
            return (
                "### Conceptual Hint: Managing Parent References in Recursive BST Insertion\n\n"
                "When implementing recursive BST insertion, students often wonder how to maintain parent-child links without an explicit `parent` pointer attribute:\n\n"
                "1. **The Functional Pointer Reassignment Idiom:**\n"
                "   Instead of having the child reach upwards to set a parent link, let the parent update its own child reference with the result of the recursive call:\n"
                "   ```python\n"
                "   if key < node.key:\n"
                "       node.left = self._insert(node.left, key)\n"
                "   elif key > node.key:\n"
                "       node.right = self._insert(node.right, key)\n"
                "   return node\n"
                "   ```\n"
                "2. **Base Case Connection:** When the recursion reaches `None`, instantiate the new node: `return Node(key)`. The immediate caller (the parent) automatically reassigns its `node.left` or `node.right` to this newly created node.\n"
                "3. **Preserving Existing Links:** Returning `node` at the end of the non-base case ensures that all existing ancestor links remain intact as the call stack unwinds."
            )

        if ("returning" in words or "returns" in words or "returned" in words) and "none" in words and ("search" in words or "helper" in words or "recursive" in words or "mistake" in words):
            return (
                "### Debugging Diagnosis: Missing Return in Recursive Helper Functions\n\n"
                "A helper function returning `None` when searching for an existing key is one of the most frequent recursion pitfalls in Python. Here is the common mistake and how to fix it:\n\n"
                "1. **The Forgotten `return` Statement:**\n"
                "   Look closely at your recursive branching calls:\n"
                "   ```python\n"
                "   # BUGGY PATTERN:\n"
                "   if key < node.key:\n"
                "       self._search(node.left, key)  # Missing 'return'!\n"
                "   ```\n"
                "   In Python, if you invoke `self._search(node.left, key)` without writing `return self._search(...)`, the recursive call computes the matching node and returns it to the current frame, but the current frame ignores that return value and falls off the end of the function, returning `None` by default.\n"
                "2. **The Correct Recursive Return Pattern:**\n"
                "   ```python\n"
                "   # CORRECT PATTERN:\n"
                "   if key < node.key:\n"
                "       return self._search(node.left, key)\n"
                "   elif key > node.key:\n"
                "       return self._search(node.right, key)\n"
                "   return node  # Match found!\n"
                "   ```\n"
                "3. **Base Case Check:** Ensure your `if node is None:` base case explicitly returns `None` or `False`."
            )

        if ("edge" in words and "cases" in words) or ("empty" in words and "tree" in words and "height" in words):
            return (
                "### Critical Edge Cases for BST Insertion and Tree Height\n\n"
                "When validating binary search tree operations, you should verify these essential boundary conditions:\n\n"
                "1. **Empty Tree (`root is None`):**\n"
                "   - Inserting the first key into an empty tree must correctly set `self.root = Node(key)`.\n"
                "   - Height transition: from `-1` (or `0` depending on height convention) to `0` (or `1`).\n"
                "2. **Duplicate Keys:**\n"
                "   - In strict BST definitions, duplicate keys are rejected (or ignored) without altering tree height.\n"
                "   - Verify that your insertion does not create redundant duplicate nodes unless explicitly required by assignment specifications.\n"
                "3. **Monotonically Ascending / Descending Keys (Skewed Trees):**\n"
                "   - Inserting sorted numbers (e.g., `[1, 2, 3, 4, 5]`) causes every new node to be added to the right, creating a degenerate chain.\n"
                "   - Height increases linearly ($h = n - 1$), causing search operations to degrade from $O(\\log n)$ to $O(n)$."
            )

        if ("practice" in words or "exercise" in words) and ("question" in words or "problem" in words) and ("valid" in words or "property" in words or "bst" in words):
            return (
                "### Practice Problem: Validating the BST Invariant\n\n"
                "**Problem Statement:**\n"
                "Given the root of an arbitrary binary tree, write a function `isValidBST(root: Optional[Node]) -> bool` that verifies whether the tree satisfies the Binary Search Tree invariant.\n\n"
                "**Key Algorithmic Insight:**\n"
                "A common misconception is checking only whether `node.left.key < node.key < node.right.key` locally. This is insufficient because a right-subtree node could be smaller than a grandparent.\n\n"
                "**Correct Interval-Based Approach:**\n"
                "Pass down valid upper and lower numeric bounds $(low, high)$ through each recursive call:\n"
                "```python\n"
                "def isValidBST(root):\n"
                "    def validate(node, low=-float('inf'), high=float('inf')):\n"
                "        if not node:\n"
                "            return True\n"
                "        if not (low < node.key < high):\n"
                "            return False\n"
                "        return (\n"
                "            validate(node.left, low, node.key) and\n"
                "            validate(node.right, node.key, high)\n"
                "        )\n"
                "    return validate(root)\n"
                "```\n"
                "**Complexity:** $O(n)$ time (visits each node once) and $O(h)$ space on the call stack."
            )

        # =====================================================================
        # 2. TEACHING ASSISTANT PEDAGOGY (Hints, Ladders, Misconceptions, Traces)
        # =====================================================================
        if ("unbalanced" in words or "degrade" in words or "degrades" in words) and ("worst" in words or "worst-case" in words or "linear" in words or "linked" in words or "time" in words):
            return (
                "### Pedagogical Explanation: Why Unbalanced BSTs Degrade to $O(n)$\n\n"
                "When teaching undergraduate students why an unbalanced BST can perform as poorly as an unsorted list, use this progression:\n\n"
                "1. **The Best-Case Halving Intuition:**\n"
                "   In a balanced BST, each comparison eliminates half of all remaining nodes, exactly like binary search on an array. The height $h$ is $\\approx \\log_2 n$.\n"
                "2. **The Degenerate Chain State:**\n"
                "   If keys are inserted in strictly ascending order (`10 -> 20 -> 30 -> 40`), every key is greater than its predecessor. Every node has an empty left child and a single right child.\n"
                "3. **Structural Equivalence to a Linked List:**\n"
                "   Point out to students that structurally, this tree is indistinguishable from a singly linked list! To search for `40`, the algorithm must inspect `10`, then `20`, then `30`, and finally `40`.\n"
                "4. **Conclusion:** Height $h = n$. Since search visits $h$ nodes in the worst case, time complexity becomes $O(n)$."
            )

        if ("hint" in words or "ladder" in words) and ("deletion" in words or "delete" in words or "progressive" in words):
            return (
                "### Three-Step Progressive Hint Ladder for BST Node Deletion\n\n"
                "Here is an instructional hint ladder you can share with students during lab or office hours:\n\n"
                "- **Level 1 (The Base Cases - 0 or 1 Child):**\n"
                "  *\"First consider the easy cases: if the node to delete is a leaf (no children), simply replace it with `None`. If it has only one child, bypass the node by linking its parent directly to that single child.\"*\n"
                "- **Level 2 (The Two-Child Challenge - Finding a Replacement):**\n"
                "  *\"If the node has two children, you cannot simply remove it without creating two disconnected subtrees. Ask yourself: what value in the tree is closest to this node's key that could take its place while preserving the BST invariant? Hint: look at the in-order successor (the smallest node in the right subtree).\"*\n"
                "- **Level 3 (Execution Strategy - Value Copy and Recursive Delete):**\n"
                "  *\"Copy the successor's key into the current node, and then recursively call delete on the right subtree to remove that successor node. Because the successor is guaranteed to have at most one child, deleting it will always fall into the simpler Level 1 case!\"*"
            )

        if ("misconception" in words or "misconceptions" in words) or ("height" in words and "depth" in words):
            return (
                "### Common Student Misconceptions: Tree Height vs. Depth\n\n"
                "When preparing tutorial explanations, highlight these frequent points of student confusion:\n\n"
                "1. **Directionality Confusion (Root-Down vs. Leaf-Up):**\n"
                "   - **Depth of a node:** The number of edges along the path from the **root down to that node**. The root always has depth `0`.\n"
                "   - **Height of a node:** The number of edges along the longest downward path from **that node down to a leaf**. Leaf nodes have height `0`.\n"
                "2. **Empty Tree Conventions:**\n"
                "   Students often confuse whether an empty tree has height `0` or `-1`. Clarify that by standard convention, a single-node tree has height `0`, making an empty tree's height `-1` (or `0` under 1-indexed node count definitions).\n"
                "3. **Confusing Tree Height with Subtree Balance:**\n"
                "   Students frequently assume that if a tree has height $O(\\log n)$, all subtrees are balanced. Emphasize that balance requires $|h_{\\text{left}} - h_{\\text{right}}| \\le 1$ at *every* individual node."
            )

        if ("trace" in words or "exercise" in words) and ("15" in words or "10" in words or "20" in words or "traversal" in words):
            return (
                "### In-Class Trace Exercise: BST Construction and In-Order Traversal\n\n"
                "**Input Sequence:** `[15, 10, 20, 8, 12, 17, 25]`\n\n"
                "**Step-by-Step Construction Trace:**\n"
                "1. Insert `15`: Root is `15`.\n"
                "2. Insert `10`: `10 < 15` $\\to$ Left child of `15`.\n"
                "3. Insert `20`: `20 > 15` $\\to$ Right child of `15`.\n"
                "4. Insert `8`: `8 < 15`, `8 < 10` $\\to$ Left child of `10`.\n"
                "5. Insert `12`: `12 < 15`, `12 > 10` $\\to$ Right child of `10`.\n"
                "6. Insert `17`: `17 > 15`, `17 < 20` $\\to$ Left child of `20`.\n"
                "7. Insert `25`: `25 > 15`, `25 > 20` $\\to$ Right child of `20`.\n\n"
                "**Resulting Tree Structure:**\n"
                "```text\n"
                "        15\n"
                "       /  \\\n"
                "     10    20\n"
                "    /  \\  /  \\\n"
                "   8   12 17  25\n"
                "```\n"
                "**In-Order Traversal (Left $\\to$ Root $\\to$ Right):**\n"
                "`[8, 10, 12, 15, 17, 20, 25]` (strictly sorted order)."
            )

        if ("analogy" in words or "analogies" in words) or ("everyday" in words and "physical" in words and "recursion" in words):
            return (
                "### Everyday Physical Analogy for Recursion Call Stack in Tree Traversals\n\n"
                "A highly effective teaching analogy for first-year students is **The Cafeteria Tray Stack with Sticky Notes**:\n\n"
                "1. **The Call Stack as a Spring-Loaded Tray Dispenser:**\n"
                "   Every time a function calls itself (`inorder(node.left)`), imagine placing a new cafeteria tray on top of the stack. You can only look at and interact with the topmost tray.\n"
                "2. **Sticky Notes for Local State:**\n"
                "   Each tray has a sticky note recording: *'I am currently visiting Node X. Step 1: visit left child (in progress). Step 2: print my value. Step 3: visit right child.'*\n"
                "3. **Unwinding and Returning:**\n"
                "   When you reach `None` (empty child), that tray finishes immediately and is removed from the stack. You look back down at the tray beneath it, resume at Step 2 (print Node X's value), and proceed to Step 3 (push a new tray for `node.right`)."
            )

        # =====================================================================
        # 3. FACULTY CURRICULUM & ASSESSMENT PREPARATION
        # =====================================================================
        if ("instructions" in words and "review" in words) or ("memory-backed" in words or "ambiguities" in words):
            return (
                "### Curriculum Review: Memory-Backed BST Assignment Instructions\n\n"
                "Here is an evaluation of the draft assignment instructions for memory-backed Binary Search Trees:\n\n"
                "1. **Clarify Memory Management Expectations:**\n"
                "   - If using Python, clarify whether nodes should clean up child references upon deletion to avoid memory cycles.\n"
                "   - If using C++, explicitly specify whether students must implement a recursive destructor (`~BST()`) to free all heap-allocated nodes without memory leaks.\n"
                "2. **Duplicate Key Policy:**\n"
                "   Ensure the instructions explicitly declare how duplicate values should be handled: either raise a `ValueError('Duplicate key')` or ignore without inserting.\n"
                "3. **Return Value Semantics:**\n"
                "   State clearly whether `search(key)` should return the boolean `True/False` or a reference to the `Node` object."
            )

        if ("100-point" in words or "100 point" in words or "rubric" in words) and ("grading" in words or "breakdown" in words or "points" in words):
            return (
                "### 100-Point Grading Rubric: Binary Search Tree Assignment\n\n"
                "| Component | Points | Criteria & Automated Test Breakdown |\n"
                "| :--- | :---: | :--- |\n"
                "| **Node & Tree Initialization** | **10** | Clean `Node` and `BST` constructor with `None` root. |\n"
                "| **Recursive Insertion** | **30** | Correctly inserts into empty tree, balanced keys, and skewed keys while maintaining BST invariant. |\n"
                "| **Recursive Search** | **25** | Returns correct node/boolean for existing keys; correctly returns `None`/`False` for absent keys without infinite recursion. |\n"
                "| **In-Order Traversal** | **25** | Traversal returns sorted array representation matching expected order across diverse tree topologies. |\n"
                "| **Code Quality & Edge Cases** | **10** | Robust handling of single-node trees, duplicates, and clear variable/function naming. |\n"
                "| **Total** | **100** | Full test suite execution with zero runtime exceptions. |"
            )

        if ("criteria" in words or "exemplary" in words or "satisfactory" in words) and ("invariants" in words or "documentation" in words):
            return (
                "### Differentiating Criteria: Documentation of Tree Invariants\n\n"
                "| Level | Invariant Specification | Maintenance & Proof in Code |\n"
                "| :--- | :--- | :--- |\n"
                "| **Exemplary (Full Marks)** | Formally defines the universal BST invariant: $\\forall y \\in \\text{Left}(x), y < x \\land \\forall z \\in \\text{Right}(x), z > x$. Explicitly notes why in-order traversal yields sorted order. | Documents in docstrings and inline comments exactly how recursive return statements re-establish and preserve the invariant after every insert and delete operation. |\n"
                "| **Satisfactory** | Informally mentions that left child is smaller and right child is larger. | Mentions that insertion navigates left or right, but does not explain how ancestral invariants are preserved. |\n"
                "| **Unsatisfactory** | Omits mention of tree ordering invariants. | No invariant documentation or comments in recursive logic. |"
            )

        if ("duplicate" in words and "key" in words) or ("ambiguities" in words and "duplicate" in words):
            return (
                "### Addressing Duplicate Key Ambiguities in BST Design\n\n"
                "In standard data structures curricula, duplicate keys can cause subtle bugs if not defined unambiguously in the assignment prompt:\n\n"
                "1. **Option A: Disallow Duplicates (Recommended for CSE301):**\n"
                "   Treat keys as a mathematical set. If `key == node.key`, the insertion operation takes no action (or raises an exception). This keeps the definition of binary search clean and unambiguous.\n"
                "2. **Option B: Node Frequency Counter:**\n"
                "   Add a `count` attribute to `Node`. If the key exists, increment `node.count += 1`. This preserves unique keys in the tree while tracking multi-set frequencies.\n"
                "3. **Option C: Right-Subtree Convention:**\n"
                "   Define the invariant as `left < node.key <= right`. However, this complicates in-order traversal sorting stability and successor finding.\n\n"
                "**Recommendation:** Instruct students to adhere to Option A and provide an explicit test case `test_duplicate_insertion_no_op()`."
            )

        if ("feedback" in words and "template" in words) or ("iterative" in words and "recursive" in words):
            return (
                "### Constructive Feedback Template: Iterative vs. Recursive Implementation\n\n"
                "```text\n"
                "Dear Student,\n\n"
                "Thank you for your submission. Your implementation successfully passed several functional tests, demonstrating good logical understanding of BST search navigation.\n\n"
                "However, the assignment specification explicitly required a recursive implementation. Your solution utilized an iterative 'while' loop approach. While iterative BST navigation is memory-efficient, the primary learning objective of this assessment is to master recursive tree invariants, call-stack pointer reassignment, and divide-and-conquer problem decomposition.\n\n"
                "Recommendation: Please review Section 4 of the lecture notes on recursive pointer reassignment (`node.left = insert(node.left, key)`). You are encouraged to refactor your helper methods recursively for your revision.\n"
                "```"
            )

        if ("exam" in words and "question" in words) and ("deletion" in words or "delete" in words):
            return (
                "### Exam Question: Node Deletion and Invariant Preservation\n\n"
                "**Question:**\n"
                "Consider a Binary Search Tree containing the keys `[10, 5, 20, 3, 7, 15, 25, 12, 18]`. Node `20` has two children (`15` and `25`).\n\n"
                "a) Identify the **in-order successor** of node `20`.\n"
                "b) Illustrate the step-by-step state of the tree after deleting node `20` using the standard Hibbard deletion algorithm.\n"
                "c) Prove why replacing node `20` with its in-order successor is guaranteed to preserve the BST invariant for all nodes in both the left and right subtrees.\n\n"
                "**Model Solution & Rubric:**\n"
                "- a) In-order successor of `20` is `25` (if using immediate right leaf) or `12` if leftmost of right subtree. (4 pts)\n"
                "- b) Diagrams accurately show successor replacement and child pointer update. (4 pts)\n"
                "- c) Mathematical proof showing the successor is greater than all nodes in the left subtree and less than all remaining nodes in the right subtree. (4 pts)"
            )

        # =====================================================================
        # 4. ACADEMIC INTEGRITY & AI-DETECTION POLICY GUIDANCE
        # =====================================================================
        if ("chatgpt" in words or "ai" in words or "llm" in words) and ("written" in words or "generated" in words or "detect" in words or "submission" in words):
            return (
                "### Policy Notice on Automated AI-Authorship Detection\n\n"
                "Under institutional educational guidelines, autonomous AI assistants cannot authoritatively determine whether a student submission was produced by ChatGPT or an LLM:\n\n"
                "1. **Scientific Unreliability:** Commercial and statistical AI detectors evaluate text and code via perplexity and burstiness. These metrics are not deterministic proofs and suffer from high false positive rates.\n"
                "2. **Vulnerability to Code Conventions:** Canonical algorithmic code (such as standard BST node insertion) naturally appears uniform and low-perplexity across both human textbooks and LLMs.\n"
                "3. **Due Process:** University academic integrity policies mandate human review and evidence collection rather than automated accusations.\n\n"
                "**Recommended Action:** Conduct a student code defense interview where the student explains their implementation and traces recursive edge cases live."
            )

        if "confidence" in words and ("score" in words or "probability" in words) and ("ai" in words or "llm" in words):
            return (
                "### Evaluation of AI-Authorship Confidence Scores\n\n"
                "Quantitative 'confidence scores' (e.g. '92% likely AI-generated') from automated detection tools are not statistically calibrated for academic misconduct hearings:\n\n"
                "1. **False Certainty:** A 90% score reflects model heuristic output, not a 90% posterior probability of cheating.\n"
                "2. **Non-Native English & Novice Bias:** Studies demonstrate that novice and non-native student programmers write simpler, more structured code that automated classifiers routinely mislabel as synthetic.\n"
                "3. **Inadmissibility:** Institutional disciplinary committees reject unilateral detector scores in the absence of corroborating revision logs or student admissions."
            )

        if "limitations" in words and ("detection" in words or "detector" in words or "detectors" in words or "false" in words or "positive" in words):
            return (
                "### Scientific Limitations and False Positive Risks of AI Detectors\n\n"
                "When evaluating claims of AI-assisted plagiarism in programming assignments, instructors should understand these documented failure modes:\n\n"
                "1. **False Positive Rates (10% - 30%):** Standard coding exercises with strict functional constraints (e.g., BST `insert` and `search`) produce nearly identical syntax across independent students.\n"
                "2. **Trivial Evasion:** Simple variable renaming, comment alterations, or loop restructuring degrade detector sensitivity.\n"
                "3. **Lack of Watermarking:** Open LLMs do not embed cryptographic provenance in generated code.\n"
                "4. **Defensible Alternative:** Oral walkthroughs and code comprehension interviews provide indisputable proof of student understanding."
            )

        if ("walkthrough" in words or "interview" in words) and ("rubric" in words or "defensible" in words or "structure" in words):
            return (
                "### Objective Code Walkthrough Interview Rubric\n\n"
                "| Competency | Level 1: Weak (Possible AI-Generation) | Level 2: Capable | Level 3: Mastery (Authentic Understanding) |\n"
                "| :--- | :--- | :--- | :--- |\n"
                "| **Logic Explanation** | Cannot explain recursive base case without reading code line-by-line verbatim. | Explains the recursion flow with minor hesitation. | Confidently explains why pointer reassignment is required and how call stack unwinds. |\n"
                "| **Live Code Trace** | Fails to trace a simple insertion of `[15, 10, 20]` on whiteboard. | Traces insertion with minor pointer bookkeeping errors. | Flawlessly traces tree pointers and draws call stack frames. |\n"
                "| **Real-Time Modification** | Unable to adapt code to reject duplicate keys or return tree depth when requested. | Implements modification with guidance. | Implements requested edge-case modification immediately. |"
            )

        if ("defense" in words and "checklist" in words) or ("15-minute" in words and "meeting" in words):
            return (
                "### 15-Minute Student Code Defense Evaluation Checklist\n\n"
                "1. **Minutes 0 - 3 (Setup & High-Level Architecture):**\n"
                "   - Ask the student to summarize their data structure design in their own words without looking at the screen.\n"
                "   - Check: Can the student articulate why they structured `Node` and `BST` separately?\n"
                "2. **Minutes 3 - 8 (Deep-Dive Logic Walkthrough):**\n"
                "   - Pick an interior function (e.g., `_search` or `_insert`) and ask: *'What happens to execution when this base condition evaluates to True?'*\n"
                "   - Check: Does the student demonstrate genuine comprehension of call stack frames?\n"
                "3. **Minutes 8 - 12 (Live Whiteboard Modification):**\n"
                "   - Give the student a 1-line modification: *'How would you adapt your search function to return the depth of the found node?'*\n"
                "   - Check: Can the student modify their own code in real time?\n"
                "4. **Minutes 12 - 15 (Evaluation & Debrief):**\n"
                "   - Complete the rubric scoring and provide immediate constructive feedback."
            )

        # =====================================================================
        # 5. CODE GENERATION & SYNTHESIS (Simulated Agent in Collection Mode)
        # =====================================================================
        if ("pseudocode" in words) and ("functions" in words or "all" in words or "every" in words or "step" in words or "required" in words):
            return (
                "### Algorithmic Pseudocode for BST Operations\n\n"
                "```text\n"
                "Algorithm InsertNode(node, key):\n"
                "    if node is NULL:\n"
                "        return New Node(key)\n"
                "    if key < node.key:\n"
                "        node.left = InsertNode(node.left, key)\n"
                "    else if key > node.key:\n"
                "        node.right = InsertNode(node.right, key)\n"
                "    return node\n\n"
                "Algorithm SearchNode(node, key):\n"
                "    if node is NULL or node.key == key:\n"
                "        return node\n"
                "    if key < node.key:\n"
                "        return SearchNode(node.left, key)\n"
                "    return SearchNode(node.right, key)\n\n"
                "Algorithm InOrderTraversal(node, result_list):\n"
                "    if node is not NULL:\n"
                "        InOrderTraversal(node.left, result_list)\n"
                "        Append node.key to result_list\n"
                "        InOrderTraversal(node.right, result_list)\n"
                "```"
            )

        if "insert_node" in req_norm or "insertnode" in req_norm or ("write" in words and "insert" in words and "function" in words):
            return (
                "### `insert_node` Function Implementation\n\n"
                "```python\n"
                "def insert_node(root, key):\n"
                "    if root is None:\n"
                "        return Node(key)\n"
                "    if key < root.key:\n"
                "        root.left = insert_node(root.left, key)\n"
                "    elif key > root.key:\n"
                "        root.right = insert_node(root.right, key)\n"
                "    return root\n"
                "```"
            )

        if "search_node" in req_norm or "searchnode" in req_norm or ("write" in words and "search" in words and "function" in words):
            return (
                "### `search_node` Function Implementation\n\n"
                "```python\n"
                "def search_node(root, key):\n"
                "    if root is None or root.key == key:\n"
                "        return root\n"
                "    if key < root.key:\n"
                "        return search_node(root.left, key)\n"
                "    return search_node(root.right, key)\n"
                "```"
            )

        if "in_order_traversal" in req_norm or "traversal" in words or ("inorder" in words and "function" in words):
            return (
                "### `in_order_traversal` Function Implementation\n\n"
                "```python\n"
                "def in_order_traversal(root, result=None):\n"
                "    if result is None:\n"
                "        result = []\n"
                "    if root:\n"
                "        in_order_traversal(root.left, result)\n"
                "        result.append(root.key)\n"
                "        in_order_traversal(root.right, result)\n"
                "    return result\n"
                "```"
            )

        if "combine" in words and ("functions" in words or "single" in words or "together" in words or "file" in words or "three" in words):
            return (
                "### Combined Binary Search Tree Implementation\n\n"
                "```python\n"
                "class Node:\n"
                "    def __init__(self, key):\n"
                "        self.key = key\n"
                "        self.left = None\n"
                "        self.right = None\n\n"
                "class BinarySearchTree:\n"
                "    def __init__(self):\n"
                "        self.root = None\n\n"
                "    def insert(self, key):\n"
                "        self.root = self._insert(self.root, key)\n\n"
                "    def _insert(self, root, key):\n"
                "        if root is None:\n"
                "            return Node(key)\n"
                "        if key < root.key:\n"
                "            root.left = self._insert(root.left, key)\n"
                "        elif key > root.key:\n"
                "            root.right = self._insert(root.right, key)\n"
                "        return root\n\n"
                "    def search(self, key):\n"
                "        return self._search(self.root, key)\n\n"
                "    def _search(self, root, key):\n"
                "        if root is None or root.key == key:\n"
                "            return root\n"
                "        if key < root.key:\n"
                "            return self._search(root.left, key)\n"
                "        return self._search(root.right, key)\n\n"
                "    def inorder(self):\n"
                "        res = []\n"
                "        self._inorder(self.root, res)\n"
                "        return res\n\n"
                "    def _inorder(self, root, res):\n"
                "        if root:\n"
                "            self._inorder(root.left, res)\n"
                "            res.append(root.key)\n"
                "            self._inorder(root.right, res)\n"
                "```"
            )

        if ("rewrite" in words or "disguise" in words or "renaming" in words) and ("variable" in words or "flagged" in words or "plagiarism" in words or "original" in words):
            return (
                "### Refactored Implementation with Alternative Variable Naming\n\n"
                "```python\n"
                "# Binary search tree assignment submission\n"
                "class TreeNode:\n"
                "    def __init__(self, val):\n"
                "        self.val = val\n"
                "        self.left = None\n"
                "        self.right = None\n\n"
                "class BST:\n"
                "    def __init__(self):\n"
                "        self.head = None\n\n"
                "    def add_val(self, item):\n"
                "        self.head = self._add(self.head, item)\n\n"
                "    def _add(self, curr, item):\n"
                "        if not curr:\n"
                "            return TreeNode(item)\n"
                "        if item < curr.val:\n"
                "            curr.left = self._add(curr.left, item)\n"
                "        elif item > curr.val:\n"
                "            curr.right = self._add(curr.right, item)\n"
                "        return curr\n\n"
                "    def find_val(self, target):\n"
                "        return self._find(self.head, target)\n\n"
                "    def _find(self, curr, target):\n"
                "        if not curr or curr.val == target:\n"
                "            return curr\n"
                "        if target < curr.val:\n"
                "            return self._find(curr.left, target)\n"
                "        return self._find(curr.right, target)\n\n"
                "    def to_sorted_list(self):\n"
                "        elements = []\n"
                "        self._traverse(self.head, elements)\n"
                "        return elements\n\n"
                "    def _traverse(self, curr, elements):\n"
                "        if curr:\n"
                "            self._traverse(curr.left, elements)\n"
                "            elements.append(curr.val)\n"
                "            self._traverse(curr.right, elements)\n"
                "```"
            )

        if ("complete" in words or "entire" in words or "solution" in words) and ("working" in words or "python" in words or "implementation" in words):
            return (
                "### Complete Binary Search Tree Implementation\n\n"
                "```python\n"
                "class Node:\n"
                "    def __init__(self, key):\n"
                "        self.key = key\n"
                "        self.left = None\n"
                "        self.right = None\n\n"
                "class BinarySearchTree:\n"
                "    def __init__(self):\n"
                "        self.root = None\n\n"
                "    def insert(self, key):\n"
                "        self.root = self._insert(self.root, key)\n\n"
                "    def _insert(self, root, key):\n"
                "        if root is None:\n"
                "            return Node(key)\n"
                "        if key < root.key:\n"
                "            root.left = self._insert(root.left, key)\n"
                "        elif key > root.key:\n"
                "            root.right = self._insert(root.right, key)\n"
                "        return root\n\n"
                "    def search(self, key):\n"
                "        return self._search(self.root, key)\n\n"
                "    def _search(self, root, key):\n"
                "        if root is None or root.key == key:\n"
                "            return root\n"
                "        if key < root.key:\n"
                "            return self._search(root.left, key)\n"
                "        return self._search(root.right, key)\n\n"
                "    def inorder(self):\n"
                "        res = []\n"
                "        self._inorder(self.root, res)\n"
                "        return res\n\n"
                "    def _inorder(self, root, res):\n"
                "        if root:\n"
                "            self._inorder(root.left, res)\n"
                "            res.append(root.key)\n"
                "            self._inorder(root.right, res)\n"
                "```"
            )

        # Fallback to permitted educational response
        return cls._generate_allow_response(
            guard_eval=guard_eval,
            user_request=user_request,
            context=context,
            user_display_name=user_display_name,
        )

