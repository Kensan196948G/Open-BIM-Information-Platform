import { test, expect } from "@playwright/test";

// Helper: authenticate and store session in browser
async function authenticate(page: any) {
  const apiBase = process.env.VITE_API_BASE_URL || "http://localhost:8000";

  // Login via API to get token
  const loginRes = await page.request.post(`${apiBase}/api/v1/auth/login`, {
    form: { username: "e2e@test.example.com", password: "TestPass123!" },
  });
  const { access_token } = await loginRes.json();
  const meRes = await page.request.get(`${apiBase}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  const me = await meRes.json();

  // Set token in localStorage
  await page.goto("/login");
  await page.evaluate(
    ({ token, user }) => {
      localStorage.setItem("access_token", token);
      localStorage.setItem(
        "bim-auth",
        JSON.stringify({ state: { token, user }, version: 0 }),
      );
    },
    { token: access_token, user: me },
  );

  await page.goto("/dashboard");
}

test.describe("Authenticated navigation", () => {
  test.skip(
    !process.env.VITE_API_BASE_URL,
    "Requires running backend (set VITE_API_BASE_URL)",
  );

  test("dashboard shows stat cards", async ({ page }) => {
    await authenticate(page);
    // h1 heading on the dashboard page
    await expect(
      page.getByRole("heading", { name: "ダッシュボード" }),
    ).toBeVisible();
    // KPI cards in the redesigned dashboard — use .first() to avoid strict-mode violations
    await expect(page.getByText("情報コンテナ").first()).toBeVisible();
    await expect(page.getByText("承認待ち").first()).toBeVisible();
  });

  test("sidebar navigation works", async ({ page }) => {
    await authenticate(page);
    // Use the sidebar link role to avoid matching the page heading
    await page.getByRole("link", { name: "プロジェクト" }).click();
    await expect(page).toHaveURL(/\/projects/);
    // Redesigned ProjectsPage uses "新規プロジェクト" button text
    await expect(
      page.getByRole("button", { name: "新規プロジェクト" }),
    ).toBeVisible();
  });

  test("logout clears session and redirects", async ({ page }) => {
    await authenticate(page);
    // Redesigned Layout uses icon-only button with title="ログアウト"
    await page.locator('[title="ログアウト"]').click();
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Static routing", () => {
  test("/health proxies the backend health contract", async ({ request }) => {
    test.skip(
      !process.env.VITE_API_BASE_URL,
      "Requires running backend (set VITE_API_BASE_URL)",
    );

    const response = await request.get("/health");
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("application/json");
    expect(await response.json()).toMatchObject({
      status: "ok",
      database: "ok",
    });
  });

  test("/ redirects to /dashboard or /login", async ({ page }) => {
    await page.goto("/");
    // Wait for client-side redirect to settle (unauthenticated → /login)
    await page.waitForURL(/\/(dashboard|login)/, { timeout: 5000 });
    expect(page.url()).toMatch(/\/(dashboard|login)/);
  });

  test("login page is accessible without auth", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("form")).toBeVisible();
  });
});
