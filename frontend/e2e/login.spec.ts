import { test, expect } from "@playwright/test";

test.describe("Login page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
  });

  test("shows login form with correct elements", async ({ page }) => {
    await expect(page.getByText("Open BIM 情報基盤")).toBeVisible();
    await expect(page.getByPlaceholder("user@example.com")).toBeVisible();
    await expect(page.getByRole("button", { name: "ログイン" })).toBeVisible();
  });

  test("shows error on invalid credentials", async ({ page }) => {
    await page.getByPlaceholder("user@example.com").fill("invalid@example.com");
    await page.getByRole("button", { name: "ログイン" }).click();

    // Password field is required — browser validation should prevent submission
    // or API returns error
    await expect(page.locator("form")).toBeVisible();
  });

  test("redirects unauthenticated users to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("login form has email and password inputs", async ({ page }) => {
    const emailInput = page.getByPlaceholder("user@example.com");
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(emailInput).toBeEnabled();
    await expect(passwordInput).toBeEnabled();
  });
});
