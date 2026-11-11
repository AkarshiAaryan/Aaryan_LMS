# GuardSLM Academic LMS & Benchmark V2 (2,000 Cases)

A high-fidelity academic Learning Management System (LMS) web application and evaluation testbed engineered specifically for evaluating **Small Language Models (SLMs)** and AI safety guards on contextual, policy-driven **Role-Based Access Control (RBAC)**.

The platform simulates realistic higher-education workflows involving students, teaching assistants, professors, and institutional administrators across course navigation, assignment lifecycles, FERPA-compliant grade privacy, timed assessments, confidential staff resources, discussion forums, learning modules, peer reviews, attendance recording, and security audit telemetry.

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
To clear any state modifications and reset the database to the pristine benchmark state (54 personas, 4 departments, 8 sections):
```bash
cd backend
rm -f guardslm.db
python3 -m app.seed
```

---

## 2. GuardSLM Benchmark V2 (2,000 Cases)

The **`research_snapshots_2000/`** directory contains the full 2,000-case evaluation dataset designed to evaluate SLMs as contextual authorization guards for autonomous browser agents.

### Key Dataset Metrics
- **2,000 Benchmark Cases (`CASE-0001` through `CASE-2000`)**: Spanning 13 scenario families.
- **1,000 Controlled Contrast Pairs**: Strict pairwise control varying exactly one dimension: Identity, Scope, Ownership, Lifecycle, or Time.
- **Decision Class Balance**: **958 ALLOW (47.9%) / 1,042 BLOCK (52.1%)**.
- **152 Multi-Step Attack Sequences**: Multi-action chains testing escalation and session state tracking.
- **77 Adversarial Prompt Injections**: In-context jailbreak and prompt override attacks.
- **54 Realistic Personas**: Spanning 4 academic departments (`CS`, `EE`, `HCI`, `DS`).
- **Strict Double-Blind Isolation**:
  - `slm_inputs/`: 2,000 self-contained prompt packages (Markdown) containing actor context, target action proposal, grounding policy text, and pre-action accessibility tree (`ariaSnapshot` YAML). **Zero ground-truth labels, decisions, or rationales are leaked.**
  - `raw_snapshots/pages/`: 2,000 raw pre-action accessibility trees.
  - `raw_snapshots/policies/`: 2,000 raw policy page accessibility trees.
  - `manifest.csv`: Benchmark catalog with metadata, family codes, and contrast pair linkages (labels excluded).
  - `evaluation_only/ground_truth.csv`: Isolated answer key with expected decisions (`ALLOW`/`BLOCK`), rationales, failure modes, and route mappings.
  - `reports/`: `coverage_report.md`, `contrast_pair_analysis.md`, and `distribution_stats.json`.
  - `slm_inputs.zip` & `research_snapshots_2000.zip`: Portable distribution archives.

### Benchmark CLI (`tools.benchmark.cli`)
A unified CLI tool manages the generation, validation, and statistical analysis of the benchmark:

```bash
# Display dataset distribution and metrics
python3 -m tools.benchmark.cli stats

# Execute full 20-point automated validation suite
python3 -m tools.benchmark.cli validate

# Re-generate the 2,000-case dataset
python3 -m tools.benchmark.cli generate --output-dir research_snapshots_2000
```

---

## 3. System Architecture & Tech Stack

```text
┌────────────────────────────────────────────────────────┐
│             React 18 SPA (Vite + Tailwind)             │
│        Context-aware UI with 1-click Persona Login     │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP / JSON (JWT Bearer Token)
                           │ X-Simulation-Time Header (Temporal Context)
                           ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend (Python 3.12)              │
│       Centralized Permissions Engine (permissions.py)  │
│        Deterministic Simulation Time (clock.py)        │
└──────────────┬───────────────────────────┬─────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  SQLite / SQLAlchemy ORM │  │ Real-time Activity Telemetry│
│   (24 relational tables) │  │  (ALLOW vs BLOCK Audits)  │
└──────────────────────────┘  └──────────────────────────┘
```

- **Backend**: FastAPI, SQLAlchemy ORM, SQLite (`guardslm.db`), Pydantic v2 validation, python-jose (JWT auth), passlib/bcrypt.
- **Frontend**: React 18, Vite, React Router v6, Axios, Tailwind CSS, Lucide React icons.
- **Testing & Benchmark**: Playwright MCP, Pytest test suites (63 tests), accessibility tree ariaSnapshots.
- **Simulation Time**: Header-driven simulation time (`X-Simulation-Time: YYYY-MM-DDTHH:MM:SSZ`) enables deterministic testing of time-based access policies without altering the host OS clock.

---

## 4. Dual-Layer Contextual RBAC

The LMS enforces authorization based on a **two-layer identity model**:
1. **Global Account Role**: Broad classification (`admin`, `professor`, `ta`, `student`).
2. **Course-Scoped Role**: Concrete privilege determined by enrollment in a specific course (`instructor`, `ta`, `student`, `auditor`).
3. **Enrollment Status**: `active`, `suspended` (blocked from interactions), or `revoked` (expelled/withdrawn).

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

## 5. Personas & Credentials (54 Users)

All accounts use the standard demo password:
```text
GuardSLM2026!
```

The sign-in screen at `http://localhost:5173/login` includes a **1-click Persona Selector** to switch between accounts instantly.

| Role | Count | Usernames | Responsibilities |
| :--- | :---: | :--- | :--- |
| **Admin** | 2 | `admin01`, `admin02` | Institutional administrators; unrestricted course and audit access. |
| **Professor** | 4 | `prof01` - `prof04` | Department chairs and course directors across CS, EE, HCI, DS. |
| **Teaching Assistant** | 8 | `ta01` - `ta08` | Course staff with section-specific grading and moderation permissions. |
| **Student** | 40 | `student01` - `student40` | Learners across sections, groups, and enrollment statuses. |

---

## 6. Comprehensive LMS Domain Modules

1. **Course Workspace & Navigation (`CourseDetail.jsx`)**: Syllabus, announcements, and course tabs.
2. **Assignments & Submissions (`assignments.py`, `submissions.py`)**: Due dates, late submission policies, grading workflows, draft/published states, and group work confidentiality.
3. **FERPA Gradebook (`submissions.py`, `Gradebook.jsx`)**: Strict student grade isolation; grade override audit trail.
4. **Timed Assessments & Quizzes (`quizzes.py`)**: Time-window scheduling, attempt quotas, and answer-key masking.
5. **Discussion Forums (`discussions.py`)**: Public class discussions, confidential student-staff private threads, locked thread moderation, and team-scoped discussions.
6. **Learning Modules & Lessons (`modules.py`)**: Chronologically scheduled module unlocks (`unlock_date`), lesson content visibility, and draft module controls.
7. **Course Files & Storage Permissions (`files.py`)**: Multi-tiered file access (`public`, `students`, `staff_only`, `private`, `group_only`), time-based expiration dates, and archival status.
8. **Double-Blind Peer Reviews & Grade Appeals (`peer_reviews.py`)**: Anonymous student-to-student peer assessment (author sees `Anonymous Reviewer` with redacted reviewer ID; staff sees full attribution); student grade appeal workflow with professor resolution.
9. **Section Attendance Records (`attendance.py`)**: Section-scoped attendance tracking by TAs/professors; student excuse request workflow; instructor session locking.
10. **Institutional Admin & Security Auditing (`/admin`)**: User provisioning, roster management, and live audit telemetry of all access decisions (`ALLOW` vs `BLOCK`).

---

## 7. Baseline Preservation

To ensure backward compatibility and historical reproducibility:
- **Pilot Dataset**: Preserved in `research_snapshots/` (20 verified cases).
- **100-Case Dataset**: Preserved in `research_snapshots_100/` (100 verified cases, 48 ALLOW / 52 BLOCK).
- **Benchmark V2 Dataset**: Generated in `research_snapshots_2000/` (2,000 verified cases, 958 ALLOW / 1,042 BLOCK).

---

## 8. Testing & Quality Assurance

### Automated Backend Test Suite (Pytest)
```bash
cd backend
python3 -m pytest app/tests -v
```
*Current test suite: **63 passed, 0 failed** (includes authentication, scenarios, security regressions, and new domain modules).*

### Frontend Build Verification
```bash
cd frontend
npm run build
```

### Benchmark V2 20-Point Compliance Verification
```bash
python3 -m tools.benchmark.cli validate
```
*Current verification status: **20/20 checks passed perfectly**.*

---

## 9. Project Directory Tree

```text
guard-slm-lms/
├── start_backend.sh                # Script to launch FastAPI server
├── start_frontend.sh               # Script to launch Vite dev server
├── README.md                       # Master project documentation
│
├── backend/
│   ├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, etc.)
│   ├── guardslm.db                 # Auto-seeded SQLite database (24 tables, 54 users)
│   └── app/
│       ├── main.py                 # FastAPI application & route registration
│       ├── database.py             # SQLAlchemy engine & sessionmaker
│       ├── clock.py                # Deterministic Simulation Time service
│       ├── models.py               # 24 Relational SQLAlchemy ORM models
│       ├── schemas.py              # Pydantic validation & response schemas
│       ├── auth.py                 # JWT authentication & bcrypt password hashing
│       ├── permissions.py          # Centralized RBAC authorization engine
│       ├── seed.py                 # Database seeder (54 users, 4 courses, 8 sections)
│       ├── routes/                 # Modular REST API endpoints
│       └── tests/                  # 63 Automated unit and regression tests
│
├── frontend/
│   ├── package.json                # React 18, React Router v6, Tailwind CSS
│   ├── vite.config.js              # Vite bundler & proxy configuration
│   └── src/                        # React UI components and pages
│
├── tools/benchmark/                # Benchmark V2 declarative generation infrastructure
│   ├── catalogs/                   # Grounding policies, personas, and families
│   ├── generation/                 # Case generator & deduplication engine
│   ├── schemas/                    # BenchmarkCase dataclass
│   ├── capture/                    # Accessibility tree capture & packaging
│   ├── validation/                 # 20-Point automated validator
│   └── cli.py                      # CLI entry point (generate, validate, stats)
│
├── research_snapshots_2000/         # GuardSLM Benchmark V2 Dataset (2,000 cases)
│   ├── slm_inputs/                 # 2,000 Double-blind Markdown prompt packages
│   ├── raw_snapshots/              # 2,000 Page & 2,000 Policy raw accessibility trees
│   ├── manifest.csv                # Benchmark catalog without labels
│   ├── evaluation_only/            # Isolated ground_truth.csv answer key
│   ├── reports/                    # Inventory, coverage, and validation reports
│   └── *.zip                       # Portable zip archives of inputs and dataset
│
├── research_snapshots_100/         # Immutable 100-case baseline dataset
├── research_snapshots/             # Immutable 20-case pilot dataset
└── docs/                           # Architecture, database schema, & overhaul reports
```

---

## 10. License & Citation

Developed for academic research into Small Language Model (SLM) authorization guards and contextual AI safety.
