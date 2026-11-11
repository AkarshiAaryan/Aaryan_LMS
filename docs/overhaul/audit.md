# GuardSLM LMS Overhaul Audit (V1 Baseline → V2 Benchmark)

**Date**: November 11, 2026  
**Auditor**: Antigravity Research Engineering  
**Target**: Upgrade GuardSLM LMS from 100-case pilot to 2,000-case contextual authorization research benchmark.

---

## 1. Executive Summary & Existing Scale

The current GuardSLM Academic LMS codebase provides a functional dual-layer RBAC academic web application with a 100-case benchmark dataset (`research_snapshots_100/`). All 49 existing Pytest unit/integration tests pass and the frontend React 18 production build compiles cleanly.

### Current Entity Scale
| Component | Existing Count | Status in Codebase |
| :--- | :---: | :--- |
| **Global Personas** | 23 | Seeded in `seed.py` (1 Admin, 2 Profs, 4 TAs, 16 Students) |
| **Courses** | 4 | `CSE301`, `CSE302`, `CSE303`, `HCI401` |
| **Course Memberships** | 50 | In `enrollments` table with course-scoped roles |
| **Collaborative Groups** | 4 | Teams Alpha, Beta, Gamma, Delta in `HCI401` |
| **Assignments** | 13 | 4 in 301, 3 in 302, 3 in 303, 3 in 401 |
| **Submissions** | 38 | 6 states (draft, submitted, graded-draft, graded-pub, locked, extended) |
| **Quizzes** | 12 | 3 per course (open, closed, upcoming windows) |
| **Quiz Attempts** | 22 | Finished, scored, and in-progress attempts |
| **Resources** | 28 | 16 student-facing, 12 staff-only |
| **Grade History Logs** | 6 | Audited regrading records with reasons |
| **Course Policies** | 26 | Displayed in frontend tab and enforced in backend |
| **Activity Telemetry** | 300+ | ALLOW/BLOCK logs in `activity_logs` |
| **Benchmark Datasets** | 2 | `research_snapshots/` (20 cases) and `research_snapshots_100/` (100 cases) |

---

## 2. Architecture & Current Routes

- **Backend**: FastAPI + SQLAlchemy + SQLite (`backend/app/main.py`)
- **Frontend**: Vite + React 18 + Tailwind CSS (`frontend/src/App.jsx`)
- **Auth**: JWT Bearer token via `backend/app/auth.py`

### Route Catalog & Handlers
- **Auth (`/auth`)**: `/login`, `/me`, `/logout`
- **Users (`/users`)**: `/users/me` (self), `/users` (admin only)
- **Courses (`/courses`)**:
  - `GET /courses`: Filtered by user enrollment (admin sees all)
  - `GET /courses/{id}`: Detailed view with course-specific role badge
  - `GET /courses/{id}/announcements`, `POST /courses/{id}/announcements`
  - `GET /courses/{id}/policies`: List of active course policy rules
- **Assignments (`/courses/{id}/assignments`, `/assignments/{id}`)**:
  - Assignment listing & detail
  - `POST /courses/{id}/assignments`: Professor / Admin only
  - `PUT /assignments/{id}`: Professor / Admin only
- **Submissions (`/assignments/{id}/submit`, `/submissions/{id}`)**:
  - Submission creation & updates
  - `POST /submissions/{id}/grade`: Staff (Prof/TA) grading with audit history
- **Grades (`/courses/{id}/grades`, `/grades/me`, `/courses/{id}/publish-grades`)**:
  - `GET /courses/{id}/grades`: Role-filtered (students get self only; staff get roster)
  - `POST /courses/{id}/publish-grades`: Professor/Admin only (TAs blocked)
- **Quizzes (`/courses/{id}/quizzes`, `/quizzes/{id}`)**:
  - `POST /quizzes/{id}/attempts`: Start attempt
  - `GET /quizzes/{id}/attempts`: Staff view or student personal attempts
  - `GET /quizzes/{id}/answers`: Answer key access governed by release schedule
- **Resources (`/courses/{id}/resources`, `/resources/{id}`)**:
  - `GET /resources/{id}`: Single resource retrieval
  - `POST /courses/{id}/resources`: Staff creation
- **Admin (`/admin`)**:
  - `/admin/users`: User management
  - `/admin/enrolments`: Roster management
  - `/admin/stats`: KPI summaries
- **Logs (`/admin/logs`)**: Query audit telemetry with ALLOW/BLOCK outcomes

---

## 3. Verified Security & Authorization Vulnerabilities

An independent audit of `backend/app/permissions.py` and route handlers revealed the following verified authorization gaps:

### 3.1 Quiz Start Authorization Flaw (`verify_quiz_start`)
- **Issue**: `verify_quiz_start` checked `if not course_role: raise 403`. Because TAs and Professors have course roles (`course_role == "ta"` or `"professor"`), they were not rejected from initiating student quiz attempts.
- **Fix**: Require `course_role == "student"`. Staff members attempting to start student quiz attempts must be rejected with 403 unless a student attempt policy explicitly applies.

### 3.2 Resource Visibility Bypass (`verify_resource_access`)
- **Issue**: `verify_resource_access()` checked `is_staff_only` but completely ignored `resource.is_visible`. If an instructor marked a resource as hidden/invisible (`is_visible = False`), any student who guessed the resource ID via `GET /resources/{id}` could retrieve it.
- **Fix**: Reject students if `resource.is_visible == False` with `403 Forbidden`.

### 3.3 Submission Ownership & Group Scoping Flaw (`verify_submission_edit`)
- **Issue**:
  1. The group membership check `GroupMember.group_id == submission.group_id` did not verify that the group belongs to the assignment's course.
  2. It did not verify that the user's course enrollment status is currently active (revoked/withdrawn students could still submit if group member rows lingered).
- **Fix**: Ensure `group.course_id == assignment.course_id` and enforce active student enrollment at edit time.

### 3.4 Unpublished Assignment / Quiz Leakage
- **Issue**: In `routes/assignments.py`, `list_course_assignments` and `get_assignment_by_id` did not filter out `is_published == False` for students.
- **Fix**: Enforce `is_published == True` for all non-staff student queries.

### 3.5 Non-Deterministic Clock & Silent Time Fallback
- **Issue**: `parse_iso_datetime` caught `Exception` and silently called `utc_now()`. If an assignment had a malformed deadline, it defaulted to the current second, introducing unpredictable authorization behavior. Furthermore, hardcoded `datetime.now(timezone.utc)` calls prevented deterministic time travel during test simulations.
- **Fix**: Implement an injectable `Clock` service supporting simulation time (via header `X-Simulation-Time` or context manager), and raise explicit errors for unparseable dates.

### 3.6 Course Role Revocation & State Invalidation
- **Issue**: Tokens contain a global role. If an enrollment was deleted or suspended in the database, some endpoints relying solely on token payloads could permit unauthorized access.
- **Fix**: Re-evaluate database course membership dynamically in all route dependencies.

---

## 4. Architectural Gaps for 2,000-Case V2 Scale

To achieve the 2,000-case benchmark target with authentic diversity and non-trivial authorization boundaries, the LMS requires:

1. **Expanded Institutional Domain**:
   - Academic Departments (e.g., Computer Science, Electrical Engineering, Human-Centered Design).
   - Course Sections (e.g., Lecture Section 01 vs 02).
   - 40–60 Personas (expanded faculty, TAs with varied duties, multi-course students).
   - Granular roles & permission scopes (Course Coordinator, Section Instructor, Grading TA, Auditor).

2. **Five New Functional LMS Modules**:
   - **Discussions & Messaging**: Course forums, private student-staff threads, post moderation.
   - **Learning Modules**: Course units, lessons, prerequisites, and scheduled release conditions.
   - **File Repository & Sharing**: Folder trees, private vs shared files, download permissions.
   - **Peer Review & Academic Appeals**: Double-blind peer evaluations and grade appeal resolution.
   - **Attendance & Scheduling**: Lecture attendance tracking, excuse requests, attendance locking.

3. **Declarative Benchmark Generation Engine (`tools/benchmark/`)**:
   - Typed Pydantic schemas for test specifications (`case_schema.py`, `actor_schema.py`, etc.).
   - Reusable entity factories (`persona_factory.py`, `course_factory.py`, etc.).
   - Scenario matrix generator with controlled contrast pairs (e.g., Professor vs TA vs Student vs Revoked TA on the identical resource).
   - Isolation manager ensuring no test case mutates state for subsequent cases.
   - Playwright capture pipeline extracting genuine `ariaSnapshot` trees.
   - Independent ground-truth verifier evaluating authoritative backend rules.
   - Automated quality validation (uniqueness, 0 leaked credentials, 0 labels in prompt packages).

---

## 5. Overhaul Stages & Implementation Sequence

- **Stage 1 (Complete)**: Codebase audit & baseline documentation (`docs/overhaul/audit.md`).
- **Stage 2**: Security & authorization refactoring (injectable clock, fix 3.1–3.6, regression tests).
- **Stage 3**: Benchmark engine infrastructure (`tools/benchmark/`).
- **Stage 4**: Existing workflow expansion (assignments, submissions, grades, quizzes, resources).
- **Stage 5**: New modules (Discussions, Modules, Files, Peer Review, Attendance).
- **Stage 6**: Scenario generation (families, contrast pairs, multi-step, adversarial).
- **Stage 7**: Dataset generation (`research_snapshots_2000/`).
- **Stage 8**: Verification, final tests, and `docs/overhaul/implementation_report.md`.
