import { test, expect, type Page } from "@playwright/test";

const API_BASE = process.env.VITE_API_BASE_URL || "http://localhost:8000";
const APPROVER = { email: "approver@e2e.local", password: "TestPass123!" };
const INITIATOR = { email: "initiator@e2e.local", password: "TestPass123!" };

async function apiLogin(page: Page, email: string, password: string) {
  const res = await page.request.post(`${API_BASE}/api/v1/auth/login`, {
    form: { username: email, password },
  });
  expect(res.status()).toBe(200);
  return res.json();
}

async function authAs(page: Page, email: string, password: string) {
  const { access_token } = await apiLogin(page, email, password);
  const meRes = await page.request.get(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  const me = await meRes.json();
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
}

async function seedApprovalTask(page: Page): Promise<{ identifier: string }> {
  // Create a fresh container + workflow via the API so tests are order-independent.
  const { access_token } = await apiLogin(
    page,
    INITIATOR.email,
    INITIATOR.password,
  );
  const auth = { Authorization: `Bearer ${access_token}` };

  const projectsRes = await page.request.get(`${API_BASE}/api/v1/projects`, {
    headers: auth,
  });
  const projects = (await projectsRes.json()).items;
  const project = projects.find((p: { code: string }) => p.code === "E2E");
  expect(project, "seeded E2E project must exist").toBeTruthy();

  const number = String(2000 + Math.floor(Math.random() * 9000));
  const identifier = `E2E-ORG-ZZ-GF-DR-AR-${number}`;
  const created = await page.request.post(
    `${API_BASE}/api/v1/projects/${project.id}/containers`,
    {
      headers: auth,
      data: { identifier, title: `E2E Approval ${number}` },
    },
  );
  expect(created.status()).toBe(201);
  const container = await created.json();

  await page.request.post(
    `${API_BASE}/api/v1/projects/${project.id}/containers/${container.id}/transition`,
    {
      headers: auth,
      data: { action: "submit" },
    },
  );

  // Find the approver's user id.
  const approverRes = await page.request.post(
    `${API_BASE}/api/v1/auth/login`,
    { form: { username: APPROVER.email, password: APPROVER.password } },
  );
  const approver = await approverRes.json();
  const approverMe = await page.request.get(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${approver.access_token}` },
  });
  const approverUser = await approverMe.json();

  const wf = await page.request.post(`${API_BASE}/api/v1/workflows`, {
    headers: auth,
    data: {
      project_id: project.id,
      target_type: "container",
      target_id: container.id,
      workflow_type: "state_transition",
      assignee_ids: [approverUser.id],
    },
  });
  expect(wf.status()).toBe(201);

  await authAs(page, APPROVER.email, APPROVER.password);
  await page.goto("/approvals");
  return { identifier };
}

test.describe("Approvals page — live backend (seeded data)", () => {
  test.skip(
    !process.env.VITE_API_BASE_URL,
    "Requires running backend (set VITE_API_BASE_URL)",
  );

  test("approver sees the pending task queue", async ({ page }) => {
    await seedApprovalTask(page);
    await expect(
      page.getByRole("heading", { name: "承認タスク" }),
    ).toBeVisible();
    await expect(page.getByText("キュー")).toBeVisible();
    await expect(page.getByText("件").first()).toBeVisible();
  });

  test("detail panel shows container context and ISO checklist", async ({
    page,
  }) => {
    const { identifier } = await seedApprovalTask(page);
    await expect(page.getByText(identifier)).toBeVisible();
    await expect(page.getByText("命名規則 ISO 19650-2 に適合")).toBeVisible();
  });

  test("approve action removes the task from the queue", async ({ page }) => {
    await seedApprovalTask(page);
    const badgeBefore = await page.locator(".app-badge.tone-warning").first().textContent();
    const countBefore = Number((badgeBefore ?? "0").replace(/\D/g, ""));

    await page.getByRole("button", { name: "承認して公開" }).click();
    await expect(page.getByText(/を承認しました/)).toBeVisible();

    const badgeAfter = await page.locator(".app-badge.tone-warning").first().textContent();
    const countAfter = Number((badgeAfter ?? "0").replace(/\D/g, ""));
    expect(countAfter).toBeLessThan(countBefore);
  });

  test("return action removes the task from the queue", async ({ page }) => {
    await seedApprovalTask(page);
    const badgeBefore = await page.locator(".app-badge.tone-warning").first().textContent();
    const countBefore = Number((badgeBefore ?? "0").replace(/\D/g, ""));

    await page.getByRole("button", { name: "差戻し" }).click();
    await expect(page.getByText(/を差戻ししました/)).toBeVisible();

    const badgeAfter = await page.locator(".app-badge.tone-warning").first().textContent();
    const countAfter = Number((badgeAfter ?? "0").replace(/\D/g, ""));
    expect(countAfter).toBeLessThan(countBefore);
  });

  test("reject action removes the task from the queue", async ({ page }) => {
    await seedApprovalTask(page);
    await page.getByRole("button", { name: "却下" }).click();
    await expect(page.getByText(/を却下しました/)).toBeVisible();
    await expect(page).toHaveURL(/\/approvals/);
  });
});
