import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle,
  Download,
  Link as LinkIcon,
  Loader2,
  Plus,
} from "lucide-react";
import { requirementsApi } from "@/api/requirements";
import type { RequirementsDocument, DocumentStatus } from "@/api/requirements";
import { api } from "@/lib/api";
import type { PaginatedResponse, Project } from "@/types";

const DOC_TYPES = ["OIR", "AIR", "PIR", "EIR", "BEP", "MIDP", "TIDP"] as const;

const statusMeta: Record<
  DocumentStatus,
  { tone: "success" | "warning" | "neutral" | "danger"; label: string }
> = {
  approved: { tone: "success", label: "承認済" },
  under_review: { tone: "warning", label: "レビュー中" },
  draft: { tone: "neutral", label: "ドラフト" },
  superseded: { tone: "danger", label: "改訂済" },
  withdrawn: { tone: "danger", label: "廃止" },
};

const itemStatusMeta = {
  met: { tone: "success", label: "充足" },
  partial: { tone: "warning", label: "一部充足" },
  not_met: { tone: "danger", label: "未充足" },
} as const;

export default function RequirementsPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [activeDocId, setActiveDocId] = useState<string>("");

  const { data: projectsData } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
    select: (data) => data.items,
  });

  const projects = projectsData ?? [];

  const effectiveProjectId = selectedProjectId || projects[0]?.id || "";

  const {
    data: docsData,
    isLoading: docsLoading,
    isError: docsError,
  } = useQuery({
    queryKey: ["requirements", effectiveProjectId],
    queryFn: () => requirementsApi.listDocuments(effectiveProjectId),
    enabled: !!effectiveProjectId,
  });

  const docs = docsData?.items ?? [];
  const activeDoc: RequirementsDocument | undefined =
    docs.find((d) => d.id === activeDocId) ?? docs[0];

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">要求文書 (EIR / BEP)</h1>
          <p className="t-sec mt-1">ISO 19650 情報要求・配信計画</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="rounded-lg border px-3 py-2 text-sm"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--text)",
            }}
            value={selectedProjectId || projects[0]?.id || ""}
            onChange={(e) => {
              setSelectedProjectId(e.target.value);
              setActiveDocId("");
            }}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} · {p.name}
              </option>
            ))}
          </select>
          <button className="app-btn app-btn-primary">
            <Plus className="h-4 w-4" />
            文書を作成
          </button>
        </div>
      </div>

      <div className="app-card-pad mb-4">
        <div className="t-label mb-3">情報要求の階層 (ISO 19650)</div>
        <div className="flex gap-2 overflow-x-auto">
          {DOC_TYPES.map((type) => {
            const doc = docs.find((d) => d.document_type === type);
            const selected = doc?.id === activeDoc?.id;
            return (
              <button
                key={type}
                disabled={!doc}
                className="min-w-[92px] rounded-xl border px-4 py-2 text-center"
                style={{
                  borderColor: selected ? "var(--primary)" : "var(--border)",
                  background: selected
                    ? "var(--primary-subtle)"
                    : doc
                      ? "var(--surface)"
                      : "var(--surface-2)",
                  opacity: doc ? 1 : 0.5,
                }}
                onClick={() => doc && setActiveDocId(doc.id)}
              >
                <div
                  className="mono text-sm font-bold"
                  style={{
                    color: selected ? "var(--primary-text)" : "var(--text)",
                  }}
                >
                  {type}
                </div>
                <div
                  className="text-[9.5px]"
                  style={{ color: "var(--text-3)" }}
                >
                  要求文書
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {docsLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2
            className="h-6 w-6 animate-spin"
            style={{ color: "var(--primary)" }}
          />
        </div>
      )}

      {docsError && (
        <div
          className="rounded-xl border p-6 text-center text-sm"
          style={{ borderColor: "var(--border)", color: "var(--danger-fg)" }}
        >
          要求文書の読み込みに失敗しました。プロジェクトを選択し直してください。
        </div>
      )}

      {!docsLoading && !docsError && (
        <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
          <div className="app-card overflow-hidden">
            <div
              className="border-b px-4 py-3"
              style={{ borderColor: "var(--border)" }}
            >
              <span className="t-h2">文書 ({docs.length})</span>
            </div>
            {docs.length === 0 ? (
              <div
                className="px-4 py-8 text-center text-sm"
                style={{ color: "var(--text-3)" }}
              >
                {effectiveProjectId
                  ? "このプロジェクトに要求文書はありません"
                  : "プロジェクトを選択してください"}
              </div>
            ) : (
              docs.map((doc) => {
                const selected = doc.id === activeDoc?.id;
                const meta = statusMeta[doc.status] ?? statusMeta.draft;
                return (
                  <button
                    key={doc.id}
                    className="block w-full border-b p-4 text-left"
                    style={{
                      borderColor: "var(--border-faint)",
                      borderLeft: selected
                        ? "3px solid var(--primary)"
                        : "3px solid transparent",
                      background: selected
                        ? "var(--primary-subtle)"
                        : "transparent",
                    }}
                    onClick={() => setActiveDocId(doc.id)}
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <span
                        className="mono rounded-md px-2 py-0.5 text-xs font-bold"
                        style={{ background: "var(--surface-3)" }}
                      >
                        {doc.document_type}
                      </span>
                      <span
                        className={`app-badge app-badge-sq tone-${meta.tone}`}
                      >
                        {meta.label}
                      </span>
                      <span className="mono t-tiny ml-auto">
                        {doc.revision}
                      </span>
                    </div>
                    <div className="text-[12.5px] font-medium">{doc.title}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="t-tiny mono ml-auto">
                        {doc.item_count} 要件
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="app-card-pad">
            {!activeDoc ? (
              <div
                className="flex items-center justify-center py-20 text-sm"
                style={{ color: "var(--text-3)" }}
              >
                左側から文書を選択してください
              </div>
            ) : (
              <>
                <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div>
                    <div className="mb-2 flex items-center gap-2">
                      <span
                        className="mono rounded-md px-2 py-1 text-xs font-bold"
                        style={{ background: "var(--surface-3)" }}
                      >
                        {activeDoc.document_type}
                      </span>
                      <span
                        className="mono text-[12.5px]"
                        style={{ color: "var(--text-2)" }}
                      >
                        {activeDoc.revision}
                      </span>
                      <span
                        className={`app-badge app-badge-sq tone-${(statusMeta[activeDoc.status] ?? statusMeta.draft).tone}`}
                      >
                        {
                          (statusMeta[activeDoc.status] ?? statusMeta.draft)
                            .label
                        }
                      </span>
                    </div>
                    <h2 className="t-h1">{activeDoc.title}</h2>
                    {activeDoc.description && (
                      <p className="t-sec mt-1 max-w-2xl">
                        {activeDoc.description}
                      </p>
                    )}
                  </div>
                  <button className="app-btn app-btn-sm">
                    <Download className="h-3.5 w-3.5" />
                    PDF
                  </button>
                </div>

                <div className="mb-5 grid gap-3 sm:grid-cols-4">
                  <div
                    className="rounded-xl p-3"
                    style={{ background: "var(--surface-2)" }}
                  >
                    <div className="t-label mb-2">要件数</div>
                    <div className="text-sm font-semibold">
                      {activeDoc.item_count} 件
                    </div>
                  </div>
                  <div
                    className="rounded-xl p-3 sm:col-span-3"
                    style={{ background: "var(--surface-2)" }}
                  >
                    <div className="t-label mb-2">関連文書</div>
                    <span className="app-badge app-badge-sq tone-info">
                      <LinkIcon className="h-3 w-3" />
                      EIR / BEP / MIDP
                    </span>
                  </div>
                </div>

                <div className="mb-3 flex items-center justify-between">
                  <div className="t-h2">要求事項明細</div>
                  <span className="t-tiny">
                    何を / いつ / どのように / 誰のために
                  </span>
                </div>
                <div
                  className="overflow-hidden rounded-xl border"
                  style={{ borderColor: "var(--border)" }}
                >
                  <div className="overflow-x-auto">
                    <table className="app-table min-w-[860px]">
                      <thead>
                        <tr>
                          <th>No.</th>
                          <th>何を</th>
                          <th>いつ</th>
                          <th>どのように</th>
                          <th>誰のために</th>
                          <th>状態</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeDoc.items.length === 0 ? (
                          <tr>
                            <td
                              colSpan={6}
                              className="py-8 text-center text-sm"
                              style={{ color: "var(--text-3)" }}
                            >
                              要求事項がありません
                            </td>
                          </tr>
                        ) : (
                          activeDoc.items.map((item) => {
                            const im =
                              itemStatusMeta[item.status] ??
                              itemStatusMeta.not_met;
                            return (
                              <tr key={item.id}>
                                <td>
                                  <span className="mono text-xs font-semibold">
                                    {item.sequence_number}
                                  </span>
                                </td>
                                <td className="font-medium">{item.what}</td>
                                <td>{item.when_required ?? "—"}</td>
                                <td>{item.how ?? "—"}</td>
                                <td>{item.who ?? "—"}</td>
                                <td>
                                  <span
                                    className={`app-badge app-badge-sq tone-${im.tone}`}
                                  >
                                    <CheckCircle className="h-3 w-3" />
                                    {im.label}
                                  </span>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
