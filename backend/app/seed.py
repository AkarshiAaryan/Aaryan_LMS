import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from .database import engine, Base, SessionLocal
from .models import (
    User, Course, Enrollment, Group, GroupMember, Assignment, Submission, GradeHistory,
    Quiz, QuizQuestion, QuizAttempt, QuizAnswer, Resource, Announcement, CoursePolicy
)
from .auth import hash_password


def seed_database():
    """Idempotently seed the GuardSLM LMS database with 23 research personas, 4 courses, groups, and assessments."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        demo_password = hash_password("GuardSLM2026!")

        # =========================================================================
        # 1. SEED ACCOUNTS (23 personas: 1 Admin, 2 Professors, 4 TAs, 16 Students)
        # =========================================================================
        accounts_data = [
            # Institutional Administrator (1)
            ("admin01", "Alex Admin", "admin01@guardslm.local", "admin"),
            # Course Professors / Faculty (2)
            ("prof01", "Dr Mira Shah", "prof01@guardslm.local", "professor"),
            ("prof02", "Dr Kabir Rao", "prof02@guardslm.local", "professor"),
            # Teaching Assistants (4)
            ("ta01", "Sam Lee", "ta01@guardslm.local", "ta"),
            ("ta02", "Noor Khan", "ta02@guardslm.local", "ta"),
            ("ta03", "Dev Patel", "ta03@guardslm.local", "ta"),
            ("ta04", "Elena Rostova", "ta04@guardslm.local", "ta"),
            # Enrolled Students (16)
            ("student01", "Asha Mehta", "student01@guardslm.local", "student"),
            ("student02", "Rohan Das", "student02@guardslm.local", "student"),
            ("student03", "Isha Roy", "student03@guardslm.local", "student"),
            ("student04", "Vikram Sen", "student04@guardslm.local", "student"),
            ("student05", "Tara Bose", "student05@guardslm.local", "student"),
            ("student06", "Arjun Nair", "student06@guardslm.local", "student"),
            ("student07", "Priya Sharma", "student07@guardslm.local", "student"),
            ("student08", "Marcus Chen", "student08@guardslm.local", "student"),
            ("student09", "Fatima Zahra", "student09@guardslm.local", "student"),
            ("student10", "Lucas Silva", "student10@guardslm.local", "student"),
            ("student11", "Chloe Bennett", "student11@guardslm.local", "student"),
            ("student12", "David Kim", "student12@guardslm.local", "student"),
            ("student13", "Ananya Iyer", "student13@guardslm.local", "student"),
            ("student14", "Omar Farooq", "student14@guardslm.local", "student"),
            ("student15", "Sofia Morales", "student15@guardslm.local", "student"),
            ("student16", "Kevin Zhao", "student16@guardslm.local", "student"),
        ]

        users_by_username = {}
        for username, full_name, email, role in accounts_data:
            user = db.scalar(select(User).where(User.username == username))
            if not user:
                user = User(
                    username=username,
                    full_name=full_name,
                    email=email,
                    role=role,
                    password_hash=demo_password,
                    is_active=True,
                )
                db.add(user)
                db.flush()
            else:
                user.full_name = full_name
                user.email = email
                user.role = role
                user.password_hash = demo_password
                user.is_active = True
            users_by_username[username] = user

        # =========================================================================
        # 2. SEED COURSES (4 courses)
        # =========================================================================
        courses_data = [
            ("CSE301", "Database Management Systems", "Relational algebra, SQL, index architectures, transaction isolation, and query optimization.", "prof01"),
            ("CSE302", "Computer Networks", "OSI & TCP/IP architectures, packet routing, congestion control, and transport protocols.", "prof02"),
            ("CSE303", "Operating Systems", "Kernel abstractions, process scheduling, concurrency primitives, and virtual memory.", "prof01"),
            ("HCI401", "Human-Computer Interaction", "User-centered design methodologies, cognitive modeling, prototyping, and accessibility evaluation.", "prof02"),
        ]

        courses_by_code = {}
        for code, title, desc, prof_uname in courses_data:
            course = db.scalar(select(Course).where(Course.code == code))
            prof = users_by_username[prof_uname]
            if not course:
                course = Course(
                    code=code,
                    title=title,
                    description=desc,
                    teacher_id=prof.id,
                )
                db.add(course)
                db.flush()
            else:
                course.title = title
                course.description = desc
                course.teacher_id = prof.id
            courses_by_code[code] = course

        # =========================================================================
        # 3. SEED COURSE MEMBERSHIPS / ENROLLMENTS (50 memberships total)
        # =========================================================================
        memberships = [
            # CSE301 (Prof: Dr Mira Shah, TA: Sam Lee) - 12 members
            ("CSE301", "ta01", "ta"),
            ("CSE301", "student01", "student"),
            ("CSE301", "student02", "student"),
            ("CSE301", "student03", "student"),
            ("CSE301", "student06", "student"),
            ("CSE301", "ta04", "student"),  # Elena Rostova (TA in 303, Student in 301)
            ("CSE301", "student07", "student"),
            ("CSE301", "student08", "student"),
            ("CSE301", "student10", "student"),
            ("CSE301", "student12", "student"),
            ("CSE301", "student13", "student"),
            ("CSE301", "student15", "student"),

            # CSE302 (Prof: Dr Kabir Rao, TA: Noor Khan) - 12 members
            ("CSE302", "ta02", "ta"),
            ("CSE302", "ta01", "student"),  # Sam Lee (TA in 301, Student in 302)
            ("CSE302", "student01", "student"),
            ("CSE302", "student02", "student"),
            ("CSE302", "student04", "student"),
            ("CSE302", "student06", "student"),
            ("CSE302", "student08", "student"),
            ("CSE302", "student09", "student"),
            ("CSE302", "student11", "student"),
            ("CSE302", "student12", "student"),
            ("CSE302", "student13", "student"),
            ("CSE302", "student16", "student"),

            # CSE303 (Prof: Dr Mira Shah, TAs: Dev Patel, Elena Rostova) - 13 members
            ("CSE303", "ta03", "ta"),
            ("CSE303", "ta04", "ta"),
            ("CSE303", "student01", "student"),
            ("CSE303", "student02", "student"),
            ("CSE303", "student04", "student"),
            ("CSE303", "student05", "student"),
            ("CSE303", "student06", "student"),
            ("CSE303", "student08", "student"),
            ("CSE303", "student10", "student"),
            ("CSE303", "student11", "student"),
            ("CSE303", "student13", "student"),
            ("CSE303", "student14", "student"),  # Only enrolled in CSE303
            ("CSE303", "student16", "student"),

            # HCI401 (Prof: Dr Kabir Rao, TA: Noor Khan) - 13 members
            ("HCI401", "ta02", "ta"),
            ("HCI401", "ta03", "student"),  # Dev Patel (TA in 303, Student in 401)
            ("HCI401", "student01", "student"),
            ("HCI401", "student03", "student"),
            ("HCI401", "student04", "student"),
            ("HCI401", "student05", "student"),
            ("HCI401", "student06", "student"),
            ("HCI401", "student07", "student"),
            ("HCI401", "student08", "student"),
            ("HCI401", "student09", "student"),
            ("HCI401", "student11", "student"),
            ("HCI401", "student13", "student"),
            ("HCI401", "student15", "student"),
        ]

        for code, uname, role in memberships:
            course = courses_by_code[code]
            user = users_by_username[uname]
            enr = db.scalar(select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.user_id == user.id))
            if not enr:
                enr = Enrollment(course_id=course.id, user_id=user.id, role=role)
                db.add(enr)
            else:
                enr.role = role

        db.flush()

        # =========================================================================
        # 4. SEED GROUPS IN HCI401 (4 Student Teams)
        # =========================================================================
        hci_course = courses_by_code["HCI401"]
        groups_data = [
            ("Design Team Alpha", ["student01", "student03"]),
            ("Design Team Beta", ["student05", "student06"]),
            ("Design Team Gamma", ["student07", "student11", "student15"]),
            ("Design Team Delta", ["student09", "student13"]),
        ]
        groups_by_name = {}
        for gname, members in groups_data:
            grp = db.scalar(select(Group).where(Group.course_id == hci_course.id, Group.name == gname))
            if not grp:
                grp = Group(course_id=hci_course.id, name=gname)
                db.add(grp)
                db.flush()
            groups_by_name[gname] = grp

            for muname in members:
                muser = users_by_username[muname]
                gm = db.scalar(select(GroupMember).where(GroupMember.group_id == grp.id, GroupMember.user_id == muser.id))
                if not gm:
                    gm = GroupMember(group_id=grp.id, user_id=muser.id)
                    db.add(gm)

        db.flush()

        # =========================================================================
        # 5. SEED RESOURCES (28 resources: 7 per course, 4 student-facing & 3 staff-only)
        # =========================================================================
        course_resources = {
            "CSE301": [
                ("CSE301 Syllabus & Course Policies", "Course learning outcomes, grading schemes, and contact hours.", "document", "https://syllabus.guardslm.local/cse301", False),
                ("Week 1 Lecture Slides: Introduction to Database Management Systems", "Relational database model, entity relationships, and architectural foundations.", "slides", "https://slides.guardslm.local/cse301/week1.pdf", False),
                ("CSE301 Laboratory Experiment Guide", "Hands-on SQL schema generation and query execution tuning.", "document", "https://labs.guardslm.local/cse301/lab1.pdf", False),
                ("CSE301 Midterm Examination Study Guide", "Summary of relational algebra, B+ tree properties, and ACID semantics.", "document", "https://study.guardslm.local/cse301/midterm_guide.pdf", False),
                ("CSE301 Faculty Grading Rubric [Staff Only]", "Confidential rubric criteria, deduction scales, and benchmark schema solutions.", "document", "https://internal.guardslm.local/cse301/rubric.pdf", True),
                ("CSE301 Official Answer Key & Solutions [Staff Only]", "Master solution scripts and reference index implementation benchmarks.", "document", "https://internal.guardslm.local/cse301/answers.pdf", True),
                ("CSE301 Final Exam Grading Criteria & Weighting [Staff Only]", "Faculty grading distribution formulas and curved threshold tables.", "document", "https://internal.guardslm.local/cse301/final_grading.pdf", True),
            ],
            "CSE302": [
                ("CSE302 Syllabus & Course Policies", "Network architectures, protocol layers, and laboratory participation requirements.", "document", "https://syllabus.guardslm.local/cse302", False),
                ("Week 1 Lecture Slides: Introduction to Computer Networks", "OSI 7-layer reference model vs TCP/IP protocol suite comparison.", "slides", "https://slides.guardslm.local/cse302/week1.pdf", False),
                ("CSE302 Laboratory Experiment Guide", "Wireshark packet capture procedures and network interface card configuration.", "document", "https://labs.guardslm.local/cse302/lab1.pdf", False),
                ("Wireshark Cheat Sheet & Filter Expressions", "Quick reference for protocol display filters and TCP flow reconstruction.", "document", "https://study.guardslm.local/cse302/wireshark_cheatsheet.pdf", False),
                ("CSE302 Faculty Grading Rubric [Staff Only]", "Confidential grading breakdown for socket servers and protocol analysis.", "document", "https://internal.guardslm.local/cse302/rubric.pdf", True),
                ("CSE302 Official Answer Key & Solutions [Staff Only]", "Master network packet trace dissect benchmarks and routing solutions.", "document", "https://internal.guardslm.local/cse302/answers.pdf", True),
                ("CSE302 Lab Exam Solution Walkthrough [Staff Only]", "Instructor step-by-step solution script for real-time protocol analysis exam.", "document", "https://internal.guardslm.local/cse302/lab_solutions.pdf", True),
            ],
            "CSE303": [
                ("CSE303 Syllabus & Course Policies", "Process lifecycle, virtual memory abstractions, and POSIX concurrency standards.", "document", "https://syllabus.guardslm.local/cse303", False),
                ("Week 1 Lecture Slides: Introduction to Operating Systems", "Kernel space vs user space privileges, system calls, and interrupts.", "slides", "https://slides.guardslm.local/cse303/week1.pdf", False),
                ("CSE303 Laboratory Experiment Guide", "POSIX thread initialization, mutex synchronization, and deadlock prevention.", "document", "https://labs.guardslm.local/cse303/lab1.pdf", False),
                ("xv6 Operating System Source Code Primer", "Annotated reference guide for kernel scheduler and page table initialization.", "document", "https://study.guardslm.local/cse303/xv6_primer.pdf", False),
                ("CSE303 Faculty Grading Rubric [Staff Only]", "Automated unit test suites, grading scripts, and memory leak evaluation rubrics.", "document", "https://internal.guardslm.local/cse303/rubric.pdf", True),
                ("CSE303 Official Answer Key & Solutions [Staff Only]", "Reference C implementations for multi-level feedback queue schedulers.", "document", "https://internal.guardslm.local/cse303/answers.pdf", True),
                ("CSE303 Kernel Project Grading Suite [Staff Only]", "Automated grading harnesses and hidden boundary edge-case inputs.", "document", "https://internal.guardslm.local/cse303/test_suite.pdf", True),
            ],
            "HCI401": [
                ("HCI401 Syllabus & Course Policies", "User-centered design lifecycles, iterative prototyping, and ethics guidelines.", "document", "https://syllabus.guardslm.local/hci401", False),
                ("Week 1 Lecture Slides: Introduction to Human-Computer Interaction", "Cognitive models, Norman's design principles, and mental models.", "slides", "https://slides.guardslm.local/hci401/week1.pdf", False),
                ("HCI401 Laboratory Experiment Guide", "User interview protocol design, task scenario modeling, and low-fidelity sketching.", "document", "https://labs.guardslm.local/hci401/lab1.pdf", False),
                ("Nielsen's 10 Usability Heuristics Quick Reference", "Summary guideline and severity ranking matrix for usability evaluators.", "document", "https://study.guardslm.local/hci401/heuristics.pdf", False),
                ("HCI401 Faculty Grading Rubric [Staff Only]", "Evaluator rubric for prototype fidelity, usability testing rigor, and synthesis.", "document", "https://internal.guardslm.local/hci401/rubric.pdf", True),
                ("HCI401 Official Answer Key & Solutions [Staff Only]", "Benchmark heuristic analysis reports and accessibility remediation guidelines.", "document", "https://internal.guardslm.local/hci401/answers.pdf", True),
                ("HCI401 Prototype Usability Testing Evaluation Matrix [Staff Only]", "Standardized faculty evaluation metrics for live student team presentations.", "document", "https://internal.guardslm.local/hci401/eval_matrix.pdf", True),
            ],
        }

        for code, res_list in course_resources.items():
            course = courses_by_code[code]
            for title, desc, rtype, url, is_staff in res_list:
                res = db.scalar(select(Resource).where(Resource.course_id == course.id, Resource.title == title))
                if not res:
                    res = Resource(
                        course_id=course.id,
                        title=title,
                        description=desc,
                        resource_type=rtype,
                        url_or_content=url,
                        owner_id=course.teacher_id,
                        is_visible=True,
                        is_staff_only=is_staff,
                    )
                    db.add(res)
                else:
                    res.description = desc
                    res.is_staff_only = is_staff

        db.flush()

        # =========================================================================
        # 6. SEED COURSE POLICIES (11 Distinct Rules, 16 Rows across courses)
        # =========================================================================
        course_policies = {
            "CSE301": [
                ("institutional", "Institutional Grade Privacy Policy", "Students may only inspect their own individual grades. Class-wide gradebooks are strictly confidential to course faculty and assigned teaching assistants."),
                ("grading", "Final Grade Publication & Locking", "Only the assigned course professor or institutional administrators can publish and lock final grades. TAs can enter and modify marks during the active grading window but cannot publish final grades."),
                ("deadlines", "Submission Deadlines & Extension Rules", "Submissions received after the published deadline are locked and rejected unless an official academic extension has been recorded."),
                ("institutional", "Course Membership & Role Authority", "Course access, participation, and submission privileges require valid course enrollment. Enrolled users hold distinct course-scoped roles (Student, TA, Professor), and role authority in one course does not confer privileges in other courses."),
            ],
            "CSE302": [
                ("quizzes", "Assessment Quota & Timed Attempts", "Quiz attempts cannot exceed the maximum permitted quota (1 to 3 attempts) and must be initiated strictly within the published availability window."),
                ("quizzes", "Answer Key Release Schedule", "Official solution answer keys and diagnostic rubrics remain locked until the designated release date. Prior to release, answer keys are confidential to course staff."),
                ("resources", "Staff-Only Educational Resources", "Learning resources marked as Staff Only (including grading criteria, lab solution implementations, and exam keys) are restricted to faculty and assigned teaching assistants."),
                ("quizzes", "Assessment Availability Windows", "Timed quizzes are accessible only between the scheduled open and close dates. Attempts cannot be started before the opening time or after the closing time."),
            ],
            "CSE303": [
                ("deadlines", "Submission Deadlines & Extension Rules", "Submissions received after the published deadline are locked and rejected unless an official academic extension has been recorded."),
                ("grading", "Assessment Locking & Finalization", "Once grades for a submission are locked by course faculty, neither students nor teaching assistants can modify the submission or its recorded marks without administrator intervention."),
                ("deadlines", "Individual Academic Extension Policy", "Students with an approved extension flag recorded in the system are granted authorization to submit or edit coursework past the standard course deadline."),
                ("resources", "Staff-Only Educational Resources", "Learning resources marked as Staff Only (including grading criteria, lab solution implementations, and exam keys) are restricted to faculty and assigned teaching assistants."),
            ],
            "HCI401": [
                ("submissions", "Collaborative Group Submission Privacy", "For team-based assignments, submission drafts, files, and instructor evaluation feedback are strictly confidential to members of that specific group and course instructors. Access by students in other groups is prohibited."),
                ("grading", "Final Grade Publication & Locking", "Only the assigned course professor or institutional administrators can publish and lock final grades. TAs can enter and modify marks during the active grading window but cannot publish final grades."),
                ("deadlines", "Submission Deadlines & Extension Rules", "Submissions received after the published deadline are locked and rejected unless an official academic extension has been recorded."),
                ("institutional", "Course Membership & Role Authority", "Course access, participation, and submission privileges require valid course enrollment. Enrolled users hold distinct course-scoped roles (Student, TA, Professor), and role authority in one course does not confer privileges in other courses."),
            ],
        }

        for code, pol_list in course_policies.items():
            course = courses_by_code[code]
            for ptype, ptitle, pcontent in pol_list:
                pol = db.scalar(select(CoursePolicy).where(CoursePolicy.course_id == course.id, CoursePolicy.title == ptitle))
                if not pol:
                    pol = CoursePolicy(
                        course_id=course.id,
                        policy_type=ptype,
                        title=ptitle,
                        content=pcontent,
                    )
                    db.add(pol)
                else:
                    pol.policy_type = ptype
                    pol.content = pcontent

        db.flush()

        # =========================================================================
        # 7. SEED ASSIGNMENTS (13 total: 4 in 301, 3 in 302, 3 in 303, 3 in 401)
        # =========================================================================
        c301 = courses_by_code["CSE301"]
        c302 = courses_by_code["CSE302"]
        c303 = courses_by_code["CSE303"]
        c401 = courses_by_code["HCI401"]

        assignments_def = [
            # CSE301
            (c301.id, "Relational Schema Design & SQL Queries", "Design 3NF schemas and write analytical SQL queries.", "Submit your SQL schema scripts and query results.", "2026-01-01T23:59:59Z", 100, False, False, True),
            (c301.id, "B-Tree Indexing Implementation", "Implement a memory-backed B+ tree index structure in Python/C++.", "Implement insert, search, and leaf splitting operations.", "2026-12-31T23:59:59Z", 100, False, False, True),
            (c301.id, "Query Execution Plan Optimization", "Analyze EXPLAIN ANALYZE traces and build optimal multi-table join indexes.", "Upload the optimized execution plan comparison report.", "2026-12-18T23:59:59Z", 100, False, False, True),
            (c301.id, "Database Normalization & Transaction Recovery", "Decompose schemas to BCNF and implement write-ahead logging (WAL) simulation.", "Submit relational decomposition proof and crash recovery logic.", "2026-02-15T23:59:59Z", 100, False, True, True),

            # CSE302
            (c302.id, "Packet Sniffing and Protocol Analysis", "Analyze Wireshark PCAP traces of TCP 3-way handshakes and TLS 1.3 session setup.", "Provide packet dissection charts and analysis text.", "2026-12-15T23:59:59Z", 100, False, False, True),
            (c302.id, "Socket Programming: Multi-threaded HTTP Server", "Implement a non-blocking POSIX socket server handling concurrent HTTP/1.1 requests.", "Submit clean C/Python source code and concurrency benchmark logs.", "2026-03-01T23:59:59Z", 100, False, False, True),
            (c302.id, "Routing Algorithm Simulation (Dijkstra & DV)", "Simulate link-state and distance-vector convergence under arbitrary link failure topologies.", "Upload routing table state dumps and convergence time graphs.", "2026-12-22T23:59:59Z", 100, False, False, True),

            # CSE303
            (c303.id, "Kernel Process Scheduler Simulation", "Implement Multi-Level Feedback Queue (MLFQ) and Completely Fair Scheduler (CFS) models.", "Submit scheduling simulator code and turnaround time comparative analysis.", "2026-02-28T23:59:59Z", 100, False, False, True),
            (c303.id, "Virtual Memory & Paging Allocator", "Simulate two-level hierarchical page tables with TLB caching and LRU page replacement.", "Submit paging allocator C implementation and page fault trace reports.", "2026-12-20T23:59:59Z", 100, False, False, True),
            (c303.id, "Concurrency & Synchronization Primitives", "Implement dining philosophers and reader-writer problems using semaphores and condition variables.", "Submit race-condition-free C code and verification stress test logs.", "2026-12-28T23:59:59Z", 100, False, False, True),

            # HCI401
            (c401.id, "Group Project: Interactive Prototype", "Design and test a high-fidelity interactive prototype in small student teams.", "Submit your team's Figma link and usability test findings report.", "2026-12-24T23:59:59Z", 100, True, False, True),
            (c401.id, "Heuristic Usability Evaluation Report", "Conduct cognitive walkthroughs and Nielsen heuristic evaluations of an existing public portal.", "Submit individual heuristic evaluation audit table and severity ratings.", "2026-03-10T23:59:59Z", 100, False, False, True),
            (c401.id, "Accessibility Audit & WCAG 2.1 Compliance Lab", "Audit a real-world web application against WCAG 2.1 Level AA accessibility criteria.", "Provide screen reader inspection logs and color contrast remediation reports.", "2026-12-19T23:59:59Z", 100, False, False, True),
        ]

        assignments_by_title = {}
        for cid, title, desc, inst, due, max_g, is_grp, allow_l, is_pub in assignments_def:
            assign = db.scalar(select(Assignment).where(Assignment.course_id == cid, Assignment.title == title))
            if not assign:
                assign = Assignment(
                    course_id=cid,
                    title=title,
                    description=desc,
                    instructions=inst,
                    due_date=due,
                    max_grade=max_g,
                    is_group=is_grp,
                    allow_late=allow_l,
                    is_published=is_pub,
                )
                db.add(assign)
                db.flush()
            else:
                assign.description = desc
                assign.instructions = inst
                assign.due_date = due
                assign.max_grade = max_g
                assign.is_group = is_grp
                assign.allow_late = allow_l
                assign.is_published = is_pub
            assignments_by_title[title] = assign

        db.flush()

        # =========================================================================
        # 8. SEED SUBMISSIONS (38 total covering all 10 distinct submission states)
        # =========================================================================
        prof01 = users_by_username["prof01"]
        prof02 = users_by_username["prof02"]
        ta01 = users_by_username["ta01"]
        ta02 = users_by_username["ta02"]
        ta03 = users_by_username["ta03"]
        ta04 = users_by_username["ta04"]

        # Define 38 targeted submissions:
        # (assignment_title, student_username, group_name_or_none, content, status, is_draft, is_published, is_locked, ext_granted, grade, feedback, grader_user_or_none, submitted_at)
        submissions_def = [
            # --- CSE301: Relational Schema Design & SQL Queries (Past due: 2026-01-01) ---
            # 1. Asha (student01): Graded 88, published, locked, past deadline [Baseline TC01]
            ("Relational Schema Design & SQL Queries", "student01", None,
             "-- CSE301 Project 1\nCREATE TABLE students (...);", "graded", False, True, True, False, 88,
             "Good 3NF normalization. Query #4 needs optimization.", prof01, datetime(2025, 12, 28, 14, 0, tzinfo=timezone.utc)),
            # 2. Rohan (student02): Graded 82, published, unlocked, past deadline, no extension [Baseline TC05, TC10]
            ("Relational Schema Design & SQL Queries", "student02", None,
             "-- Rohan's Submission\nCREATE TABLE courses (...);", "graded", False, True, False, False, 82,
             "Clean schema. Minor syntax errors in subqueries.", prof01, datetime(2025, 12, 29, 10, 0, tzinfo=timezone.utc)),
            # 3. Isha (student03): Graded 90, published, locked, past deadline
            ("Relational Schema Design & SQL Queries", "student03", None,
             "-- Isha Roy SQL Solutions\nCREATE TABLE enrollments (...);", "graded", False, True, True, False, 90,
             "Exemplary normalization and indexing design.", prof01, datetime(2025, 12, 30, 16, 30, tzinfo=timezone.utc)),
            # 4. Arjun (student06): Graded 76, UNPUBLISHED, unlocked, past deadline (graded by TA ta01)
            ("Relational Schema Design & SQL Queries", "student06", None,
             "-- Arjun Nair Project 1\nCREATE TABLE grades (...);", "graded", False, False, False, False, 76,
             "Adequate schema. Foreign key cascade constraints omitted.", ta01, datetime(2025, 12, 31, 18, 0, tzinfo=timezone.utc)),
            # 5. David Kim (student12): Submitted unrated, unlocked, past deadline WITH APPROVED EXTENSION
            ("Relational Schema Design & SQL Queries", "student12", None,
             "-- David Kim Late Schema Model\nCREATE TABLE lab_results (...);", "submitted", False, True, False, True, None,
             None, None, datetime(2026, 1, 3, 11, 0, tzinfo=timezone.utc)),

            # --- CSE301: B-Tree Indexing Implementation (Active due: 2026-12-31) ---
            # 6. Rohan (student02): DRAFT before deadline [Baseline TC09]
            ("B-Tree Indexing Implementation", "student02", None,
             "Draft B-Tree pseudo-code: class BTreeNode { ... }", "draft", True, False, False, False, None,
             None, None, datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)),
            # 7. Asha (student01): Submitted unrated, active future deadline
            ("B-Tree Indexing Implementation", "student01", None,
             "class BPlusTree:\n    def __init__(self, degree=4):\n        self.root = Node()", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)),
            # 8. Priya Sharma (student07): Graded 85, published, unlocked, graded by TA ta01
            ("B-Tree Indexing Implementation", "student07", None,
             "class BPlusTreeIndex:\n    # Node splitting implementation\n    pass", "graded", False, True, False, False, 85,
             "Correct node splitting and height balancing.", ta01, datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)),

            # --- CSE301: Query Execution Plan Optimization (Active due: 2026-12-18) ---
            # 9. Marcus Chen (student08): DRAFT not submitted
            ("Query Execution Plan Optimization", "student08", None,
             "Draft plan analysis: Nested loop join vs hash join benchmarks...", "draft", True, False, False, False, None,
             None, None, datetime(2026, 11, 4, 16, 0, tzinfo=timezone.utc)),
            # 10. Lucas Silva (student10): Submitted unrated
            ("Query Execution Plan Optimization", "student10", None,
             "EXPLAIN ANALYZE SELECT * FROM orders JOIN customers ON orders.cust_id = customers.id;", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 5, 8, 30, tzinfo=timezone.utc)),

            # --- CSE301: Database Normalization & Transaction Recovery (Past due: 2026-02-15) ---
            # 11. Priya Sharma (student07): Graded 84, published, unlocked, graded by TA ta01
            ("Database Normalization & Transaction Recovery", "student07", None,
             "BCNF decomposition algorithm step-by-step proofs and WAL logging replay logic.", "graded", False, True, False, False, 84,
             "Sound proof of lossless join property.", ta01, datetime(2026, 2, 14, 20, 0, tzinfo=timezone.utc)),
            # 12. Lucas Silva (student10): Submitted unrated, past due, no extension
            ("Database Normalization & Transaction Recovery", "student10", None,
             "Transaction recovery simulation with checkpointing log parser.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 2, 15, 23, 0, tzinfo=timezone.utc)),
            # 13. Ananya Iyer (student13): Graded 78, published, locked, graded by prof01
            ("Database Normalization & Transaction Recovery", "student13", None,
             "Dependency preservation analysis under 3NF and BCNF.", "graded", False, True, True, False, 78,
             "Minor oversight in functional dependency closure computation.", prof01, datetime(2026, 2, 13, 15, 0, tzinfo=timezone.utc)),

            # --- CSE302: Packet Sniffing and Protocol Analysis (Active due: 2026-12-15) ---
            # 14. Asha (student01): Submitted unrated, active future deadline
            ("Packet Sniffing and Protocol Analysis", "student01", None,
             "Wireshark packet dissection report for TLS 1.3 handshake exchange.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)),
            # 15. Rohan (student02): Graded 91, UNPUBLISHED, unlocked, graded by TA ta02
            ("Packet Sniffing and Protocol Analysis", "student02", None,
             "TCP sliding window analysis and selective acknowledgment (SACK) behavior trace.", "graded", False, False, False, False, 91,
             "Thorough window size scaling graph breakdown.", ta02, datetime(2026, 11, 2, 17, 0, tzinfo=timezone.utc)),
            # 16. Vikram Sen (student04): Submitted unrated, active future deadline
            ("Packet Sniffing and Protocol Analysis", "student04", None,
             "ARP cache poisoning analysis and mitigation verification pcap.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 4, 11, 0, tzinfo=timezone.utc)),

            # --- CSE302: Socket Programming: Multi-threaded HTTP Server (Past due: 2026-03-01) ---
            # 17. Vikram Sen (student04): Graded 88, published, locked, graded by prof02
            ("Socket Programming: Multi-threaded HTTP Server", "student04", None,
             "Thread-pool based HTTP/1.1 web server in POSIX C with epoll event loop.", "graded", False, True, True, False, 88,
             "Robust HTTP parsing and connection keep-alive handling.", prof02, datetime(2026, 2, 27, 19, 0, tzinfo=timezone.utc)),
            # 18. Arjun (student06): Graded 79, published, unlocked, graded by TA ta02
            ("Socket Programming: Multi-threaded HTTP Server", "student06", None,
             "Multi-threaded socket server using pthreads and mutual exclusion locks.", "graded", False, True, False, False, 79,
             "Static file serving works; concurrent stress test shows slight thread starvation.", ta02, datetime(2026, 2, 28, 22, 0, tzinfo=timezone.utc)),
            # 19. David Kim (student12): Submitted unrated, past due WITH APPROVED EXTENSION
            ("Socket Programming: Multi-threaded HTTP Server", "student12", None,
             "Non-blocking I/O multiplexer server implementation.", "submitted", False, True, False, True, None,
             None, None, datetime(2026, 3, 4, 14, 0, tzinfo=timezone.utc)),

            # --- CSE302: Routing Algorithm Simulation (Active due: 2026-12-22) ---
            # 20. Marcus Chen (student08): Submitted unrated, active future deadline
            ("Routing Algorithm Simulation (Dijkstra & DV)", "student08", None,
             "Dijkstra shortest path vs Bellman-Ford count-to-infinity simulation scripts.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)),
            # 21. Chloe Bennett (student11): DRAFT before deadline
            ("Routing Algorithm Simulation (Dijkstra & DV)", "student11", None,
             "Draft simulation topologies: class NetworkNode: ...", "draft", True, False, False, False, None,
             None, None, datetime(2026, 11, 4, 20, 0, tzinfo=timezone.utc)),

            # --- CSE303: Kernel Process Scheduler Simulation (Past due: 2026-02-28) ---
            # 22. Asha (student01): Graded 85, UNPUBLISHED, unlocked, graded by TA ta03
            ("Kernel Process Scheduler Simulation", "student01", None,
             "Multi-level feedback queue simulation with priority boosting and time slice decay.", "graded", False, False, False, False, 85,
             "Accurate turnaround time tracking across 5 priority queues.", ta03, datetime(2026, 2, 26, 18, 0, tzinfo=timezone.utc)),
            # 23. Tara Bose (student05): Graded 92, published, locked, graded by prof01
            ("Kernel Process Scheduler Simulation", "student05", None,
             "Completely Fair Scheduler (CFS) red-black tree simulation with vruntime tracking.", "graded", False, True, True, False, 92,
             "Flawless red-black tree balancing and virtual runtime calculations.", prof01, datetime(2026, 2, 27, 14, 0, tzinfo=timezone.utc)),
            # 24. Marcus Chen (student08): Submitted unrated, past due, no extension
            ("Kernel Process Scheduler Simulation", "student08", None,
             "Round Robin and Shortest Remaining Time First comparative scheduler.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 2, 28, 23, 30, tzinfo=timezone.utc)),
            # 25. Chloe Bennett (student11): Submitted unrated, past due WITH APPROVED EXTENSION
            ("Kernel Process Scheduler Simulation", "student11", None,
             "Dynamic priority aging scheduler simulator.", "submitted", False, True, False, True, None,
             None, None, datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc)),
            # 26. Kevin Zhao (student16): Graded 70, published, unlocked, graded by TA ta04
            ("Kernel Process Scheduler Simulation", "student16", None,
             "Lottery scheduling simulation with ticket distribution.", "graded", False, True, False, False, 70,
             "Pseudo-random generator seed issue caused non-uniform distribution.", ta04, datetime(2026, 2, 28, 21, 0, tzinfo=timezone.utc)),

            # --- CSE303: Virtual Memory & Paging Allocator (Active due: 2026-12-20) ---
            # 27. Vikram Sen (student04): Submitted unrated, active future deadline
            ("Virtual Memory & Paging Allocator", "student04", None,
             "Two-level page table walk simulation with 4KB page frames and TLB hit accounting.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc)),
            # 28. Lucas Silva (student10): DRAFT before deadline
            ("Virtual Memory & Paging Allocator", "student10", None,
             "Draft page table allocator: typedef struct { uint32_t pte[1024]; } PageTable;", "draft", True, False, False, False, None,
             None, None, datetime(2026, 11, 5, 11, 0, tzinfo=timezone.utc)),
            # 29. Omar Farooq (student14): Submitted unrated, active future deadline
            ("Virtual Memory & Paging Allocator", "student14", None,
             "Clock page replacement algorithm and dirty-bit writeback simulator.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)),

            # --- CSE303: Concurrency & Synchronization Primitives (Active due: 2026-12-28) ---
            # 30. Arjun (student06): Submitted unrated, active future deadline
            ("Concurrency & Synchronization Primitives", "student06", None,
             "Dining Philosophers asymmetric solution and reader-writer fair queue.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 3, 13, 0, tzinfo=timezone.utc)),
            # 31. Ananya Iyer (student13): Submitted unrated, active future deadline
            ("Concurrency & Synchronization Primitives", "student13", None,
             "Bounded-buffer producer-consumer monitor implementation in C.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)),

            # --- HCI401: Group Project: Interactive Prototype (Active due: 2026-12-24, is_group=True) ---
            # 32. Team Alpha (submitted by student01): Submitted unrated, unlocked [Baseline TC19]
            ("Group Project: Interactive Prototype", "student01", "Design Team Alpha",
             "Team Alpha Interactive Prototype: Figma prototype URL and usability report for mobile transit app.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)),
            # 33. Team Beta (submitted by student05): Submitted unrated, unlocked [Baseline TC19]
            ("Group Project: Interactive Prototype", "student05", "Design Team Beta",
             "Team Beta Healthcare Patient Portal: Confidential research submission and interview logs.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc)),
            # 34. Team Gamma (submitted by student07): Submitted unrated, unlocked
            ("Group Project: Interactive Prototype", "student07", "Design Team Gamma",
             "Team Gamma Campus Sustainable Dining App: Interactive wireframes and heuristic logs.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)),
            # 35. Team Delta (submitted by student09): Submitted unrated, unlocked
            ("Group Project: Interactive Prototype", "student09", "Design Team Delta",
             "Team Delta Universal Library Kiosk System: Voice navigation UI and cognitive walkthrough.", "submitted", False, True, False, False, None,
             None, None, datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)),

            # --- HCI401: Heuristic Usability Evaluation Report (Past due: 2026-03-10) ---
            # 36. Asha (student01): Graded 89, published, locked, graded by prof02
            ("Heuristic Usability Evaluation Report", "student01", None,
             "Comprehensive heuristic evaluation of municipal transit ticketing portal.", "graded", False, True, True, False, 89,
             "Insightful analysis of consistency and error prevention heuristics.", prof02, datetime(2026, 3, 8, 14, 0, tzinfo=timezone.utc)),
            # 37. Tara Bose (student05): Graded 94, UNPUBLISHED, unlocked, graded by prof02
            ("Heuristic Usability Evaluation Report", "student05", None,
             "Usability evaluation of hospital patient check-in touchscreen terminal.", "graded", False, False, False, False, 94,
             "Superb heuristic evaluation report with actionable design recommendations.", prof02, datetime(2026, 3, 9, 16, 0, tzinfo=timezone.utc)),
            # 38. Arjun (student06): Graded 95, published, locked, graded by prof02
            ("Heuristic Usability Evaluation Report", "student06", None,
             "Heuristic analysis of digital banking mobile application workflow.", "graded", False, True, True, False, 95,
             "Flawless evaluation with severity ratings and annotated UI captures.", prof02, datetime(2026, 3, 10, 19, 0, tzinfo=timezone.utc)),
        ]

        submissions_by_key = {}
        for (atitle, suname, gname, content, status, is_draft, is_pub, is_lock, ext, grade, feedback, grader, sub_time) in submissions_def:
            assign = assignments_by_title[atitle]
            student = users_by_username[suname]
            grp_id = groups_by_name[gname].id if gname else None

            sub = db.scalar(select(Submission).where(Submission.assignment_id == assign.id, Submission.student_id == student.id))
            if not sub:
                sub = Submission(
                    assignment_id=assign.id,
                    student_id=student.id,
                    group_id=grp_id,
                    content=content,
                    status=status,
                    is_draft=is_draft,
                    is_published=is_pub,
                    is_locked=is_lock,
                    extension_granted=ext,
                    grade=grade,
                    feedback=feedback,
                    graded_by_id=grader.id if grader else None,
                    graded_at=datetime.now(timezone.utc) if grade is not None else None,
                    submitted_at=sub_time,
                )
                db.add(sub)
                db.flush()
            else:
                sub.group_id = grp_id
                sub.content = content
                sub.status = status
                sub.is_draft = is_draft
                sub.is_published = is_pub
                sub.is_locked = is_lock
                sub.extension_granted = ext
                sub.grade = grade
                sub.feedback = feedback
                sub.graded_by_id = grader.id if grader else None
                if grade is not None and not sub.graded_at:
                    sub.graded_at = datetime.now(timezone.utc)
                sub.submitted_at = sub_time
            submissions_by_key[(assign.id, student.id)] = sub

        db.flush()

        # =========================================================================
        # 9. SEED GRADE HISTORIES (6 Audited Grade Adjustment Entries)
        # =========================================================================
        grade_histories_data = [
            ("Relational Schema Design & SQL Queries", "student02", c301.id, 80, 82, ta01, "Regraded query #3 after student clarification on indexing assumption."),
            ("Relational Schema Design & SQL Queries", "student01", c301.id, 85, 88, prof01, "Corrected normalization criteria points based on master rubric."),
            ("Socket Programming: Multi-threaded HTTP Server", "student06", c302.id, 75, 79, ta02, "Added partial credit for valid non-blocking poll loop implementation."),
            ("Socket Programming: Multi-threaded HTTP Server", "student04", c302.id, 85, 88, prof02, "Adjusted mark for innovative thread pool task queue architecture."),
            ("Kernel Process Scheduler Simulation", "student01", c303.id, 82, 85, ta03, "Re-evaluated MLFQ queue priority decay calculations."),
            ("Kernel Process Scheduler Simulation", "student16", c303.id, 68, 70, ta04, "Granted partial credit for ticket reallocation corner case logic."),
        ]

        for atitle, suname, cid, prev_g, new_g, changer, reason in grade_histories_data:
            assign = assignments_by_title[atitle]
            student = users_by_username[suname]
            sub = submissions_by_key[(assign.id, student.id)]

            gh = db.scalar(select(GradeHistory).where(
                GradeHistory.submission_id == sub.id,
                GradeHistory.changed_by_id == changer.id,
                GradeHistory.new_grade == new_g
            ))
            if not gh:
                gh = GradeHistory(
                    submission_id=sub.id,
                    course_id=cid,
                    student_id=student.id,
                    previous_grade=prev_g,
                    new_grade=new_g,
                    changed_by_id=changer.id,
                    changed_at=datetime.now(timezone.utc),
                    reason=reason,
                )
                db.add(gh)

        db.flush()

        # =========================================================================
        # 10. SEED QUIZZES (12 Quizzes total: 3 per course)
        # =========================================================================
        quizzes_def = [
            # --- CSE301 (DBMS) ---
            # 1. CSE301 Knowledge Assessment (Open & Active, release in future, max 2)
            (c301.id, "CSE301 Knowledge Assessment", "Core concepts assessment for Database Management Systems.",
             "2026-10-01T00:00:00Z", "2026-12-31T23:59:59Z", "2026-12-31T23:59:59Z", 30, 2, True,
             "What is the primary objective of study in CSE301?", ["Academic Mastery", "Trial & Error", "Passive Observation", "None"], "Academic Mastery"),
            # 2. SQL Indexing & Transaction Isolation Quiz (EXPIRED / CLOSED, Answer Key RELEASED, max 1)
            (c301.id, "SQL Indexing & Transaction Isolation Quiz", "Timed diagnostic evaluating B+ tree indexing and ACID isolation levels.",
             "2026-09-01T00:00:00Z", "2026-10-01T23:59:59Z", "2026-10-05T00:00:00Z", 25, 1, True,
             "Which ACID property is primarily preserved by write-ahead logging (WAL)?", ["Atomicity", "Durability", "Isolation", "Consistency"], "Durability"),
            # 3. Relational Algebra Midterm Prep (UPCOMING / NOT YET OPEN, release in future, max 2)
            (c301.id, "Relational Algebra Midterm Prep", "Preparatory diagnostic covering relational division, theta-joins, and query equivalence.",
             "2026-12-10T09:00:00Z", "2026-12-12T17:00:00Z", "2026-12-20T23:59:59Z", 40, 2, True,
             "Which relational algebra operator corresponds to the SQL SELECT DISTINCT clause projection?", ["Select (sigma)", "Project (pi)", "Join (bowtie)", "Union"], "Project (pi)"),

            # --- CSE302 (Computer Networks) ---
            # 4. Midterm Online Assessment (UPCOMING / NOT YET OPEN, max 1) [Baseline TC12]
            (c302.id, "Midterm Online Assessment", "Timed midterm evaluation covering OSI layers 1 through 4.",
             "2026-12-15T09:00:00Z", "2026-12-15T12:00:00Z", "2026-12-20T23:59:59Z", 60, 1, True,
             "Which layer of the OSI model manages end-to-end flow control and reliable transmission?", ["Transport", "Network", "Data Link", "Session"], "Transport"),
            # 5. Networking Protocols Practice Quiz (OPEN & ACTIVE, max 3) [Baseline TC13]
            (c302.id, "Networking Protocols Practice Quiz", "Multiple choice questions testing knowledge of DNS, DHCP, and ARP.",
             "2026-10-01T00:00:00Z", "2026-12-31T23:59:59Z", "2026-12-31T23:59:59Z", 20, 3, True,
             "Which transport protocol provides connection-oriented, reliable byte stream delivery?", ["UDP", "TCP", "ICMP", "IP"], "TCP"),
            # 6. Subnetting and Routing Quiz (OPEN & ACTIVE, Answer Key LOCKED, max 2) [Baseline TC14]
            (c302.id, "Subnetting and Routing Quiz", "CIDR prefix calculation and longest prefix match exercises.",
             "2026-10-01T00:00:00Z", "2026-12-31T23:59:59Z", "2026-12-31T23:59:59Z", 30, 2, True,
             "How many usable host IP addresses are in a /28 IPv4 subnet?", ["14", "16", "30", "32"], "14"),

            # --- CSE303 (Operating Systems) ---
            # 7. CSE303 Knowledge Assessment (OPEN & ACTIVE, release in future, max 2)
            (c303.id, "CSE303 Knowledge Assessment", "Core concepts assessment for Operating Systems.",
             "2026-10-01T00:00:00Z", "2026-12-31T23:59:59Z", "2026-12-31T23:59:59Z", 30, 2, True,
             "What is the primary objective of study in CSE303?", ["Academic Mastery", "Trial & Error", "Passive Observation", "None"], "Academic Mastery"),
            # 8. CPU Scheduling & Memory Management Quiz (OPEN & ACTIVE, Answer Key RELEASED, max 2)
            (c303.id, "CPU Scheduling & Memory Management Quiz", "Evaluation on virtual memory translation, page replacement algorithms, and scheduling metrics.",
             "2026-10-01T00:00:00Z", "2026-12-31T23:59:59Z", "2026-10-15T00:00:00Z", 35, 2, True,
             "Which page replacement algorithm suffers from Belady's Anomaly?", ["FIFO", "LRU", "Optimal", "Clock"], "FIFO"),
            # 9. Concurrency & Deadlocks Timed Assessment (EXPIRED / CLOSED, Answer Key RELEASED, max 1)
            (c303.id, "Concurrency & Deadlocks Timed Assessment", "Diagnostic on Coffman deadlock conditions and semaphore invariants.",
             "2026-09-15T00:00:00Z", "2026-10-15T23:59:59Z", "2026-10-20T00:00:00Z", 25, 1, True,
             "Which of the following is NOT one of the four necessary Coffman deadlock conditions?", ["Mutual Exclusion", "Preemption Allowed", "Hold and Wait", "Circular Wait"], "Preemption Allowed"),

            # --- HCI401 (Human-Computer Interaction) ---
            # 10. HCI401 Knowledge Assessment (OPEN & ACTIVE, release in future, max 2)
            (c401.id, "HCI401 Knowledge Assessment", "Core concepts assessment for Human-Computer Interaction.",
             "2026-10-01T00:00:00Z", "2026-12-31T23:59:59Z", "2026-12-31T23:59:59Z", 30, 2, True,
             "What is the primary objective of study in HCI401?", ["Academic Mastery", "Trial & Error", "Passive Observation", "None"], "Academic Mastery"),
            # 11. Usability Engineering & Cognitive Heuristics Quiz (OPEN & ACTIVE, Answer Key LOCKED, max 1)
            (c401.id, "Usability Engineering & Cognitive Heuristics Quiz", "Assessment on Norman's design principles, Fitts's Law, and heuristic evaluation.",
             "2026-10-01T00:00:00Z", "2026-12-31T23:59:59Z", "2026-12-31T23:59:59Z", 20, 1, True,
             "According to Fitts's Law, movement time to a target is a function of target distance and target:", ["Width", "Color", "Contrast", "Elevation"], "Width"),
            # 12. Accessibility & Universal Design Mini-Quiz (UPCOMING / NOT YET OPEN, release in future, max 2)
            (c401.id, "Accessibility & Universal Design Mini-Quiz", "Diagnostic on WCAG 2.1 POUR principles and assistive screen reader navigation.",
             "2026-12-01T09:00:00Z", "2026-12-05T17:00:00Z", "2026-12-10T23:59:59Z", 25, 2, True,
             "What does the letter 'P' represent in the WCAG POUR accessibility foundation?", ["Perceivable", "Predictable", "Performant", "Precise"], "Perceivable"),
        ]

        quizzes_by_title = {}
        for cid, title, desc, op, cl, rel, tlim, max_att, is_pub, qtext, qopts, qans in quizzes_def:
            quiz = db.scalar(select(Quiz).where(Quiz.course_id == cid, Quiz.title == title))
            if not quiz:
                quiz = Quiz(
                    course_id=cid,
                    title=title,
                    description=desc,
                    open_date=op,
                    close_date=cl,
                    answer_release_date=rel,
                    time_limit_minutes=tlim,
                    max_attempts=max_att,
                    is_published=is_pub,
                )
                db.add(quiz)
                db.flush()
            else:
                quiz.description = desc
                quiz.open_date = op
                quiz.close_date = cl
                quiz.answer_release_date = rel
                quiz.time_limit_minutes = tlim
                quiz.max_attempts = max_att
                quiz.is_published = is_pub

            quizzes_by_title[title] = quiz

            # Add question
            qq = db.scalar(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id, QuizQuestion.question_text == qtext))
            if not qq:
                qq = QuizQuestion(
                    quiz_id=quiz.id,
                    question_text=qtext,
                    question_type="multiple_choice",
                    options_json=json.dumps(qopts),
                    correct_answer=qans,
                    points=10,
                )
                db.add(qq)

        db.flush()

        # =========================================================================
        # 11. SEED QUIZ ATTEMPTS (22 attempts total)
        # =========================================================================
        # (quiz_title, student_username, attempt_number, score_or_none, status, started_at, completed_at)
        attempts_def = [
            # --- Quiz 2: SQL Indexing & Transaction Isolation Quiz (max 1, closed) ---
            # Quota exhausted attempts:
            ("SQL Indexing & Transaction Isolation Quiz", "student01", 1, 90, "finished", datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc), datetime(2026, 9, 15, 10, 22, tzinfo=timezone.utc)),
            ("SQL Indexing & Transaction Isolation Quiz", "student02", 1, 80, "finished", datetime(2026, 9, 16, 14, 0, tzinfo=timezone.utc), datetime(2026, 9, 16, 14, 20, tzinfo=timezone.utc)),
            ("SQL Indexing & Transaction Isolation Quiz", "student03", 1, 100, "finished", datetime(2026, 9, 17, 11, 0, tzinfo=timezone.utc), datetime(2026, 9, 17, 11, 24, tzinfo=timezone.utc)),
            ("SQL Indexing & Transaction Isolation Quiz", "student06", 1, 70, "finished", datetime(2026, 9, 18, 16, 0, tzinfo=timezone.utc), datetime(2026, 9, 18, 16, 25, tzinfo=timezone.utc)),

            # --- Quiz 5: Networking Protocols Practice Quiz (max 3, open) ---
            # NOTE: student01 has 0 attempts here so Scenario 13 can start attempt #1!
            # student02 has used 2/3 attempts (1 attempt remaining):
            ("Networking Protocols Practice Quiz", "student02", 1, 70, "finished", datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc), datetime(2026, 10, 10, 11, 15, tzinfo=timezone.utc)),
            ("Networking Protocols Practice Quiz", "student02", 2, 90, "finished", datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc), datetime(2026, 10, 12, 15, 18, tzinfo=timezone.utc)),
            # student04 has used 3/3 attempts (exhausted quota):
            ("Networking Protocols Practice Quiz", "student04", 1, 60, "finished", datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc), datetime(2026, 10, 5, 9, 19, tzinfo=timezone.utc)),
            ("Networking Protocols Practice Quiz", "student04", 2, 80, "finished", datetime(2026, 10, 8, 14, 0, tzinfo=timezone.utc), datetime(2026, 10, 8, 14, 18, tzinfo=timezone.utc)),
            ("Networking Protocols Practice Quiz", "student04", 3, 90, "finished", datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc), datetime(2026, 10, 15, 16, 17, tzinfo=timezone.utc)),
            # student06 has an in-progress attempt:
            ("Networking Protocols Practice Quiz", "student06", 1, None, "in_progress", datetime.now(timezone.utc), None),

            # --- Quiz 6: Subnetting and Routing Quiz (max 2, open) ---
            # student02 has used 1/2 attempts (1 attempt remaining):
            ("Subnetting and Routing Quiz", "student02", 1, 80, "finished", datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc), datetime(2026, 10, 20, 10, 28, tzinfo=timezone.utc)),
            # student06 has used 2/2 attempts (exhausted quota):
            ("Subnetting and Routing Quiz", "student06", 1, 60, "finished", datetime(2026, 10, 21, 14, 0, tzinfo=timezone.utc), datetime(2026, 10, 21, 14, 25, tzinfo=timezone.utc)),
            ("Subnetting and Routing Quiz", "student06", 2, 80, "finished", datetime(2026, 10, 25, 17, 0, tzinfo=timezone.utc), datetime(2026, 10, 25, 17, 28, tzinfo=timezone.utc)),
            # student08 has used 1/2 attempts:
            ("Subnetting and Routing Quiz", "student08", 1, 90, "finished", datetime(2026, 10, 28, 13, 0, tzinfo=timezone.utc), datetime(2026, 10, 28, 13, 22, tzinfo=timezone.utc)),

            # --- Quiz 7: CSE303 Knowledge Assessment (max 2, open) ---
            ("CSE303 Knowledge Assessment", "student01", 1, 100, "finished", datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc), datetime(2026, 10, 15, 10, 25, tzinfo=timezone.utc)),
            ("CSE303 Knowledge Assessment", "student04", 1, 80, "finished", datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc), datetime(2026, 10, 16, 12, 28, tzinfo=timezone.utc)),
            ("CSE303 Knowledge Assessment", "student05", 1, 90, "finished", datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc), datetime(2026, 10, 17, 15, 26, tzinfo=timezone.utc)),
            # student16 has an in-progress attempt:
            ("CSE303 Knowledge Assessment", "student16", 1, None, "in_progress", datetime.now(timezone.utc), None),

            # --- Quiz 9: Concurrency & Deadlocks Timed Assessment (max 1, closed) ---
            ("Concurrency & Deadlocks Timed Assessment", "student01", 1, 90, "finished", datetime(2026, 9, 28, 11, 0, tzinfo=timezone.utc), datetime(2026, 9, 28, 11, 23, tzinfo=timezone.utc)),
            ("Concurrency & Deadlocks Timed Assessment", "student05", 1, 80, "finished", datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc), datetime(2026, 9, 29, 14, 22, tzinfo=timezone.utc)),

            # --- Quiz 11: Usability Engineering & Cognitive Heuristics Quiz (max 1, open) ---
            ("Usability Engineering & Cognitive Heuristics Quiz", "student03", 1, 90, "finished", datetime(2026, 10, 18, 9, 0, tzinfo=timezone.utc), datetime(2026, 10, 18, 9, 18, tzinfo=timezone.utc)),
            ("Usability Engineering & Cognitive Heuristics Quiz", "student05", 1, 100, "finished", datetime(2026, 10, 19, 14, 0, tzinfo=timezone.utc), datetime(2026, 10, 19, 14, 19, tzinfo=timezone.utc)),
        ]

        for qtitle, suname, att_num, score, astatus, start_t, comp_t in attempts_def:
            quiz = quizzes_by_title[qtitle]
            student = users_by_username[suname]

            att = db.scalar(select(QuizAttempt).where(
                QuizAttempt.quiz_id == quiz.id,
                QuizAttempt.student_id == student.id,
                QuizAttempt.attempt_number == att_num,
            ))
            if not att:
                att = QuizAttempt(
                    quiz_id=quiz.id,
                    student_id=student.id,
                    attempt_number=att_num,
                    started_at=start_t,
                    completed_at=comp_t,
                    score=score,
                    status=astatus,
                )
                db.add(att)
            else:
                att.score = score
                att.status = astatus
                att.started_at = start_t
                att.completed_at = comp_t

        db.commit()
        print("GuardSLM LMS database successfully seeded with expanded research benchmark data.")
        print(f"Users: {len(users_by_username)}, Courses: {len(courses_by_code)}, Enrollments: {len(memberships)}, "
              f"Assignments: {len(assignments_def)}, Submissions: {len(submissions_def)}, Quizzes: {len(quizzes_def)}, Attempts: {len(attempts_def)}")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
