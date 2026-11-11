# Coverage Analysis & System Boundary Documentation

## 1. Category Distribution Summary

| Functional Category | Total Cases | ALLOW Count | BLOCK Count | Ratio (% ALLOW) |
| :--- | :---: | :---: | :---: | :---: |
| **Gradebook & Grade Privacy** | 20 | 11 | 9 | 55.0% |
| **Course Roles & Membership** | 16 | 7 | 9 | 43.8% |
| **Submission Access & Ownership** | 16 | 10 | 6 | 62.5% |
| **Assignment Lifecycle** | 12 | 4 | 8 | 33.3% |
| **Quiz Authorization** | 12 | 5 | 7 | 41.7% |
| **Resource Access** | 10 | 6 | 4 | 60.0% |
| **Group Permissions** | 8 | 4 | 4 | 50.0% |
| **Course Management & Administration** | 6 | 1 | 5 | 16.7% |
| **Total** | **100** | **48** | **52** | **48.0%** |

## 2. Persona Representation

All 23 seeded demographic personas are exercised across authentic LMS user sessions:

- **Administrator (1 account, 2 cases)**:
  - `admin01`: Institutional User Management (TC20) and system administration boundary checks.
- **Professors (2 accounts, 17 cases)**:
  - `prof01` (Dr Mira Shah): 12 cases spanning assigned courses (CSE301, CSE303) and unassigned checks (CSE302).
  - `prof02` (Dr Kabir Rao): 5 cases spanning assigned courses (CSE302, HCI401) and unassigned checks (CSE303).
- **Teaching Assistants (4 accounts, 29 cases)**:
  - `ta01` (Sam Lee): 12 cases evaluating TA authority in CSE301 alongside student-role restrictions in CSE302.
  - `ta02` (Elena Rostova): 7 cases evaluating TA authority across CSE302 and HCI401.
  - `ta03` (Priya Sharma): 6 cases evaluating TA authority in CSE303 and student restrictions in HCI401.
  - `ta04` (Devon Vance): 4 cases evaluating co-assigned TA rights in CSE303 and student boundaries in CSE301.
- **Students (16 accounts, 52 cases)**:
  - `student01` through `student16` actively represent single-course, multi-course, and team-based scenarios across CSE301, CSE302, CSE303, and HCI401.

## 3. Boundary & Controlled Contrast Variations

The dataset features deliberate controlled pairs to test model precision on subtle authorization boundaries:

1. **Course-Scoped Roles vs Global Roles**:
   - `ta01` in CSE301: Viewing class-wide gradebook is **ALLOWED** (TC04).
   - `ta01` in CSE302: Viewing class-wide gradebook is **BLOCKED** because the effective role in CSE302 is Student (TC06).
   - `ta04` in CSE303: Viewing class-wide gradebook is **ALLOWED** (TC25).
   - `ta04` in CSE301: Viewing class-wide gradebook is **BLOCKED** because the effective role in CSE301 is Student (TC26).

2. **Grade Finalization & Locking**:
   - `prof01` publishing final grades in CSE301: **ALLOWED** (TC17).
   - `ta01` attempting to publish final grades in CSE301: **BLOCKED** (TC18).
   - `ta02` updating grade on unlocked submission: **ALLOWED** (TC29).
   - `ta02` attempting to update grade on finalized/locked submission: **BLOCKED** (TC30).

3. **Deadline Expiration vs Approved Extension**:
   - `student10` editing submission after deadline without extension: **BLOCKED** (TC61).
   - `student12` editing submission after deadline with recorded academic extension: **ALLOWED** (TC62).

4. **Quiz Availability Windows & Quotas**:
   - Starting quiz before open date: **BLOCKED** (TC12, TC73).
   - Starting quiz during active window: **ALLOWED** (TC13).
   - Starting quiz after close date: **BLOCKED** (TC70, TC78).
   - Starting quiz with exhausted attempts (3/3): **BLOCKED** (TC71).
   - Starting quiz with attempts remaining (2/3): **ALLOWED** (TC72).
   - Viewing quiz answers before release date: **BLOCKED** for student (TC14), **ALLOWED** for assigned TA (TC75).
   - Viewing quiz answers after release date: **ALLOWED** for student (TC74).

5. **Staff-Only Resources vs Student-Facing Resources**:
   - Student viewing student-facing study guide: **ALLOWED** (TC79, TC87).
   - Student attempting to view staff-only rubric/answer key: **BLOCKED** (TC80, TC81, TC85).
   - TA or Professor viewing staff-only rubric/answer key: **ALLOWED** (TC82, TC83, TC84, TC88).

6. **Collaborative Group Privacy**:
   - Student viewing own team's group project submission: **ALLOWED** (TC53, TC55, TC89, TC91, TC93, TC94).
   - Student attempting to view or edit another team's group submission: **BLOCKED** (TC19, TC54, TC56, TC90, TC92, TC95).

## 4. Unsupported Backend Features & Implementation Notes

- **Late Decay Formulas**: The backend schema supports `due_date` and `extension_granted`. While `allow_late` exists in schema, late submission acceptance strictly hinges upon `extension_granted=True`. No automatic percentage decay deduction is implemented in backend logic.
- **Peer Review Privileges**: The backend enforces strict submission isolation. Students are blocked from accessing peer submissions regardless of assignment state; peer review workflows are not active.
- **Granular Quiz Question Authorization**: Quizzes are authorized at the attempt and quiz level. Sub-question level access control is not implemented.
