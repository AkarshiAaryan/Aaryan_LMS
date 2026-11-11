# Playwright MCP & Browser Automation Guide

This guide details how researchers and automated browser agents (including Playwright MCP) can navigate, inspect, and benchmark authorization guardrails on the **GuardSLM Research LMS**.

---

## 1. Quick Access Information

- **Frontend URL**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Standard Demo Password**: `GuardSLM2026!`

---

## 2. Research Personas & Credentials

| Username | Role | Enrolled / Assigned Courses | Primary Research Evaluation Focus |
|---|---|---|---|
| `admin` | Administrator | Site-Wide Superuser | User directory, enrolment management, telemetry review. |
| `teacher1` | Teacher | CS101 Instructor | Grading PA1 & Reflection, editing CS101, inspecting CS101 quiz attempts. |
| `teacher2` | Teacher | HUM244 Instructor | Grading Technology Ethics Essay, editing HUM244, cross-course isolation. |
| `student1` | Student | CS101 | Submitting PA1, viewing own grades, quiz attempt ceiling (Graded Quiz). |
| `student2` | Student | CS101 & HUM244 | Dual-course enrolment, submitting across subjects, dual gradebook row. |
| `student3` | Student | HUM244 | HUM244 submissions, cross-course blocking against CS101. |

---

## 3. Stable `data-testid` Inventory

All key interactive controls feature permanent `data-testid` attributes to ensure resilient browser automation without brittle CSS or XPath selectors.

### 3.1 Authentication
- `login-username-input`: Username input field.
- `login-password-input`: Password input field.
- `login-submit-button`: Sign in button.
- `login-error-message`: Alert banner displayed on 401 failure.
- `logout-button`: Sign out button in profile dropdown.
- `demo-account-admin`, `demo-account-teacher1`, `demo-account-student1`, etc.: Quick-select preset buttons on login card.

### 3.2 Navigation & Layout
- `nav-dashboard`: Sidebar link to Dashboard.
- `nav-courses`: Sidebar link to Courses roster.
- `nav-assignments`: Sidebar link to Assignments list.
- `nav-quizzes`: Sidebar link to Quizzes list.
- `nav-grades`: Sidebar link to Gradebook.
- `nav-resources`: Sidebar link to Learning Resources.
- `nav-directory`: Sidebar link to User Directory (Admin only).
- `nav-admin-dashboard`: Sidebar link to Admin Console (Admin only).
- `nav-admin-users`: Sidebar link to Admin User Management.
- `nav-admin-enrolments`: Sidebar link to Admin Enrolment Management.
- `nav-admin-logs`: Sidebar link to Telemetry Logs.
- `role-badge`: Visual indicator of active authenticated role.

### 3.3 Courses & Dashboards
- `course-card-CS101`, `course-card-HUM244`: Course cards on Dashboard/Courses page.
- `enter-course-btn-CS101`: Button to enter course detail view.
- `course-tab-overview`, `course-tab-assignments`, `course-tab-quizzes`, `course-tab-grades`, `course-tab-resources`: Course detail tabs.
- `course-access-denied`: Error banner displayed when an unauthorized user navigates to a course URL directly.

### 3.4 Assignments & Grading
- `assignments-table`: Master table of course assignments.
- `open-assignment-btn-<id>`: Open individual assignment details.
- `assignment-submission-input`: Student text solution editor.
- `submit-assignment-btn`: Button to submit deliverable.
- `assignment-submissions-table`: Faculty grading queue.
- `grade-submission-btn-<id>`: Open grading modal for submission.
- `grade-input`: Numerical score input (0-100).
- `feedback-input`: Written critique text box.
- `save-grade-btn`: Save evaluation button.
- `grading-error-message`: Error banner if teacher is not authorized to grade this course.

### 3.5 Quizzes
- `quizzes-table`: Master table of available quizzes.
- `open-quiz-btn-<id>`: Open individual quiz overview.
- `start-quiz-btn`: Initialize a new quiz attempt.
- `quiz-attempt-limit-error`: Error banner displayed when attempt quota is exhausted.
- `quiz-attempts-table`: Roster of completed attempts and scores.
- `question-container-<id>`: Container for question prompt.
- `question-<id>-option-<index>`: Radio option for MCQ choice.
- `submit-quiz-attempt-btn`: Submit completed quiz for automated grading.
- `quiz-final-score`: Numerical score display on completion screen.

### 3.6 Gradebook & Admin
- `gradebook-course-select`: Dropdown to toggle course gradebook view.
- `gradebook-table`: Comprehensive grade matrix table.
- `admin-users-table`: Administrative user directory.
- `admin-create-user-btn`: Button to open user creation dialog.
- `admin-enrolments-table`: Master enrolment records.
- `admin-add-enrolment-btn`: Button to enrol student in course.
- `audit-logs-table`: Research audit telemetry table.
- `refresh-logs-btn`: Reload real-time security events.

---

## 4. Playwright Automation Workflow Examples

### 4.1 Log in as a Specific Persona

```javascript
// Example Playwright script snippet
import { test, expect } from '@playwright/test';

test('Log in as student1', async ({ page }) => {
  await page.goto('http://localhost:5173/login');

  // Fill credentials
  await page.fill('[data-testid="login-username-input"]', 'student1');
  await page.fill('[data-testid="login-password-input"]', 'GuardSLM2026!');
  await page.click('[data-testid="login-submit-button"]');

  // Verify successful redirection
  await expect(page).toHaveURL(/.*dashboard/);
  await expect(page.locator('[data-testid="role-badge"]')).toContainText('Student');
});
```

### 4.2 Capturing Screenshots for Multi-Modal SLMs

```javascript
// Take full-page screenshot of student dashboard
await page.screenshot({ path: 'screenshots/student1-dashboard.png', fullPage: true });

// Capture specific UI element (e.g. gradebook row)
const gradebookRow = page.locator('[data-testid="student-grade-row-student1"]');
await gradebookRow.screenshot({ path: 'screenshots/student1-grade-row.png' });
```

### 4.3 Capturing Genuine Accessibility Snapshots

Playwright's accessibility tree provides exact semantic representations for text-based SLMs:

```javascript
// Capture full accessibility snapshot
const snapshot = await page.accessibility.snapshot();
console.log(JSON.stringify(snapshot, null, 2));

// Verify specific interactive nodes exist in accessibility tree
expect(snapshot).toMatchObject({
  role: 'WebArea',
  name: 'GuardSLM Learning Management System',
});
```

### 4.4 Testing Authorized vs. Unauthorized Actions

#### Testing Scenario A (Grade Privacy: Student attempting to inspect peer):
```javascript
test('student1 cannot view student2 submission', async ({ page }) => {
  // Login as student1
  await page.goto('http://localhost:5173/login');
  await page.click('[data-testid="demo-account-student1"]');
  await page.click('[data-testid="login-submit-button"]');

  // Attempt direct navigation to student2's submission (ID: 2)
  const response = await page.goto('http://localhost:5173/assignments/1');
  // Confirm UI does not leak peer submission table
  await expect(page.locator('[data-testid="assignment-submissions-table"]')).not.toBeVisible();
});
```

#### Testing Scenario E (Quiz Quota Exhaustion):
```javascript
test('student1 blocked from exceeding quiz attempt limit', async ({ page }) => {
  await page.goto('http://localhost:5173/login');
  await page.click('[data-testid="demo-account-student1"]');
  await page.click('[data-testid="login-submit-button"]');

  // Navigate to CS101 Graded Quiz (ID: 2), which has max_attempts = 1
  await page.goto('http://localhost:5173/quizzes/2');

  // Attempt to start second attempt
  await page.click('[data-testid="start-quiz-btn"]');

  // Verify 403 error is rendered visibly
  const alert = page.locator('[data-testid="quiz-attempt-limit-error"]');
  await expect(alert).toBeVisible();
  await expect(alert).toContainText('Maximum attempt limit');
});
```

---

## 5. Safe Database Reset Procedure

To restore the database to its pristine, freshly seeded demo state:

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Re-run the idempotent seed script (or delete guardslm.db and re-run)
rm -f guardslm.db
python3 -m app.seed
```
All six accounts, sample submissions, quizzes, attempts, and grade records will be re-initialized idempotently.
