import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import ContainerDetailPage from "@/pages/ContainerDetailPage";
import * as containersApiModule from "@/api/containers";
import * as shareRequestsApiModule from "@/api/shareRequests";
import * as apiModule from "@/lib/api";
import { useAuthStore } from "@/hooks/useAuthStore";
import type { InformationContainer, PaginatedResponse } from "@/types";
import type { ShareRequest } from "@/api/shareRequests";

const CONTAINER: InformationContainer = {
  id: "container-1",
  project_id: "proj-1",
  created_by: "user-1",
  identifier: "PRJ-ORG-XX-01-DR-A-0001",
  title: "テストコンテナ",
  container_type: "drawing",
  current_state: "WIP",
  current_revision: "P01",
  current_branch: null,
  security_level: "limited",
  naming_valid: true,
  naming_issues: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

afterEach(() => {
  vi.restoreAllMocks();
});

const PENDING_REQUEST: ShareRequest = {
  id: "sr-1",
  container_id: "container-1",
  requested_by_user_id: "user-1",
  approved_by_user_id: null,
  reason: "外部レビューのため",
  status: "pending",
  expires_at: null,
  created_at: "2026-02-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
};

function wrap() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/projects/proj-1/containers/container-1"]}>
      <QueryClientProvider client={qc}>
        <Routes>
          <Route
            path="/projects/:projectId/containers/:containerId"
            element={<ContainerDetailPage />}
          />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ContainerDetailPage — 外部共有申請", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: {
        id: "user-1",
        email: "u@example.com",
        username: "u",
        full_name: "Test User",
        is_active: true,
        is_platform_admin: false,
      },
      token: "test-token",
      refreshToken: null,
    });

    vi.spyOn(apiModule.api, "get").mockImplementation((url: string) => {
      if (url === `/projects/proj-1/containers`) {
        return Promise.resolve({
          data: {
            items: [CONTAINER],
            total: 1,
            page: 1,
            size: 20,
          } as PaginatedResponse<InformationContainer>,
        }) as never;
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    vi.spyOn(containersApiModule, "listFiles").mockResolvedValue([]);
    vi.spyOn(containersApiModule, "listContainerRevisions").mockResolvedValue(
      [],
    );
    vi.spyOn(shareRequestsApiModule.shareRequestsApi, "list").mockResolvedValue(
      { items: [PENDING_REQUEST], total: 1 },
    );
  });

  it("外部共有タブに申請件数が表示される", async () => {
    wrap();
    expect(await screen.findByText("外部共有 (1)")).toBeInTheDocument();
  });

  it("外部共有タブをクリックすると申請一覧と申請フォームが表示される", async () => {
    const user = userEvent.setup();
    wrap();

    await user.click(await screen.findByText("外部共有 (1)"));

    await waitFor(() => {
      expect(screen.getByText("外部共有を申請")).toBeInTheDocument();
      expect(screen.getByText("外部レビューのため")).toBeInTheDocument();
      expect(screen.getByText("pending")).toBeInTheDocument();
    });
  });

  it("申請フォームから作成APIが呼ばれる", async () => {
    const user = userEvent.setup();
    const createSpy = vi
      .spyOn(shareRequestsApiModule.shareRequestsApi, "create")
      .mockResolvedValue({ ...PENDING_REQUEST, id: "sr-new" });
    wrap();

    await user.click(await screen.findByText("外部共有 (1)"));
    const textarea = await screen.findByPlaceholderText("申請理由（任意）");
    await user.type(textarea, "パートナー向け");
    const submitButtons = await screen.findAllByText("外部共有を申請");
    await user.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        "proj-1",
        "container-1",
        "パートナー向け",
      );
    });
  });

  it("pending の申請には承認・却下ボタンが表示される", async () => {
    const user = userEvent.setup();
    wrap();

    await user.click(await screen.findByText("外部共有 (1)"));

    await waitFor(() => {
      expect(screen.getByText("承認")).toBeInTheDocument();
      expect(screen.getByText("却下")).toBeInTheDocument();
      expect(screen.getByText("失効")).toBeInTheDocument();
    });
  });

  it("承認ボタンから承認APIが呼ばれる", async () => {
    const user = userEvent.setup();
    const approveSpy = vi
      .spyOn(shareRequestsApiModule.shareRequestsApi, "approve")
      .mockResolvedValue({
        ...PENDING_REQUEST,
        status: "approved",
        token: "tok",
        share_url_path: "/api/v1/public/shared/tok",
      });
    wrap();

    await user.click(await screen.findByText("外部共有 (1)"));
    await user.click(await screen.findByText("承認"));

    await waitFor(() => {
      expect(approveSpy).toHaveBeenCalledWith("proj-1", "container-1", "sr-1");
    });
  });
});

describe("shareRequestsApi", () => {
  it("list は正しいエンドポイントを呼ぶ", async () => {
    const spy = vi
      .spyOn(apiModule.api, "get")
      .mockResolvedValue({ data: { items: [], total: 0 } } as never);
    await shareRequestsApiModule.shareRequestsApi.list("proj-1", "container-1");
    expect(spy).toHaveBeenCalledWith(
      "/projects/proj-1/containers/container-1/share-requests",
    );
  });

  it("revoke は正しいエンドポイントを呼ぶ", async () => {
    const spy = vi
      .spyOn(apiModule.api, "post")
      .mockResolvedValue({ data: PENDING_REQUEST } as never);
    await shareRequestsApiModule.shareRequestsApi.revoke(
      "proj-1",
      "container-1",
      "sr-1",
    );
    expect(spy).toHaveBeenCalledWith(
      "/projects/proj-1/containers/container-1/share-requests/sr-1/revoke",
      {},
    );
  });
});
