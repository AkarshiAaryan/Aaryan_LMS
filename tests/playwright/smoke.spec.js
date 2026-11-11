const { test, expect } = require('@playwright/test');

const DEMO_PERSONAS = [
  { username: 'admin01', role: 'admin', expectedName: 'Alex Admin' },
  { username: 'prof01', role: 'professor', expectedName: 'Dr Mira Shah' },
  { username: 'prof02', role: 'professor', expectedName: 'Dr Kabir Rao' },
  { username: 'ta01', role: 'ta', expectedName: 'Sam Lee' },
  { username: 'ta02', role: 'ta', expectedName: 'Noor Khan' },
  { username: 'ta03', role: 'ta', expectedName: 'Dev Patel' },
  { username: 'student01', role: 'student', expectedName: 'Asha Mehta' },
  { username: 'student02', role: 'student', expectedName: 'Rohan Das' },
];

test.describe('GuardSLM LMS Smoke Tests', () => {

  test('Login page renders correctly with demo account selectors', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText('GuardSLM LMS');
    await expect(page.locator('[data-testid="login-username-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-password-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-submit-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="demo-account-admin01"]')).toBeVisible();
    await expect(page.locator('[data-testid="demo-account-student01"]')).toBeVisible();
  });

  test('Invalid credentials trigger accessible error banner', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-username-input"]', 'student01');
    await page.fill('[data-testid="login-password-input"]', 'WrongPassword123!');
    await page.click('[data-testid="login-submit-button"]');

    const errorAlert = page.locator('[data-testid="login-error-message"]');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText('Incorrect username or password');
  });

  for (const persona of DEMO_PERSONAS) {
    test(`Sign in as ${persona.username} (${persona.role})`, async ({ page }) => {
      await page.goto('/login');
      await page.fill('[data-testid="login-username-input"]', persona.username);
      await page.fill('[data-testid="login-password-input"]', 'GuardSLM2026!');
      await page.click('[data-testid="login-submit-button"]');

      // Verify redirection to dashboard
      await expect(page).toHaveURL(/.*dashboard/);
      await expect(page.locator('[data-testid="role-badge"]')).toBeVisible();
      await expect(page.locator('[data-testid="user-full-name"]')).toContainText(persona.expectedName);

      // Verify role-based sidebar items
      if (persona.role === 'admin') {
        await expect(page.locator('[data-testid="nav-admin-dashboard"]')).toBeVisible();
        await expect(page.locator('[data-testid="nav-admin-users"]')).toBeVisible();
      } else {
        await expect(page.locator('[data-testid="nav-admin-dashboard"]')).not.toBeVisible();
      }

      // Test Logout
      await page.click('[data-testid="user-profile-menu-button"]');
      await page.click('[data-testid="logout-button"]');
      await expect(page).toHaveURL(/.*login/);
    });
  }
});
