import { beforeEach, describe, expect, it, vi } from "vitest";
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
  owner_user_id: "user-1",
  doc_type: "EIR",
  title: "雇用主情報要件",
  description: "ISO 19650 EIR 文書",
  revision: "01",
  status: "approved",
  effective_from: null,
  effective_to: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-10T00:00:00Z",
  item_count: 2,
  items: [
    {
      id: "item-1",
      document_id: "doc-eir",
      item_no: "001",
      what: "LOD200 モデル",
      when_required: "設計完了時",
      how_required: "IFC 形式",
      for_whom: "設計チーム",
      acceptance_criteria: null,
      responsible_user_id: null,
      status: "met",
      notes: null,
    },
    {
      id: "item-2",
      document_id: "doc-eir",
      item_no: "002",
      what: "竣工 BIM モデル",
      when_required: "竣工時",
      how_required: "IFC + PDF",
      for_whom: "施工チーム",
      acceptance_criteria: null,
      responsible_user_id: null,
      status: "partial",
      notes: null,
    },
  ],
};

const BEP_DOC: RequirementsDocument = {
  id: "doc-bep",
  project_id: "proj-1",
  owner_user_id: "user-2",
  doc_type: "BEP",
  title: "BIM 実行計画",
  description: null,
  revision: "00",
  status: "draft",
  effective_from: null,
  effective_to: null,
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
    expect(
      (await screen.findAllByText("雇用主情報要件")).length,
    ).toBeGreaterThan(0);
    expect(await screen.findByText("BIM 実行計画")).toBeInTheDocument();
  });

  it("承認済ステータスバッジが表示される", async () => {
    wrap(<RequirementsPage />);
    expect((await screen.findAllByText("承認済")).length).toBeGreaterThan(0);
  });

  it("EIR 文書をクリックすると詳細が表示される", async () => {
    const user = userEvent.setup();
    wrap(<RequirementsPage />);

    const docBtn = (await screen.findAllByText("雇用主情報要件"))[0];
    await user.click(docBtn);

    await waitFor(() => {
      expect(screen.getByText("LOD200 モデル")).toBeInTheDocument();
      expect(screen.getByText("竣工 BIM モデル")).toBeInTheDocument();
    });
  });

  it("充足・一部充足バッジが要求事項テーブルに表示される", async () => {
    const user = userEvent.setup();
    wrap(<RequirementsPage />);

    const docBtn = (await screen.findAllByText("雇用主情報要件"))[0];
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

  it("文書を作成ダイアログから作成APIが呼ばれる", async () => {
    const user = userEvent.setup();
    const createSpy = vi
      .spyOn(requirementsApiModule.requirementsApi, "createDocument")
      .mockResolvedValue({ ...EIR_DOC, id: "doc-new", title: "新規EIR" });
    wrap(<RequirementsPage />);

    await user.click(await screen.findByText("文書を作成"));
    await user.type(
      await screen.findByPlaceholderText("例: 雇用主情報要件 (EIR)"),
      "新規EIR",
    );
    await user.click(await screen.findByText("作成"));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith("proj-1", expect.objectContaining({ title: "新規EIR" }));
    });
  });

  it("要件を追加フォームから作成APIが呼ばれる", async () => {
    const user = userEvent.setup();
    const createItemSpy = vi
      .spyOn(requirementsApiModule.requirementsApi, "createItem")
      .mockResolvedValue({
        id: "item-new",
        document_id: "doc-bep",
        item_no: "001",
        what: "追加要件",
        when_required: null,
        how_required: null,
        for_whom: null,
        acceptance_criteria: null,
        responsible_user_id: null,
        status: "not_met",
        notes: null,
      });
    wrap(<RequirementsPage />);

    await user.click(await screen.findByText("BIM 実行計画"));
    await user.click(await screen.findByText("要件を追加"));
    await user.type(
      await screen.findByText("何を（必須）").then((label) => label.nextElementSibling as HTMLTextAreaElement),
      "追加要件",
    );
    await user.click(await screen.findByText("追加"));

    await waitFor(() => {
      expect(createItemSpy).toHaveBeenCalledWith(
        "proj-1",
        "doc-bep",
        expect.objectContaining({ what: "追加要件" }),
      );
    });
  });
});

// ─── API unit tests ───────────────────────────────────────────────────────

describe("requirementsApi", () => {
  it("listDocuments は正しいエンドポイントを呼ぶ", async () => {
    const spy = vi
      .spyOn(requirementsApiModule.requirementsApi, "listDocuments")
      .mockResolvedValue({ items: [], total: 0 });
    await requirementsApiModule.requirementsApi.listDocuments("proj-1");
    expect(spy).toHaveBeenCalledWith("proj-1");
  });
});
