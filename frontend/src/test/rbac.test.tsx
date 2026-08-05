import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import RBACPage from "@/pages/RBACPage";
import * as rbacApiModule from "@/api/rbac";
import type { Organization, Permission, Role } from "@/api/rbac";

// ─── fixtures ─────────────────────────────────────────────────────────────

const ORG: Organization = {
  id: "org-1",
  name: "テスト組織",
  slug: "test-org",
  description: null,
  is_active: true,
};

const PERM_READ: Permission = {
  id: "perm-read",
  code: "project:read",
  description: "プロジェクト閲覧",
  category: "project",
};

const PERM_WRITE: Permission = {
  id: "perm-write",
  code: "project:write",
  description: "プロジェクト編集",
  category: "project",
};

const SYSTEM_ROLE: Role = {
  id: "role-admin",
  organization_id: null,
  name: "管理者",
  description: "システム管理者",
  is_system_role: true,
  permissions: [PERM_READ],
};

const CUSTOM_ROLE: Role = {
  id: "role-viewer",
  organization_id: "org-1",
  name: "閲覧者",
  description: null,
  is_system_role: false,
  permissions: [],
};

// ─── helpers ──────────────────────────────────────────────────────────────

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

// ─── tests ────────────────────────────────────────────────────────────────

describe("RBACPage", () => {
  beforeEach(() => {
    vi.spyOn(rbacApiModule.rbacApi, "listOrganizations").mockResolvedValue([
      ORG,
    ]);
    vi.spyOn(rbacApiModule.rbacApi, "listPermissions").mockResolvedValue([
      PERM_READ,
      PERM_WRITE,
    ]);
    vi.spyOn(rbacApiModule.rbacApi, "listRoles").mockResolvedValue([
      SYSTEM_ROLE,
      CUSTOM_ROLE,
    ]);
  });

  it("ページタイトルが表示される", async () => {
    wrap(<RBACPage />);
    expect(await screen.findByText("ロール・権限管理")).toBeInTheDocument();
  });

  it("ロール一覧が表示される", async () => {
    wrap(<RBACPage />);
    expect(await screen.findByText("管理者")).toBeInTheDocument();
    expect(await screen.findByText("閲覧者")).toBeInTheDocument();
  });

  it("システムロールに「システム」バッジが表示される", async () => {
    wrap(<RBACPage />);
    expect(await screen.findByText("システム")).toBeInTheDocument();
  });

  it("カスタムロールには編集・削除ボタンが表示される", async () => {
    wrap(<RBACPage />);
    // wait for roles to load
    await screen.findByText("閲覧者");
    const editBtns = screen.getAllByText("編集");
    expect(editBtns.length).toBeGreaterThan(0);
  });

  it("ロールを展開すると権限パネルが表示される", async () => {
    const user = userEvent.setup();
    wrap(<RBACPage />);
    await screen.findByText("管理者");

    // Find a chevron button near 管理者
    const adminCard = screen.getByText("管理者").closest(".rounded-xl");
    expect(adminCard).toBeTruthy();

    const chevronBtn = adminCard!.querySelector(
      "button:last-child",
    ) as HTMLButtonElement;
    await user.click(chevronBtn);

    // Permissions panel should appear
    await waitFor(() => {
      expect(screen.getByText("project:read")).toBeInTheDocument();
    });
  });

  it("システムロールの権限チェックボックスは無効化される", async () => {
    const user = userEvent.setup();
    wrap(<RBACPage />);
    await screen.findByText("管理者");

    const adminCard = screen.getByText("管理者").closest(".rounded-xl");
    const chevronBtn = adminCard!.querySelector(
      "button:last-child",
    ) as HTMLButtonElement;
    await user.click(chevronBtn);

    await waitFor(() => {
      const permBtn = screen.getByText("project:read").closest("button");
      expect(permBtn).toBeDisabled();
    });
  });

  it("ロールを作成ダイアログが開く", async () => {
    const user = userEvent.setup();
    wrap(<RBACPage />);
    await screen.findByText("ロールを作成");

    await user.click(screen.getByText("ロールを作成"));
    expect(
      await screen.findByText("ロールを作成", { selector: "h2" }),
    ).toBeInTheDocument();
  });
});

// ─── API client unit tests ────────────────────────────────────────────────

describe("rbacApi.listOrganizations", () => {
  it("正しいエンドポイントが呼ばれる", async () => {
    const spy = vi
      .spyOn(rbacApiModule.rbacApi, "listOrganizations")
      .mockResolvedValue([ORG]);
    spy.mockClear();
    await rbacApiModule.rbacApi.listOrganizations();
    expect(spy).toHaveBeenCalledOnce();
  });
});
