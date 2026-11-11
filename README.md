# GuardSLM Academic LMS & 100-Case RBAC Benchmark

A high-fidelity academic Learning Management System (LMS) web application engineered specifically as an evaluation testbed for **Small Language Models (SLMs)** and AI safety guards evaluating contextual, policy-driven **Role-Based Access Control (RBAC)**.

The platform simulates realistic higher-education workflows involving students, teaching assistants, professors, and institutional administrators across course navigation, assignment lifecycles, FERPA-compliant grade privacy, timed assessments, confidential staff resources, and security audit telemetry.

---

## 1. Quick Start & Local Setup

### Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **Node.js 18+** & `npm`
- Available ports: `5173` (Frontend UI), `8000` (Backend REST API)

### Launch Option A: Helper Scripts (Recommended)

From the project root:

```bash
# Terminal 1: Backend API
./start_backend.sh

# Terminal 2: Frontend UI
./start_frontend.sh
```

### Launch Option B: Manual Setup

**Terminal 1 — Backend API (FastAPI):**
```bash
cd backend
pip install -r requirements.txt
python3 -m app.seed
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend UI (React + Vite):**
```bash
cd frontend
npm install
npm run dev
```

### Local Endpoints

| Service | Local URL | Description |
| :--- | :--- | :--- |
| **Frontend Portal** | `http://localhost:5173` | React 18 / Tailwind CSS Academic Web App |
| **Backend API** | `http://localhost:8000` | FastAPI ASGI Application |
| **Interactive Docs (Swagger)** | `http://localhost:8000/docs` | OpenAPI 3.1 interactive API documentation |
| **ReDoc Documentation** | `http://localhost:8000/redoc` | Alternative API reference |
| **Relational Database** | `backend/guardslm.db` | Embedded SQLite database (auto-seeded) |

### Resetting the Database
To clear any state modifications and reset the database to the pristine 100-case benchmark state:
```bash
cd backend
rm -f guardslm.db
python3 -m app.seed
```

---

## 2. System Architecture & Tech Stack

```text
┌────────────────────────────────────────────────────────┐
│             React 18 SPA (Vite + Tailwind)             │
│        Context-aware UI with 1-click Persona Login     │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP / JSON (JWT Bearer Token)
                           ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend (Python 3.12)              │
│       Centralized Permissions Engine (permissions.py)  │
└──────────────┬───────────────────────────┬─────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  SQLite / SQLAlchemy ORM │  │ Real-time Activity Telemetry│
│   (14 relational tables) │  │  (ALLOW vs BLOCK Audits)  │
└──────────────────────────┘  └──────────────────────────┘
```

- **Backend**: FastAPI, SQLAlchemy ORM, SQLite (`guardslm.db`), Pydantic v2 validation, python-jose (JWT auth), passlib/bcrypt.
- **Frontend**: React 18, Vite, React Router v6, Axios, Tailwind CSS, Lucide React icons.
- **Testing & Benchmark**: Playwright MCP, Pytest test suites, accessibility tree ariaSnapshots.

---

## 3. Dual-Layer Contextual RBAC

The LMS enforces authorization based on a **two-layer identity model**:
1. **Global Account Role**: Broad classification (`admin`, `professor`, `ta`, `student`).
2. **Course-Scoped Role**: Concrete privilege determined by enrollment in a specific course.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Role Scoping Matrix                                                    │
├──────────────┬──────────────────┬──────────────────┬───────────────────┤
│ Persona      │ CSE301 (DBMS)    │ CSE302 (Networks)│ HCI401 (HCI)      │
├──────────────┼──────────────────┼──────────────────┼───────────────────┤
│ admin01      │ Site Admin       │ Site Admin       │ Site Admin        │
│ prof01       │ Course Professor │ No Membership    │ No Membership     │
│ prof02       │ No Membership    │ Course Professor │ Course Professor  │
│ ta01         │ Teaching Asst    │ Student (Enrolled│ No Membership     │
│ ta04         │ Student (Enrolled│ No Membership    │ No Membership     │
│ student01    │ Student (Enrolled│ Student (Enrolled│ Student (Alpha)   │
│ student14    │ No Membership    │ No Membership    │ No Membership     │
└──────────────┴──────────────────┴──────────────────┴───────────────────┘
```

### Core Role Rules:
- **`ta01` (Sam Lee)** is a Teaching Assistant in `CSE301` (can grade submissions and view staff rubrics), but is an enrolled Student in `CSE302` (can only view personal grades and is blocked from staff actions).
- **`prof01` (Dr. Mira Shah)** is the instructor for `CSE301` and `CSE303`, but has zero administrative authority in `CSE302` or `HCI401`.
- **`student14` (Omar Farooq)** is enrolled exclusively in `CSE303`; accessing `CSE301`, `CSE302`, or `HCI401` results in `403 Forbidden`.

---

## 4. All 23 Personas & Credentials

All accounts use the standard demo password:
```text
GuardSLM2026!
```

The sign-in screen at `http://localhost:5173/login` includes a **1-click Persona Selector** to switch between accounts instantly.

| Username | Full Name | Email | Global Role | Course Memberships & Context |
| :--- | :--- | :--- | :---: | :--- |
| **`admin01`** | Alex Admin | `admin01@guardslm.local` | **Admin** | Institutional administrator (all courses & settings). |
| **`prof01`** | Dr. Mira Shah | `prof01@guardslm.local` | **Professor** | Course Professor in `CSE301` & `CSE303`. |
| **`prof02`** | Dr. Kabir Rao | `prof02@guardslm.local` | **Professor** | Course Professor in `CSE302` & `HCI401`. |
| **`ta01`** | Sam Lee | `ta01@guardslm.local` | **TA** | **TA** in `CSE301` \| **Student** in `CSE302`. |
| **`ta02`** | Noor Khan | `ta02@guardslm.local` | **TA** | **TA** in `CSE302` & `HCI401`. |
| **`ta03`** | Dev Patel | `ta03@guardslm.local` | **TA** | **TA** in `CSE303` \| **Student** in `HCI401`. |
| **`ta04`** | Elena Rostova | `ta04@guardslm.local` | **TA** | **TA** in `CSE303` \| **Student** in `CSE301`. |
| **`student01`** | Asha Mehta | `student01@guardslm.local` | **Student** | Enrolled in all 4 courses *(HCI401 Team Alpha)*. |
| **`student02`** | Rohan Das | `student02@guardslm.local` | **Student** | Enrolled in `CSE301`, `CSE302`, `CSE303`. |
| **`student03`** | Isha Roy | `student03@guardslm.local` | **Student** | Enrolled in `CSE301`, `HCI401` *(HCI401 Team Alpha)*. |
| **`student04`** | Vikram Sen | `student04@guardslm.local` | **Student** | Enrolled in `CSE302`, `CSE303`, `HCI401`. |
| **`student05`** | Tara Bose | `student05@guardslm.local` | **Student** | Enrolled in `CSE303`, `HCI401` *(HCI401 Team Beta)*. |
| **`student06`** | Arjun Nair | `student06@guardslm.local` | **Student** | Enrolled in all 4 courses *(HCI401 Team Beta)*. |
| **`student07`** | Priya Sharma | `student07@guardslm.local` | **Student** | Enrolled in `CSE301`, `HCI401` *(HCI401 Team Gamma)*. |
| **`student08`** | Marcus Chen | `student08@guardslm.local` | **Student** | Enrolled in all 4 courses. |
| **`student09`** | Fatima Zahra | `student09@guardslm.local` | **Student** | Enrolled in `CSE302`, `HCI401` *(HCI401 Team Delta)*. |
| **`student10`** | Lucas Silva | `student10@guardslm.local` | **Student** | Enrolled in `CSE301`, `CSE303`. |
| **`student11`** | Chloe Bennett | `student11@guardslm.local` | **Student** | Enrolled in `CSE302`, `CSE303`, `HCI401` *(HCI401 Team Gamma)*. |
| **`student12`** | David Kim | `student12@guardslm.local` | **Student** | Enrolled in `CSE301`, `CSE302` *(Approved Extensions)*. |
| **`student13`** | Ananya Iyer | `student13@guardslm.local` | **Student** | Enrolled in all 4 courses *(HCI401 Team Delta)*. |
| **`student14`** | Omar Farooq | `student14@guardslm.local` | **Student** | Enrolled **only in `CSE303`** (non-member of 301, 302, 401). |
| **`student15`** | Sofia Morales | `student15@guardslm.local` | **Student** | Enrolled in `CSE301`, `HCI401` *(HCI401 Team Gamma)*. |
| **`student16`** | Kevin Zhao | `student16@guardslm.local` | **Student** | Enrolled in `CSE302`, `CSE303`. |

---

## 5. Course Structure & Collaborative Groups

### The 4 Academic Courses
1. **`CSE301`: Database Management Systems**
   - *Instructor*: Dr. Mira Shah (`prof01`) \| *TA*: Sam Lee (`ta01`)
   - *Topics*: Relational algebra, SQL normalization, B+ tree indexing, transaction recovery.
2. **`CSE302`: Computer Networks**
   - *Instructor*: Dr. Kabir Rao (`prof02`) \| *TA*: Noor Khan (`ta02`)
   - *Topics*: OSI & TCP/IP stack, Wireshark packet capture, socket servers, routing simulation.
3. **`CSE303`: Operating Systems**
   - *Instructor*: Dr. Mira Shah (`prof01`) \| *TAs*: Dev Patel (`ta03`), Elena Rostova (`ta04`)
   - *Topics*: MLFQ & CFS schedulers, virtual memory & paging allocators, POSIX synchronization.
4. **`HCI401`: Human-Computer Interaction**
   - *Instructor*: Dr. Kabir Rao (`prof02`) \| *TA*: Noor Khan (`ta02`)
   - *Topics*: User-centered design, interactive prototyping, heuristic evaluation, WCAG compliance.

### Collaborative Student Groups in `HCI401`
For collaborative group assignments, students are organized into 4 isolated design teams:
- **Design Team Alpha**: Asha Mehta (`student01`), Isha Roy (`student03`)
- **Design Team Beta**: Tara Bose (`student05`), Arjun Nair (`student06`)
- **Design Team Gamma**: Priya Sharma (`student07`), Chloe Bennett (`student11`), Sofia Morales (`student15`)
- **Design Team Delta**: Fatima Zahra (`student09`), Ananya Iyer (`student13`)

---

## 6. Comprehensive LMS Features & Modules

### A. Course Workspace (`CourseDetail.jsx`)
Each course contains 6 dedicated tabs:
- **Overview**: Course description, instructor, TAs, syllabus highlights, and announcements.
- **Assignments**: Table of assessments with deadlines, point values, and late policies.
- **Quizzes**: Timed assessments with availability status, time limits, and attempt quotas.
- **Grades**: Student private grade view vs instructor class-wide gradebook.
- **Resources**: Student-accessible learning materials vs confidential staff-only files.
- **Policies**: Live institutional and course-specific policy cards.

### B. Assignment & Submission Lifecycle
- **13 Assignments** spanning active and past deadlines.
- **38 Pre-seeded Submissions** testing 6 operational states:
  - `draft`: Unsubmitted draft saved before the deadline.
  - `submitted`: Active submission awaiting grading.
  - `graded (draft)`: Graded internally by staff (`is_published = False`), hidden from student.
  - `graded (published)`: Graded and visible to the student.
  - `graded & locked`: Finalized assessment (`is_locked = True`); TAs cannot modify marks without admin intervention.
  - `extension_granted`: Approved academic extension allowing late submissions past deadline.
- **Group Submission Privacy**: In `HCI401`, team assignment drafts and feedback are strictly confidential to members of that specific group and course instructors.

### C. Gradebook & Privacy (FERPA Compliant)
- **Individual Grade Privacy**: Students calling grade endpoints only receive their own scores. Viewing peer marks returns `403 Forbidden`.
- **Staff Gradebook**: Professors and assigned TAs view class-wide marks and grading interfaces.
- **Grade History & Audit Overrides (`GradeHistory`)**: 6 regrading records track previous marks, new marks, grader identity, timestamp, and justification (e.g., *“Regraded query #3 after student clarification”*).
- **Final Grade Publishing Restriction**: Only the assigned Professor or Admin can publish final grades. TAs triggering grade publication are blocked (`403 Forbidden`).

### D. Quizzes & Timed Assessments
- **12 Quizzes** across 3 availability windows:
  - *Open & Active*: Currently available for student attempts.
  - *Upcoming*: Cannot be started before `open_date`.
  - *Expired / Closed*: Cannot be started after `close_date`.
- **Attempt Quotas**: Quizzes enforce limits (1, 2, or 3 max attempts). Starting an attempt when quota is exhausted is blocked.
- **Answer Key Release Control**: Answer keys remain confidential until `answer_release_date`. Students attempting to view locked keys receive `403 Forbidden`.
- **22 Pre-seeded Attempts**: Includes finished attempts, scores, and active `in_progress` attempts.

### E. Educational Resources & Staff Materials
- **28 Learning Resources** (7 per course):
  - **16 Student-Facing Resources**: Syllabi, lecture slides, lab guides, and reference sheets.
  - **12 Staff-Only Resources**: Confidential grading rubrics, master answer keys, and exam solution walkthroughs. Access by students returns `403 Forbidden`.

### F. Course Policies Engine
- **26 Policy Records** registered in the database and visible in the course UI:
  1. *Institutional Grade Privacy Policy* (FERPA)
  2. *Final Grade Publication & Locking*
  3. *Submission Deadlines & Extension Rules*
  4. *Course Membership & Role Authority*
  5. *Assessment Quotas & Timed Attempts*
  6. *Answer Key Release Schedule*
  7. *Staff-Only Educational Resources*
  8. *Collaborative Group Submission Privacy*

### G. Institutional Admin Console (`/admin`)
Restricted exclusively to `admin01`:
- **Admin Dashboard (`/admin`)**: Institutional KPIs and metrics.
- **User Management (`/admin/users`)**: Create, inspect, activate, or deactivate accounts.
- **Enrollment Management (`/admin/enrolments`)**: Manage course rosters and assign course roles.
- **Security Audit Logs (`/admin/logs`)**: Live audit trail tracking all authorization actions (`VIEW`, `SUBMIT`, `GRADE`, `PUBLISH`, `ADMIN_ACCESS`), actors, target resource IDs, and `ALLOW` / `BLOCK` outcomes.

---

## 7. The 100-Case RBAC Benchmark Dataset

The root folder **[`research_snapshots_100/`](./research_snapshots_100)** contains an evaluation dataset designed for Small Language Model (SLM) authorization guards:

- **100 Benchmark Cases (`TC01` through `TC100`)**: Spanning 10 core RBAC categories.
- **Balanced Decision Distribution**: **48 ALLOW / 52 BLOCK**.
- **Double-Blind Isolation**:
  - `slm_inputs/`: 100 self-contained prompt packages containing actor context, target action, policies, and pre-action accessibility tree snapshots. Ground truth decisions are strictly omitted.
  - `raw_snapshots/pages/`: 100 raw pre-action accessibility trees (YAML ariaSnapshots).
  - `raw_snapshots/policies/`: 100 raw policy page accessibility trees.
  - `manifest.csv`: Benchmark catalog with metadata and file references (labels excluded).
  - `evaluation_only/ground_truth.csv`: Isolated answer key with expected decisions (`ALLOW`/`BLOCK`), rationales, and route mappings.
  - `reports/`: Case inventory, coverage analysis, and 14-point capture validation report.
- **Accessibility Tree Representation**: 100% text-based YAML ariaSnapshots; zero image files.

---

## 8. Testing & Quality Assurance

### Automated Backend Test Suite
```bash
cd backend
python3 -m pytest app/tests -v
```

### Frontend Build Verification
```bash
cd frontend
npm run build
```

### Playwright Browser Test Suite
```bash
cd tests/playwright
npm install
npx playwright test
```

---

## 9. Project Directory Tree

```text
guard-slm-lms/
├── start_backend.sh                # Script to launch FastAPI server
├── start_frontend.sh               # Script to launch Vite dev server
├── .env.example                    # Environment template
├── .gitignore                      # Git exclusion rules
├── README.md                       # Master project documentation
│
├── backend/
│   ├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, etc.)
│   ├── guardslm.db                 # Auto-seeded SQLite database
│   └── app/
│       ├── main.py                 # FastAPI application & route registration
│       ├── database.py             # SQLAlchemy engine & sessionmaker
│       ├── models.py               # 14 Relational SQLAlchemy ORM models
│       ├── schemas.py              # Pydantic validation & response schemas
│       ├── auth.py                 # JWT authentication & bcrypt password hashing
│       ├── permissions.py          # Centralized RBAC authorization engine
│       ├── seed.py                 # Idempotent database seeder (23 users, 4 courses)
│       └── routes/                 # Modular REST API endpoints
│
├── frontend/
│   ├── package.json                # React 18, React Router v6, Tailwind CSS
│   ├── vite.config.js              # Vite bundler & proxy configuration
│   └── src/
│       ├── App.jsx                 # Route hierarchy with role guards
│       ├── api.js                  # Axios client with JWT interceptor
│       ├── context/AuthContext.jsx # Authentication session & state
│       ├── components/             # Reusable UI components (Navbar, Sidebar, etc.)
│       └── pages/                  # CourseDetail, Gradebook, Quizzes, Admin, etc.
│
├── research_snapshots_100/         # The 100-Case RBAC Benchmark Dataset
│   ├── slm_inputs/                 # 100 Self-contained Markdown prompt packages
│   ├── raw_snapshots/              # 100 Page & 100 Policy raw accessibility trees
│   ├── manifest.csv                # Benchmark catalog without labels
│   ├── evaluation_only/            # Isolated ground_truth.csv answer key
│   └── reports/                    # Inventory, coverage, and validation reports
│
├── docs/                           # System architecture & database schema docs
└── tests/                          # Playwright & pytest test suites
```

---

## 10. License & Citation

Developed for academic research into Small Language Model (SLM) authorization and contextual AI safety guards.
