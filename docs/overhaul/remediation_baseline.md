# GuardSLM Academic LMS & Benchmark: Comprehensive Remediation Baseline

**Generated**: 2026-11-12  
**Repository**: `AkarshiAaryan/Aaryan_LMS`  
**Working Directory**: `/home/regenesis/Desktop/guard-slm-lms`  
**Purpose**: Phase 0 baseline audit and gap analysis prior to engineering remediation.

---

## 1. Executive Summary

A comprehensive pre-remediation inspection of the repository was conducted. While the application currently builds and the test suite passes (63/63 backend tests, Vite frontend build in 27.23s), multiple severe security vulnerabilities, data-integrity defects, API contract mismatches, schema/migration risks, and benchmark provenance limitations were uncovered across the codebase.

This baseline documents the verified state of the codebase before any code modifications.

---

## 2. Existing Test & Build Results

### 2.1 Backend Pytest Suite
- **Command Executed**: `pytest backend/app/tests -v`
- **Execution Date**: 2026-11-12
- **Result**: **63 passed, 1 warning in 82.78s**
- **Test Breakdown**:
  - `backend/app/tests/test_auth.py`: 29 passed (Authentication, login, token verification, session lifecycle)
  - `backend/app/tests/test_new_modules.py`: 5 passed (Discussions, modules, files, peer reviews, attendance)
  - `backend/app/tests/test_scenarios.py`: 20 passed (Baseline RBAC scenarios 1-20)
  - `backend/app/tests/test_security_regressions.py`: 9 passed (Security regression tests)
- **Warning**: Starlette TestClient `BlockingPortal` deprecation warning (`anyio.abc.BlockingPortal`).

### 2.2 Test Isolation Flaws Identified (`backend/app/tests/conftest.py`)
- **Shared Static Database**: Tests run against a single shared SQLite file in the OS temp directory (`/tmp/test_guardslm.db`).
- **No Transaction Isolation / Savepoint Rollback**: Tests do not wrap test cases in individual database transactions with rollbacks; changes made by one test persist and bleed into subsequent tests.
- **Seeded State Fragility**: Fixtures rely on global database seeding (`seed_database()`) at session start, creating ordering dependencies and potential unique-constraint collisions (as previously occurred with `PeerReview`).

### 2.3 Frontend Production Build
- **Command Executed**: `npm run build` in `frontend/`
- **Execution Date**: 2026-11-12
- **Result**: **Clean build in 27.23s**
- **Artifacts Generated**:
  - `dist/index.html` (0.93 kB)
  - `dist/assets/index-m9BD2PGd.css` (27.34 kB)
  - `dist/assets/index-D7Kq8-sO.js` (383.75 kB)

---

## 3. Existing API Endpoint Inventory & Contract Mismatches

### 3.1 Backend Endpoint Inventory

| Module | Route / Prefix | HTTP Method | Handler Function | Response Model |
| :--- | :--- | :---: | :--- | :--- |
| `auth.py` | `/auth/login` | POST | `login_for_access_token` | `Token` |
| | `/auth/me` | GET | `get_current_user_profile` | `UserOut` |
| | `/auth/logout` | POST | `logout` | `Dict[str, str]` |
| `users.py` | `/users` | GET | `list_users` | `List[UserOut]` |
| `courses.py` | `/courses` | GET | `list_courses` | `List[CourseOut]` |
| | `/courses` | POST | `create_course` | `CourseOut` |
| | `/courses/{course_id}` | GET | `get_course_by_id` | `CourseOut` |
| | `/courses/{course_id}/assignments` | GET | `list_course_assignments` | `List[AssignmentOut]` |
| | `/courses/{course_id}/announcements` | GET | `list_course_announcements` | `List[AnnouncementOut]` |
| | `/courses/{course_id}/policies` | GET | `list_course_policies` | `List[CoursePolicyOut]` |
| `assignments.py`| `/assignments/{assignment_id}` | GET | `get_assignment_by_id` | `AssignmentOut` |
| | `/courses/{course_id}/assignments` | POST | `create_assignment` | `AssignmentOut` |
| | `/assignments/{assignment_id}` | PUT | `update_assignment` | `AssignmentOut` |
| `submissions.py`| `/assignments/{assignment_id}/submissions` | GET | `list_assignment_submissions` | `List[SubmissionOut]` |
| | `/submissions/{submission_id}` | GET | `get_submission_by_id` | `SubmissionOut` |
| | `/assignments/{assignment_id}/submit` | POST | `submit_assignment` | `SubmissionOut` |
| | `/submissions/{submission_id}/grade` | POST | `grade_submission` | `SubmissionOut` |
| | `/submissions/{submission_id}/history` | GET | `get_submission_grade_history`| `List[GradeHistoryOut]` |
| `grades.py` | `/courses/{course_id}/grades` | GET | `get_course_gradebook` | Custom Dict List |
| | `/courses/{course_id}/publish-grades` | POST | `publish_course_grades` | Custom Dict |
| `quizzes.py` | `/courses/{course_id}/quizzes` | GET | `list_course_quizzes` | `List[QuizOut]` |
| | `/quizzes/{quiz_id}` | GET | `get_quiz_by_id` | `QuizOut` |
| | `/quizzes/{quiz_id}/attempts` | GET | `get_quiz_attempts` | `List[QuizAttemptOut]` |
| | `/quizzes/{quiz_id}/attempts` | POST | `start_quiz_attempt` | `QuizAttemptOut` |
| | `/quizzes/{quiz_id}/start` | POST | `start_quiz_attempt` | `QuizAttemptOut` |
| | `/quizzes/{quiz_id}/answer-key` | GET | `get_quiz_answer_key` | Custom Dict |
| | `/quizzes/attempts/{attempt_id}/submit` | POST | `submit_quiz_attempt` | `QuizAttemptOut` |
| `resources.py` | `/courses/{course_id}/resources` | GET | `list_course_resources` | `List[ResourceOut]` |
| | `/courses/{course_id}/resources` | POST | `create_resource` | `ResourceOut` |
| | `/resources/{resource_id}` | DELETE | `delete_resource` | None (204) |
| `discussions.py`| `/courses/{course_id}/discussions` | GET / POST | `list_threads` / `create_thread` | `List[DiscussionThreadOut]` / `DiscussionThreadOut` |
| | `/discussions/{thread_id}` | GET | `get_thread` | `DiscussionThreadOut` |
| | `/discussions/{thread_id}/posts` | POST | `create_post` | `DiscussionPostOut` |
| | `/discussions/{thread_id}/lock` | PUT / POST | `lock_thread` | `DiscussionThreadOut` |
| `modules.py` | `/courses/{course_id}/modules` | GET / POST | `list_modules` / `create_module` | `List[LearningModuleOut]` / `LearningModuleOut` |
| | `/modules/{module_id}` | GET | `get_module` | `LearningModuleOut` |
| | `/modules/{module_id}/lessons` | POST | `create_lesson` | `LessonOut` |
| | `/lessons/{lesson_id}` | GET | `get_lesson` | `LessonOut` |
| `files.py` | `/courses/{course_id}/files` | GET / POST | `list_course_files` / `create_course_file` | `List[CourseFileOut]` / `CourseFileOut` |
| | `/files/{file_id}` | GET | `get_file_metadata` | `CourseFileOut` |
| | `/files/{file_id}/download` | GET | `download_file` | Binary / Stream (mock text) |
| | `/files/{file_id}` | DELETE | `delete_file` | None (204) |
| `peer_reviews.py`| `/submissions/{submission_id}/peer-reviews`| POST | `create_peer_review` | `PeerReviewOut` |
| | `/peer-reviews/{review_id}` | GET | `get_peer_review` | `PeerReviewOut` |
| | `/submissions/{submission_id}/appeal` | POST | `create_grade_appeal` | `GradeAppealOut` |
| | `/appeals/{appeal_id}/resolve` | PUT | `resolve_grade_appeal` | `GradeAppealOut` |
| `attendance.py`| `/courses/{course_id}/attendance` | GET / POST | `list_attendance` / `record_attendance` | `List[AttendanceRecordOut]` / `AttendanceRecordOut` |
| | `/attendance/{record_id}/lock` | PUT | `lock_attendance_record` | `AttendanceRecordOut` |
| | `/attendance/{record_id}/excuse` | POST | `submit_absence_excuse` | `AttendanceRecordOut` |
| `admin.py` | `/admin/stats` | GET | `get_admin_stats` | `AdminStatsOut` |
| | `/admin/users` | GET / POST | `list_all_users` / `create_user` | `List[UserOut]` / `UserOut` |
| | `/admin/users/{user_id}` | PUT | `update_user` | `UserOut` |
| | `/admin/enrolments` | GET / POST | `list_all_enrollments` / `create_enrollment` | `List[EnrollmentOut]` / `EnrollmentOut` |
| | `/admin/enrolments/{enrolment_id}` | DELETE | `delete_enrollment` | None (204) |
| `logs.py` | `/admin/logs` | GET | `get_audit_logs` | `List[ActivityLogOut]` |

### 3.2 Frontend/Backend API Contract Mismatches

1. **Student Dashboard Grades Summary**:
   - `frontend/src/pages/Dashboard.jsx:49` calls `GET /grades/me`.
   - **Backend Status**: Endpoint does NOT exist anywhere in the backend routes. Student dashboard fails to load academic overview.
2. **Gradebook Update Action**:
   - `frontend/src/pages/Gradebook.jsx:88` calls `PUT /grades/{editSubmission.id}`.
   - **Backend Status**: Endpoint does NOT exist. The backend exposes `POST /submissions/{submission_id}/grade`. Grading from standalone Gradebook errors with 404/405.
3. **Gradebook Data Hierarchy**:
   - `frontend/src/pages/Gradebook.jsx:47-60` expects a hierarchical response object containing `{ course, assignments, quizzes, students }`.
   - **Backend Status**: Backend `/courses/{course_id}/grades` returns a flat array of student grade objects (`List[Dict]`), breaking standalone gradebook rendering.
4. **Quiz Submission Endpoint**:
   - `frontend/src/pages/QuizAttempt.jsx:80` calls `POST /attempts/{attempt_id}/submit`.
   - **Backend Status**: The backend endpoint is mounted under `POST /quizzes/attempts/{attempt_id}/submit`. Submissions fail with 404.
5. **Direct Quiz Attempt Lookup Missing**:
   - `frontend/src/pages/QuizAttempt.jsx:25-50` has to iteratively fetch all courses, fetch all quizzes for each course, and fetch all attempts for each quiz to locate the target `attemptId`.
   - **Backend Status**: No direct `GET /attempts/{attempt_id}` or `GET /quizzes/attempts/{attempt_id}` endpoint exists, causing an extreme N+1 query burst on the frontend.
6. **Course-Effective Role vs Global Role**:
   - Multiple frontend pages (`Assignments.jsx`, `Quizzes.jsx`, `Gradebook.jsx`, `Resources.jsx`) check `user.role` from `AuthContext` (global role) instead of the effective course role (`course.current_user_role`). A user who is globally a TA but enrolled as a student in a specific course incorrectly sees staff buttons or is prevented from submitting work.

---

## 4. Identified Data-Integrity & Security Vulnerabilities

1. **Enrolment Status Bypassed Centrally (`backend/app/permissions.py`)**:
   - `get_user_course_role()` queries `Enrollment` by `(course_id, user_id)` but completely ignores `Enrollment.status`.
   - Suspended or revoked students/TAs retain full active privileges as long as the enrollment row exists.
2. **Unpublished Grade Leakage (`backend/app/routes/submissions.py`)**:
   - `serialize_submission()` unconditionally serializes `grade`, `feedback`, `graded_by_id`, `graded_by_name`, and `graded_at` regardless of whether `submission.is_published` is `False`.
   - Any student querying `GET /submissions/{id}` directly receives the unpublished score and internal instructor notes before grades are officially released.
3. **Duplicate Group Submissions Permitted**:
   - `Submission` uniqueness is constrained to `(assignment_id, student_id)`.
   - For group assignments, multiple students in the same group can submit separate, conflicting responses.
   - Individual assignments do not reject `group_id` if supplied by the client.
4. **Quiz Scoring Flaws & Zero-Denominator Glitch (`backend/app/routes/quizzes.py`)**:
   - In `submit_quiz_attempt`, `total_possible` is accumulated solely from questions present in `payload.answers`.
   - If `payload.answers` is empty (`[]`), `total_possible` is 0, and the handler awards **100% score** (`percentage = 100`).
   - If a student answers only 1 question out of 10 correctly, the denominator is 10 instead of 100, awarding **100% score**.
   - Submitting duplicate `question_id`s in `answers` awards duplicate points.
   - Finished attempts are not checked for immutability and can be resubmitted repeatedly.
   - Quiz time limits (`time_limit_minutes`) and closing windows (`close_date`) are not enforced at submission time.
   - Direct `datetime.now(timezone.utc)` is used instead of the deterministic `Clock`.
5. **Course File Access & Storage Mocking (`backend/app/routes/files.py`)**:
   - Download endpoint streams a dummy string (`--- Content of ... ---`) rather than actual file bytes.
   - `access_level` accepts any arbitrary string without validation against allowed enum (`public`, `students`, `staff_only`, `group_only`, `private`).
   - Group ownership checks do not verify that the group belongs to the file's course.
6. **Unpublished Assessment Exposure in Gradebook (`backend/app/routes/grades.py`)**:
   - `get_course_gradebook` does not filter `Assignment.is_published` or `Quiz.is_published` for student requests. Students can see draft assessment titles, maximum scores, and dates.
7. **Simulation Clock Fail-Open Flaw (`backend/app/clock.py`)**:
   - When parsing `X-Simulation-Time`, `except ValueError: pass` silently falls back to real wall-clock time rather than failing with HTTP 400.
8. **Hardcoded Grading Limits (`backend/app/schemas.py`, `backend/app/routes/submissions.py`)**:
   - Grades are hardcoded with `le=100` instead of validating against `assignment.max_grade`.
9. **Private Discussion Participants Missing (`backend/app/routes/discussions.py`)**:
   - Discussion threads mark `is_private=True`, but lack explicit participant lists; any course staff member can view without structured routing.
10. **Peer Reviews & Grade Appeals Missing Staff Lifecycle**:
    - Peer reviews cannot be created or allocated by staff via API; relies on manual DB insertions.
    - Grade appeals change status to approved without an authorized regrading workflow or grade-history audit entry.
11. **Attendance Disconnected from Course Sessions (`backend/app/routes/attendance.py`)**:
    - Attendance records store raw dates without an `AttendanceSession` model.
    - Lack structured start/end time, meeting room, and session-level locking.

---

## 5. Schema, Migration, & Database Limitations

1. **Model Count Discrepancy**:
   - The codebase defines **26 SQLAlchemy models** (inheriting from `Base`), but previous documentation incorrectly claims 24.
2. **Missing Alembic Migration Infrastructure**:
   - The repository has no `alembic/` directory or `alembic.ini`.
   - Schema alterations have relied on raw `sqlite3` `ALTER TABLE` or `Base.metadata.create_all()`, which does not modify existing table columns in SQLite.
3. **SQLite Foreign Keys Disabled**:
   - Direct SQLite connection test reveals `PRAGMA foreign_keys: (0,)` (disabled).
   - Foreign key constraints, cascading deletes, and referential integrity are not enforced by SQLite connections unless explicitly enabled via SQLAlchemy connection listeners.
4. **Seed File Discrepancy**:
   - `backend/app/seed.py` header comments state "23 demo accounts", but the script seeds 54 users.
5. **`CourseSection` Field Incompleteness**:
   - Documentation claims meeting times, room, and capacity, but the model currently only contains `id`, `course_id`, `section_number`, `title`, and `instructor_id`.

---

## 6. Known Benchmark-Generation Limitations (`tools/benchmark/`)

1. **Non-Portable Absolute File Paths**:
   - `package_builder.py` hardcodes `/home/regenesis/Desktop/guard-slm-lms/research_snapshots_2000` as default directories.
2. **Answer-Correlated Template Selection**:
   - In `package_builder.py::_get_page_template()`, template selection relies on `case.expected_decision == "ALLOW"`, which risks introducing decision-correlated artifacts into the accessibility tree.
3. **Policy Snapshot Template Hardcoding**:
   - `package_builder.py::_get_policy_template()` hardcodes `TC01_policy.md` for all 2,000 cases, ignoring the case's specific grounding policy (`POL-001` - `POL-016`).
4. **Validator Incomplete Coverage**:
   - `tools/benchmark/validation/validator.py` checks only the first 200 SLM input files for label leakage (`[:200]`).
   - Check 11 (Scenario Families representation) contains a `pass` statement and hardcodes `True` without actually computing family coverage from the data.
5. **Constraint Reminder**:
   - `research_snapshots_2000/` contains the generated dataset and must NOT be overwritten, regenerated, or deleted during this remediation. All benchmark tool repairs must be tested in isolated temporary directories.

---

## 7. Baseline Verification Sign-off

- Existing backend test suite verified: **63/63 passing**.
- Existing frontend production build verified: **Vite build clean**.
- All items in this baseline have been directly verified via code inspection and runtime execution.
