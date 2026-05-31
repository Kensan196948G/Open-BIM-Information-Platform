import { test, expect } from "@playwright/test";

// Helper: authenticate and store session in browser
async function authenticate(page: any, baseURL: string) {
  const apiBase = process.env.VITE_API_BASE_URL || "http://localhost:8000";

  // Register test user via API
  await page.request.post(`${apiBase}/api/v1/auth/register`, {
    data: {
      email: "e2e@test.example.com",
      username: "e2euser",
      full_name: "E2E Test User",
      password: "testpass123",
    },
  });

  // Login via API to get token
  const loginRes = await page.request.post(`${apiBase}/api/v1/auth/login`, {
    form: { username: "e2e@test.example.com", password: "testpass123" },
  });
  const { access_token } = await loginRes.json();

  // Set token in localStorage
  await page.goto("/login");
  await page.evaluate((token: string) => {
    localStorage.setItem("access_token", token);
    // Set zustand persisted auth
    localStorage.setItem(
      "bim-auth",
      JSON.stringify({
        state: {
          token,
          user: {
            id: "test",
            email: "e2e@test.example.com",
            username: "e2euser",
            full_name: "E2E Test User",
            is_active: true,
            is_platform_admin: false,
          },
        },
        version: 0,
      })
    );
  }, access_token);

  await page.goto("/dashboard");
}

test.describe("Authenticated navigation", () => {
  test.skip(
    !process.env.VITE_API_BASE_URL,
    "Requires running backend (set VITE_API_BASE_URL)"
  );

  test("dashboard shows stat cards", async ({ page }) => {
    await authenticate(page, process.env.BASE_URL || "http://localhost:5173");
    await expect(page.getByText("ダッシュボード")).toBeVisible();
    await expect(page.getByText("プロジェクト数")).toBeVisible();
    await expect(page.getByText("情報コンテナ")).toBeVisible();
  });

  test("sidebar navigation works", async ({ page }) => {
    await authenticate(page, process.env.BASE_URL || "http://localhost:5173");
    await page.getByText("プロジェクト").click();
    await expect(page).toHaveURL(/\/projects/);
    await expect(page.getByText("新規作成")).toBeVisible();
  });

  test("logout clears session and redirects", async ({ page }) => {
    await authenticate(page, process.env.BASE_URL || "http://localhost:5173");
    await page.getByText("ログアウト").click();
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Static routing", () => {
  test("/ redirects to /dashboard or /login", async ({ page }) => {
    await page.goto("/");
    const url = page.url();
    expect(url).toMatch(/\/(dashboard|login)/);
  });

  test("login page is accessible without auth", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("form")).toBeVisible();
  });
});
