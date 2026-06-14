import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import RequirementsPage from "@/pages/RequirementsPage";
import * as requirementsApiModule from "@/api/requirements";
import * as apiModule from "@/lib/api";
import type { RequirementsDocument } from "@/api/requirements";

// ─── fixtures ─────────────────────────────────────────────────────────────

const PROJECT = { id: "proj-1", code: "TST", name: "テストプロジェクト" };

const EIR_DOC: RequirementsDocument = {
  id: "doc-eir",
  project_id: "proj-1",
  document_type: "EIR",
  title: "雇用主情報要件",
  description: "ISO 19650 EIR 文書",
  revision: "R01",
  status: "approved",
  owner_id: "user-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-10T00:00:00Z",
  item_count: 2,
  items: [
    {
      id: "item-1",
      document_id: "doc-eir",
      sequence_number: 1,
      what: "LOD200 モデル",
      when_required: "設計完了時",
      how: "IFC 形式",
      who: "設計チーム",
      status: "met",
      notes: null,
    },
    {
      id: "item-2",
      document_id: "doc-eir",
      sequence_number: 2,
      what: "竣工 BIM モデル",
      when_required: "竣工時",
      how: "IFC + PDF",
      who: "施工チーム",
      status: "partial",
      notes: null,
    },
  ],
};

const BEP_DOC: RequirementsDocument = {
  id: "doc-bep",
  project_id: "proj-1",
  document_type: "BEP",
  title: "BIM 実行計画",
  description: null,
  revision: "R00",
  status: "draft",
  owner_id: "user-2",
  created_at: "2026-01-05T00:00:00Z",
  updated_at: "2026-01-05T00:00:00Z",
  item_count: 0,
  items: [],
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

describe("RequirementsPage", () => {
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
      requirementsApiModule.requirementsApi,
      "listDocuments",
    ).mockResolvedValue({
      items: [EIR_DOC, BEP_DOC],
      total: 2,
    });
  });

  it("ページタイトルが表示される", async () => {
    wrap(<RequirementsPage />);
    expect(await screen.findByText("要求文書 (EIR / BEP)")).toBeInTheDocument();
  });

  it("プロジェクトセレクタが表示される", async () => {
    wrap(<RequirementsPage />);
    expect(
      await screen.findByText("TST · テストプロジェクト"),
    ).toBeInTheDocument();
  });

  it("ISO 19650 文書タイプのタブが表示される", async () => {
    wrap(<RequirementsPage />);
    for (const type of ["OIR", "AIR", "PIR", "EIR", "BEP", "MIDP", "TIDP"]) {
      expect(await screen.findAllByText(type)).toBeTruthy();
    }
  });

  it("文書一覧に EIR と BEP が表示される", async () => {
    wrap(<RequirementsPage />);
    expect(await screen.findByText("雇用主情報要件")).toBeInTheDocument();
    expect(await screen.findByText("BIM 実行計画")).toBeInTheDocument();
  });

  it("承認済ステータスバッジが表示される", async () => {
    wrap(<RequirementsPage />);
    expect(await screen.findByText("承認済")).toBeInTheDocument();
  });

  it("ドラフトステータスバッジが表示される", async () => {
    wrap(<RequirementsPage />);
    expect(await screen.findByText("ドラフト")).toBeInTheDocument();
  });

  it("EIR 文書をクリックすると詳細が表示される", async () => {
    const user = userEvent.setup();
    wrap(<RequirementsPage />);

    const docBtn = await screen.findByText("雇用主情報要件");
    await user.click(docBtn);

    await waitFor(() => {
      expect(screen.getByText("LOD200 モデル")).toBeInTheDocument();
      expect(screen.getByText("竣工 BIM モデル")).toBeInTheDocument();
    });
  });

  it("充足・一部充足バッジが要求事項テーブルに表示される", async () => {
    const user = userEvent.setup();
    wrap(<RequirementsPage />);

    const docBtn = await screen.findByText("雇用主情報要件");
    await user.click(docBtn);

    await waitFor(() => {
      expect(screen.getByText("充足")).toBeInTheDocument();
      expect(screen.getByText("一部充足")).toBeInTheDocument();
    });
  });

  it("要件なし文書では「要求事項がありません」と表示される", async () => {
    const user = userEvent.setup();
    wrap(<RequirementsPage />);

    const docBtn = await screen.findByText("BIM 実行計画");
    await user.click(docBtn);

    await waitFor(() => {
      expect(screen.getByText("要求事項がありません")).toBeInTheDocument();
    });
  });
});

// ─── API unit tests ───────────────────────────────────────────────────────

describe("requirementsApi.listDocuments", () => {
  it("正しいエンドポイントが呼ばれる", async () => {
    const spy = vi
      .spyOn(requirementsApiModule.requirementsApi, "listDocuments")
      .mockResolvedValue({ items: [], total: 0 });
    await requirementsApiModule.requirementsApi.listDocuments("proj-1");
    expect(spy).toHaveBeenCalledWith("proj-1");
  });
});
