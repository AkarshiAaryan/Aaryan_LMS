# 🎓 Aaryan_LMS (GuardSLM Academic Portal & Security Benchmark)

> A modern, full-featured University Learning Management System (LMS) built with **React 18**, **Tailwind CSS**, and **FastAPI**, engineered with enterprise-grade **Role-Based Access Control (RBAC)**, FERPA-compliant privacy, and an integrated 2,000-case AI safety evaluation benchmark.

---

## 📖 Welcome! What is Aaryan_LMS?

Think of **Aaryan_LMS** as an institutional university platform like Canvas, Blackboard, or Moodle—built specifically to model authentic academic workflows between **Students**, **Teaching Assistants (TAs)**, **Professors**, and **Administrators**.

Whether you are a developer, an academic evaluator, or exploring the platform for the first time, this guide explains **every single feature**, how the system behaves, and how to get started in seconds.

---

## ⚡ Quick Start: Run the Project in 2 Steps

### Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **Node.js 18+** with `npm`

### Method 1: Helper Scripts (Recommended)
Open two terminal windows in the project directory:

```bash
# Terminal 1: Backend API & Database
./start_backend.sh

# Terminal 2: Frontend Web Application
./start_frontend.sh
```

### Method 2: Manual Commands
```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
python3 -m app.seed
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

### 🌐 Where to Open
- **Web Application Portal**: [http://localhost:5173](http://localhost:5173)
- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative API Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔑 Demo Accounts & 1-Click Persona Login

You never need to remember complex credentials. The sign-in page includes a **1-click Persona Selector** at the top that automatically signs you in as any user in the university!

- **Universal Password for ALL accounts**: `GuardSLM2026!`

### Popular Demo Accounts to Try:

| Persona | Role | Who Are They? | Why Log In As Them? |
| :--- | :---: | :--- | :--- |
| **`student01`** | Student | Asha Mehta | Enrolled in `CSE301` & `CSE302`. View student grades, submit assignments, take quizzes, read modules. |
| **`ta01`** | TA / Student | Sam Lee | **Dual-Role Persona!** He is the **Teaching Assistant** for `CSE301` (can grade peers), but simultaneously a **regular Student** in `CSE302` (can only submit homework). |
| **`prof01`** | Professor | Dr. Mira Shah | Computer Science Department Chair. Can create assignments, publish grades, resolve grade appeals, and edit courses. |
| **`prof02`** | Professor | Dr. Kabir Rao | Networks Professor (`CSE302`). Notice that Prof Shah cannot modify Prof Rao's courses! |
| **`admin01`** | Administrator | Alex Admin | University Dean / Super Admin. Manages departments, archives courses, and views the live security audit log. |

---

## 🌟 Features & Functionality (What Can You Do?)

### 1. 🎓 Student Experience
- **Interactive Course Hub**: View enrolled courses (`CSE301: Database Systems`, `CSE302: Computer Networks`, `CSE303: Operating Systems`, `HCI401: Human-Computer Interaction`).
- **Homework & Assignment Submission**:
  - Upload text, source code, or files before the deadline.
  - Supports both **Individual** and **Group Assignments** (Team Alpha, Beta, etc.). Group submissions automatically sync so teammates don't overwrite each other's work!
  - Real-time countdown timers and late submission tracking.
- **Timed Quizzes & Assessments**:
  - Take online multiple-choice quizzes with live countdown timers.
  - Enforced attempt limits (e.g., maximum 2 attempts).
  - Secure answer keys: correct answers remain hidden until the official class release date.
- **Confidential Personal Gradebook**:
  - Full FERPA compliance: students can **only** see their own grades and feedback.
  - "Draft" grades currently being reviewed by TAs are safely hidden until the professor publishes them.
- **Class Discussion Forums**:
  - Ask course questions with **nested replies**.
  - Start **Private Confidential Threads**: mark a question as "Private" so only you and the teaching staff can see it.
- **Structured Learning Modules**:
  - Browse step-by-step lecture units and lessons.
  - Check off completed modules as you study.
  - Prerequisite protection: upcoming modules stay locked until their release date or until prerequisites are completed.
- **Learning Resources & Course Files**:
  - Browse syllabi, lecture slides, and laboratory guides.
  - **In-App Document Viewer**: Click **"View"** on any resource to open an interactive document preview right in the app.
  - **Instant Download**: Click **"Download"** to save documents directly to your computer without external DNS errors.
- **Double-Blind Peer Reviews**:
  - Review your classmates' submissions anonymously. You see `Anonymous Reviewer` so grading is fair and unbiased.
- **Grade Appeals**:
  - If you believe an exam or homework was marked incorrectly, submit a formal **Grade Appeal** with your justification for instructor review.
- **Attendance Excuses**:
  - Check your lecture attendance record and submit an official excuse if you were absent.

---

### 2. 🧑‍🏫 Teaching Assistant (TA) Experience
- **Smart Dual-Role Awareness**:
  - If a TA is grading in their staff course (`CSE301`), they receive full instructor grading panels.
  - If that same TA visits a class where they are a student (`CSE302`), the LMS automatically switches them to the student submission view!
- **Decimal Grading & Feedback**:
  - Grade submissions with fractional scores (e.g. `87.5 / 100`) and leave detailed feedback notes.
- **Grade History & Audit Trail**:
  - If a score is edited, the system saves the prior score, who changed it, and why.
- **Forum Moderation**:
  - Pin important discussions to the top of the forum.
  - Lock resolved threads to prevent further student chatter.
  - Flag inappropriate messages for review.
- **Section Attendance**:
  - Take attendance for assigned discussion sections and record Present / Absent / Excused statuses.

---

### 3. 👨‍🏫 Professor & Instructor Experience
- **Course Administration**:
  - Create and edit assignments, instructions, and due dates.
  - Design quizzes, specify time limits, and set answer key release dates.
  - Upload lecture notes, syllabus files, and staff-only grading rubrics.
- **Grade Publishing Controls**:
  - Keep grades in **Draft Mode** while the grading team marks submissions.
  - Click **"Publish Grades"** to release final grades to the entire roster simultaneously.
- **Grade Appeal Adjudication**:
  - Review student grade appeals, approve or reject them, and adjust scores with automatic audit trails.
- **Course Soft-Archiving**:
  - Archive completed semesters (`PUT /courses/{id}/archive`) to prevent further edits while keeping records accessible.

---

### 4. 🛡️ University Administrator Experience
- **Academic Departments**:
  - Create, view, update, and manage university departments (`CS`, `EE`, `HCI`, `DS`).
- **Student Enrollment Lifecycle**:
  - Update student enrollment statuses between:
    - `active`: Full student access.
    - `suspended`: Temporarily frozen (blocked from taking quizzes or submitting work).
    - `revoked`: Withdrawn / expelled (completely blocked with HTTP 403 Forbidden).
  - Reassign students to different lecture sections.
- **Real-Time Security & Telemetry Audit Log (`/admin/logs`)**:
  - A live institutional security stream tracking every attempted action in the university.
  - Displays the timestamp, username, role, target resource, HTTP status, and outcome (`ALLOW` or `BLOCK`).

---

## 🔒 Security & Privacy: How Does the LMS Protect Data?

1. **Dual-Layer RBAC (Role-Based Access Control)**:
   - Your access is determined not just by who you are globally, but by **which course you are currently looking at**.
2. **FERPA Student Privacy**:
   - Students can never inspect other students' homework, exam attempts, or grades.
   - Draft grades remain confidential until published.
3. **No Traversal File Storage (`storage.py`)**:
   - Files uploaded to the system are sanitized to prevent directory traversal attacks (e.g. `../../etc/passwd`).
   - Files are stored on disk with unique UUIDs and SHA-256 hashes.
4. **Time Machine Simulation Clock (`clock.py`)**:
   - Testing deadlines is normally hard because you have to wait for the system clock.
   - Aaryan_LMS supports an `X-Simulation-Time` header, allowing researchers and automated tests to test future deadlines without changing your computer's clock!
5. **Database Foreign Key Integrity**:
   - SQLite foreign keys are strictly enforced on every database connection (`PRAGMA foreign_keys = ON`).
6. **Automatic Schema Migrations (`migrate_db.py`)**:
   - Whenever the backend starts up, it automatically checks all 28 database tables and columns, adding missing fields without erasing existing data.

---

---

## 🤖 Simulated Educational AI Assistant & Policy Guard

A central highlight of the platform is the **Embedded Educational AI Assistant** and **Authoritative Policy Guard** testbed. Rather than trusting opaque external AI APIs, this system runs a 100% deterministic, hybrid safety guard that intercepts and evaluates every prompt before generating academic guidance.

### 1. In-App Floating AI Assistant Widget
- Accessible from the bottom-right corner across **all pages** (Course View, Assignments, Quizzes, Gradebook, etc.).
- Automatically detects the user's active page, course ID, assessment status (`active`, `closed`, `upcoming`), and deadline context.
- Provides progressive pedagogical hints, concept walkthroughs, and debugging advice without giving away full homework solutions or exam answers.

### 2. Authoritative Policy Guard Decisions
Every single interaction is categorized into one of four deterministic outcomes:
| Decision | Meaning | System Behavior |
| :---: | :--- | :--- |
| **`ALLOW`** | Permitted Academic Request | Returns rich conceptual explanations, practice problems, or instructional rubrics. |
| **`LIMIT`** | Bounded Assistance | Restricts assistance to conceptual hints and pseudocode structures during active assessment windows. |
| **`BLOCK`** | Prohibited Action | Refuses the request citing the specific policy, logs violation evidence, and suggests a permitted alternative. |
| **`ESCALATE`** | Critical Safety Threshold | Immediately freezes request and files an administrative compliance escalation ticket. |

### 3. The 12 Institutional Violation Categories
1. `EXCESSIVE_ASSISTANCE`: Over-reliance on AI replacing core learning objectives.
2. `DIRECT_SOLUTION_SEEKING`: Demanding copy-pasteable homework or project solutions.
3. `ASSESSMENT_BYPASS`: Attempting to circumvent quiz, exam, or deadline restrictions.
4. `CONTEXTUAL_POLICY_VIOLATION`: Actions forbidden in the current page or assessment state.
5. `ROLE_IMPERSONATION`: Claiming to be an instructor or dean to extract restricted answers.
6. `POLICY_EVASION`: Rephrasing or prompt-injecting to bypass previous refusals.
7. `INCREMENTAL_EXTRACTION`: Slicing solutions into smaller pieces across multiple turns.
8. `UNAUTHORISED_GRADING`: Delegating authoritative student marks or grade calculations to AI.
9. `STUDENT_PRIVACY_VIOLATION`: Viewing or exporting peer student submissions or private logs (FERPA).
10. `UNAUTHORISED_DATA_ACCESS`: Accessing course materials where the user is not actively enrolled.
11. `UNAUTHORISED_ADMIN_MONITORING`: Administrators snooping on student private chats without an audit warrant.
12. `REPEATED_BOUNDARY_TESTING`: Repeatedly testing safety boundaries after receiving refusals.

### 4. Multi-Turn Conversation Auditor (`/research/audit`)
Individual guard decisions are not enough—adversaries often slice prompts across turns. The **Conversation Auditor** analyzes entire longitudinal interaction histories to assign multi-turn safety labels:
- **`HARMLESS`** (Action: `NONE`): Legitimate study sessions (including 5–10+ questions).
- **`SUSPICIOUS`** (Action: `REVIEW`): Isolated policy refusals or prompt rephrasing after a block.
- **`POLICY_VIOLATING`** (Action: `ESCALATE`): Incremental solution extraction, repeated boundary testing, or role spoofing.

### 5. Research & Compliance Console & Scenario Runner
Visit **`/research/audit`** (linked in the left navigation sidebar) to:
- Browse interactive timelines of all student and staff AI sessions.
- Run the **51 standard scenario benchmark** (ST01–ST12, TA01–TA10, PR01–PR10, AD01–AD07, AU01–AU12) with 1-click execution.
- Export complete conversation telemetry to **JSON** or **CSV** for research papers and benchmarks.

---

## 🔬 AI Safety & Benchmark Research (GuardSLM V2)

Beyond being a university LMS, this repository serves as a world-class evaluation benchmark for **Small Language Models (SLMs)** functioning as **AI Authorization Guards**:

- **2,000 Verified Test Cases (`research_snapshots_2000/`)**: Spanning 13 scenario families.
- **1,000 Controlled Contrast Pairs**: Two test cases differing by exactly **one** variable (e.g., Professor vs TA on the same file) to test if AI models can detect nuanced security boundaries.
- **Strict Double-Blind Testing**: Public evaluation packages contain **zero labels or answers**, guaranteeing genuine evaluation without data leakage.
- **20-Point Compliance Validator**: Validates manifest integrity, decision balance (47.9% ALLOW / 52.1% BLOCK), and 100% label isolation.

```bash
# View dataset distribution and statistics
python3 -m tools.benchmark.cli stats

# Run full 20-point automated compliance validator
python3 -m tools.benchmark.cli validate
```

---

## 🧪 Quality Assurance & Test Suite

The entire backend and frontend are protected by automated tests:

### Run Automated Backend Tests (94 Tests)
```bash
python3 -m pytest backend/app/tests -v
```
*(Tests pass 100% in ~20 seconds across authentication, RBAC scenarios, file storage, quiz integrity, AI Policy Guard, Multi-Turn Auditor, and API endpoints).*

### Run Frontend Production Build
```bash
cd frontend
npm run build
```
*(Builds clean Vite production bundle in ~5.1s with 0 errors).*


---

## 📂 Project Directory Structure

```text
guard-slm-lms/
├── start_backend.sh                # 1-click startup script for FastAPI backend
├── start_frontend.sh               # 1-click startup script for React frontend
├── README.md                       # Master system documentation (this file)
│
├── backend/
│   ├── requirements.txt            # Python backend dependencies
│   ├── guardslm.db                 # SQLite database (auto-seeded with 54 personas)
│   ├── storage/files/              # Secure local disk file storage directory
│   └── app/
│       ├── main.py                 # FastAPI application & startup migration lifespan
│       ├── database.py             # SQLite database engine with foreign key enforcer
│       ├── clock.py                # Time simulation service (X-Simulation-Time)
│       ├── storage.py              # File path sanitization & disk storage subsystem
│       ├── migrate_db.py           # Auto-migration script for 28 database models
│       ├── models.py               # 28 Relational SQLAlchemy database models
│       ├── schemas.py              # Pydantic data validation & serialization models
│       ├── auth.py                 # JWT access tokens & bcrypt password encryption
│       ├── permissions.py          # Centralized course-effective RBAC engine
│       ├── seed.py                 # 54 Personas, 4 courses, departments & assessments
│       ├── routes/                 # REST API routes (courses, files, grades, etc.)
│       └── tests/                  # 79 Automated regression & security tests
│
├── frontend/
│   ├── package.json                # React 18, React Router v6, Tailwind CSS
│   ├── vite.config.js              # Vite bundler with API reverse proxy
│   └── src/
│       ├── api.js                  # Axios HTTP client with JWT interceptor
│       ├── components/             # Navigation, Sidebar, Modals, Status Badges
│       ├── context/                # Authentication & User Role context
│       └── pages/                  # CourseDetail, Gradebook, Quizzes, Resources, etc.
│
├── tools/benchmark/                # Benchmark V2 generation & validation engine
│   ├── catalogs/                   # Grounding policies, personas, and families
│   ├── generation/                 # Case generator & deduplication engine
│   ├── validation/                 # 20-Point automated compliance validator
│   └── cli.py                      # Benchmark CLI (stats, validate, generate)
│
├── research_snapshots_2000/         # GuardSLM 2,000-case evaluation benchmark dataset
├── research_snapshots_100/         # Baseline 100-case dataset (preserved)
├── research_snapshots/             # Baseline 20-case pilot dataset (preserved)
└── docs/                           # Technical architecture, schemas, and reports
```

---

## 📄 License & Attribution

Developed for academic education and AI safety research into Small Language Model (SLM) authorization guards. Built with standard open-source tools: React, Vite, Tailwind CSS, FastAPI, and SQLAlchemy.
