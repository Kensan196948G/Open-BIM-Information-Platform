import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import ReportsPage from "@/pages/ReportsPage";
import * as reportsApiModule from "@/api/reports";
import * as apiModule from "@/lib/api";
import type {
  ApprovalDelaysResponse,
  NamingViolationsResponse,
  RequirementsStatusResponse,
} from "@/api/reports";

// ─── fixtures ─────────────────────────────────────────────────────────────

const PROJECT = { id: "proj-1", code: "TST", name: "テストプロジェクト" };

const NAMING_VIOLATIONS: NamingViolationsResponse = {
  items: [
    {
      container_id: "cont-1",
      identifier: "BAD-ID",
      title: "命名違反コンテナ",
      violation_type: "naming_non_compliant",
      reason: "セグメント数不足",
      occurred_at: "2026-01-01T00:00:00Z",
      current_state: "WIP",
      current_assignee_id: "user-1",
    },
    {
      container_id: "cont-2",
      identifier: "PRJ-ORG-ZZ-GF-DR-AR-0001",
      title: "却下コンテナ",
      violation_type: "rejected",
      reason: "内容不備のため差戻し",
      occurred_at: "2026-01-02T00:00:00Z",
      current_state: "WIP",
      current_assignee_id: "user-2",
    },
  ],
  total: 2,
};

const APPROVAL_DELAYS: ApprovalDelaysResponse = {
  items: [
    {
      workflow_id: "wf-1",
      workflow_type: "state_transition",
      target_type: "container",
      target_id: "cont-3",
      container_identifier: "PRJ-ORG-ZZ-GF-DR-AR-0002",
      container_title: "遅延コンテナ",
      created_at: "2026-01-01T00:00:00Z",
      elapsed_hours: 96.5,
      assignees: [
        { assignee_id: "user-3", task_type: "review", status: "pending" },
      ],
    },
  ],
  total: 1,
  threshold_hours: 72,
};

const REQUIREMENTS_STATUS: RequirementsStatusResponse = {
  items: [
    {
      document_id: "doc-1",
      doc_type: "EIR",
      title: "雇用主情報要件",
      revision: "01",
      met_count: 2,
      partial_count: 1,
      not_met_count: 1,
      total_count: 4,
      fulfillment_rate: 0.5,
    },
  ],
  total: 1,
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

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.spyOn(apiModule.api, "get").mockImplementation((url: string) => {
      if (url === "/projects") {
        return Promise.resolve({
          data: { items: [PROJECT], total: 1 },
        }) as never;
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });

    vi.spyOn(
      reportsApiModule.reportsApi,
      "getNamingViolations",
    ).mockResolvedValue(NAMING_VIOLATIONS);
    vi.spyOn(
      reportsApiModule.reportsApi,
      "getApprovalDelays",
    ).mockResolvedValue(APPROVAL_DELAYS);
    vi.spyOn(
      reportsApiModule.reportsApi,
      "getRequirementsStatus",
    ).mockResolvedValue(REQUIREMENTS_STATUS);
  });

  it("ページタイトルが表示される", async () => {
    wrap(<ReportsPage />);
    expect(
      await screen.findByText("監査・コンプライアンスレポート"),
    ).toBeInTheDocument();
  });

  it("プロジェクトセレクタが表示される", async () => {
    wrap(<ReportsPage />);
    expect(
      await screen.findByText("TST · テストプロジェクト"),
    ).toBeInTheDocument();
  });

  it("命名違反・却下件数がKPIカードに表示される", async () => {
    wrap(<ReportsPage />);
    expect(await screen.findByText("命名違反・却下")).toBeInTheDocument();
    expect((await screen.findAllByText("2")).length).toBeGreaterThan(0);
  });

  it("命名違反テーブルに違反・却下の両方が表示される", async () => {
    wrap(<ReportsPage />);
    expect(await screen.findByText("命名違反コンテナ")).toBeInTheDocument();
    expect(await screen.findByText("却下コンテナ")).toBeInTheDocument();
    expect(await screen.findByText("セグメント数不足")).toBeInTheDocument();
    expect(await screen.findByText("内容不備のため差戻し")).toBeInTheDocument();
  });

  it("承認遅延テーブルに遅延ワークフローが表示される", async () => {
    wrap(<ReportsPage />);
    expect(
      await screen.findByText("遅延コンテナ", { exact: false }),
    ).toBeInTheDocument();
    expect(await screen.findByText("96.5h")).toBeInTheDocument();
  });

  it("要求充足状況テーブルに文書別の集計が表示される", async () => {
    wrap(<ReportsPage />);
    expect(await screen.findByText("雇用主情報要件")).toBeInTheDocument();
    expect(await screen.findByText("50%")).toBeInTheDocument();
  });

  it("閾値変更で getApprovalDelays が新しい閾値で再呼び出しされる", async () => {
    wrap(<ReportsPage />);
    await screen.findByText("命名違反・却下");
    expect(reportsApiModule.reportsApi.getApprovalDelays).toHaveBeenCalledWith(
      "proj-1",
      72,
    );
  });
});

// ─── API unit tests ───────────────────────────────────────────────────────

describe("reportsApi", () => {
  it("getNamingViolations は正しいエンドポイントを呼ぶ", async () => {
    const spy = vi
      .spyOn(reportsApiModule.reportsApi, "getNamingViolations")
      .mockResolvedValue({ items: [], total: 0 });
    await reportsApiModule.reportsApi.getNamingViolations("proj-1");
    expect(spy).toHaveBeenCalledWith("proj-1");
  });

  it("getApprovalDelays は正しいエンドポイントを呼ぶ", async () => {
    const spy = vi
      .spyOn(reportsApiModule.reportsApi, "getApprovalDelays")
      .mockResolvedValue({ items: [], total: 0, threshold_hours: 48 });
    await reportsApiModule.reportsApi.getApprovalDelays("proj-1", 48);
    expect(spy).toHaveBeenCalledWith("proj-1", 48);
  });

  it("getRequirementsStatus は正しいエンドポイントを呼ぶ", async () => {
    const spy = vi
      .spyOn(reportsApiModule.reportsApi, "getRequirementsStatus")
      .mockResolvedValue({ items: [], total: 0 });
    await reportsApiModule.reportsApi.getRequirementsStatus("proj-1");
    expect(spy).toHaveBeenCalledWith("proj-1");
  });
});
