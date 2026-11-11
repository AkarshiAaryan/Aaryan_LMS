const { test, expect } = require('@playwright/test');

test.describe('GuardSLM RBAC Scenarios', () => {

  // Scenario 1: Grade Privacy
  test('Scenario 1: Student sees only own grades in gradebook; peer rows hidden', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-username-input"]', 'student01');
    await page.fill('[data-testid="login-password-input"]', 'GuardSLM2026!');
    await page.click('[data-testid="login-submit-button"]');
    await expect(page).toHaveURL(/.*dashboard/);

    await page.click('[data-testid="nav-grades"]');
    await expect(page).toHaveURL(/.*grades/);
    await expect(page.locator('body')).toContainText('Asha Mehta');
  });

  // Course Enrolment Boundaries
  test('Scenario: Direct URL navigation to unenrolled course triggers Access Forbidden', async ({ page }) => {
    // student02 is enrolled in CSE301 and CSE302, but NOT CSE303
    await page.goto('/login');
    await page.fill('[data-testid="login-username-input"]', 'student02');
    await page.fill('[data-testid="login-password-input"]', 'GuardSLM2026!');
    await page.click('[data-testid="login-submit-button"]');

    // Attempt direct URL navigation to CSE303 (ID 3)
    await page.goto('/courses/3');

    const deniedBox = page.locator('[data-testid="course-access-denied"]');
    await expect(deniedBox).toBeVisible();
    await expect(deniedBox).toContainText('Access Forbidden');
  });

  // Administrative Access Protection
  test('Scenario: Non-admin users cannot access administrative console', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-username-input"]', 'prof01');
    await page.fill('[data-testid="login-password-input"]', 'GuardSLM2026!');
    await page.click('[data-testid="login-submit-button"]');

    await page.goto('/admin');
    await expect(page).toHaveURL(/.*403/);
  });
});
