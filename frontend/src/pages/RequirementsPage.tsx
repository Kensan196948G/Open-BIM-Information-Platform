import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  Download,
  Link as LinkIcon,
  Loader2,
  Pencil,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import {
  type DocumentStatus,
  type DocumentType,
  type ItemStatus,
  type RequirementsDocument,
  requirementsApi,
} from "@/api/requirements";
import { api } from "@/lib/api";
import type { PaginatedResponse, Project } from "@/types";

const DOC_TYPES: DocumentType[] = [
  "OIR",
  "AIR",
  "PIR",
  "EIR",
  "BEP",
  "MIDP",
  "TIDP",
  "InformationProtocol",
  "Supplementary",
];

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

const itemStatusMeta: Record<
  ItemStatus,
  { tone: "success" | "warning" | "danger"; label: string }
> = {
  met: { tone: "success", label: "充足" },
  partial: { tone: "warning", label: "一部充足" },
  not_met: { tone: "danger", label: "未充足" },
};

const statusOptions: DocumentStatus[] = [
  "draft",
  "under_review",
  "approved",
  "superseded",
  "withdrawn",
];

const itemStatusOptions: ItemStatus[] = ["not_met", "partial", "met"];

interface DocFormState {
  doc_type: DocumentType;
  title: string;
  description: string;
  revision: string;
  status: DocumentStatus;
}

interface ItemFormState {
  item_no: string;
  what: string;
  when_required: string;
  how_required: string;
  for_whom: string;
  status: ItemStatus;
}

const emptyItemForm: ItemFormState = {
  item_no: "",
  what: "",
  when_required: "",
  how_required: "",
  for_whom: "",
  status: "not_met",
};

function DocCreateDialog({
  projectId,
  onClose,
}: {
  projectId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<DocFormState>({
    doc_type: "EIR",
    title: "",
    description: "",
    revision: "01",
    status: "draft",
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => requirementsApi.createDocument(projectId, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["requirements", projectId] });
      onClose();
    },
    onError: () => setError("文書の作成に失敗しました"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) {
      setError("タイトルは必須です");
      return;
    }
    setError(null);
    mutation.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl p-6 shadow-xl" style={{ background: "var(--surface)" }}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">要求文書を作成</h2>
          <button onClick={onClose} className="rounded p-1 hover:bg-black/5 dark:hover:bg-white/10">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={submit} className="grid gap-4">
          <label className="grid gap-1 text-sm">
            <span className="font-medium">文書種別</span>
            <select
              className="app-field h-10"
              value={form.doc_type}
              onChange={(e) => setForm({ ...form, doc_type: e.target.value as DocumentType })}
            >
              {DOC_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">タイトル</span>
            <input
              className="app-field h-10"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="例: 雇用主情報要件 (EIR)"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">説明（任意）</span>
            <textarea
              className="app-field min-h-[72px]"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1 text-sm">
              <span className="font-medium">改訂</span>
              <input
                className="app-field h-10"
                value={form.revision}
                onChange={(e) => setForm({ ...form, revision: e.target.value })}
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-medium">状態</span>
              <select
                className="app-field h-10"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value as DocumentStatus })}
              >
                {statusOptions.map((s) => (
                  <option key={s} value={s}>{statusMeta[s].label}</option>
                ))}
              </select>
            </label>
          </div>
          {error && <div className="rounded-lg p-3 text-sm tone-danger">{error}</div>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="app-btn h-10">
              キャンセル
            </button>
            <button type="submit" disabled={mutation.isPending} className="app-btn app-btn-primary h-10">
              {mutation.isPending ? "作成中..." : "作成"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ItemForm({
  projectId,
  doc,
  initial,
  itemId,
  onCancel,
}: {
  projectId: string;
  doc: RequirementsDocument;
  initial: ItemFormState | null;
  itemId?: string;
  onCancel: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ItemFormState>(
    initial ?? { ...emptyItemForm, item_no: String(doc.items.length + 1).padStart(3, "0") },
  );
  const [error, setError] = useState<string | null>(null);
  const editing = initial !== null;

  const mutation = useMutation({
    mutationFn: () =>
      editing
        ? requirementsApi.updateItem(projectId, doc.id, itemId!, form)
        : requirementsApi.createItem(projectId, doc.id, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["requirements", projectId] });
      onCancel();
    },
    onError: () => setError(editing ? "項目の更新に失敗しました" : "項目の追加に失敗しました"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.what.trim()) {
      setError("「何を」は必須です");
      return;
    }
    setError(null);
    mutation.mutate();
  }

  return (
    <form onSubmit={submit} className="grid gap-3 rounded-xl border p-4 sm:grid-cols-2" style={{ borderColor: "var(--border)" }}>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">No.</span>
        <input className="app-field h-9" value={form.item_no} onChange={(e) => setForm({ ...form, item_no: e.target.value })} />
      </label>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">状態</span>
        <select className="app-field h-9" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as ItemStatus })}>
          {itemStatusOptions.map((s) => (
            <option key={s} value={s}>{itemStatusMeta[s].label}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm sm:col-span-2">
        <span className="font-medium">何を（必須）</span>
        <textarea className="app-field min-h-[56px]" value={form.what} onChange={(e) => setForm({ ...form, what: e.target.value })} />
      </label>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">いつ</span>
        <input className="app-field h-9" value={form.when_required} onChange={(e) => setForm({ ...form, when_required: e.target.value })} />
      </label>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">どのように</span>
        <input className="app-field h-9" value={form.how_required} onChange={(e) => setForm({ ...form, how_required: e.target.value })} />
      </label>
      <label className="grid gap-1 text-sm sm:col-span-2">
        <span className="font-medium">誰のために</span>
        <input className="app-field h-9" value={form.for_whom} onChange={(e) => setForm({ ...form, for_whom: e.target.value })} />
      </label>
      {error && <div className="rounded-lg p-3 text-sm tone-danger sm:col-span-2">{error}</div>}
      <div className="flex justify-end gap-2 sm:col-span-2">
        <button type="button" onClick={onCancel} className="app-btn h-9">キャンセル</button>
        <button type="submit" disabled={mutation.isPending} className="app-btn app-btn-primary h-9">
          {mutation.isPending ? "保存中..." : editing ? "更新" : "追加"}
        </button>
      </div>
    </form>
  );
}

export default function RequirementsPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [activeDocId, setActiveDocId] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [addingItem, setAddingItem] = useState(false);
  const [editingItemNo, setEditingItemNo] = useState<string | null>(null);
  const qc = useQueryClient();

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

  const deleteDoc = useMutation({
    mutationFn: (docId: string) => requirementsApi.deleteDocument(effectiveProjectId, docId),
    onSuccess: () => {
      setActiveDocId("");
      qc.invalidateQueries({ queryKey: ["requirements", effectiveProjectId] });
    },
  });

  const deleteItem = useMutation({
    mutationFn: (itemId: string) =>
      requirementsApi.deleteItem(effectiveProjectId, activeDoc!.id, itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["requirements", effectiveProjectId] });
      setEditingItemNo(null);
    },
  });

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
          <button className="app-btn app-btn-primary" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            文書を作成
          </button>
        </div>
      </div>

      <div className="app-card-pad mb-4">
        <div className="t-label mb-3">情報要求の階層 (ISO 19650)</div>
        <div className="flex gap-2 overflow-x-auto">
          {DOC_TYPES.map((type) => {
            const doc = docs.find((d) => d.doc_type === type);
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
          <Loader2 className="h-6 w-6 animate-spin" style={{ color: "var(--primary)" }} />
        </div>
      )}

      {docsError && (
        <div className="rounded-xl border p-6 text-center text-sm" style={{ borderColor: "var(--border)", color: "var(--danger-fg)" }}>
          要求文書の読み込みに失敗しました。プロジェクトを選択し直してください。
        </div>
      )}

      {!docsLoading && !docsError && (
        <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
          <div className="app-card overflow-hidden">
            <div className="border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
              <span className="t-h2">文書 ({docs.length})</span>
            </div>
            {docs.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--text-3)" }}>
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
                      borderLeft: selected ? "3px solid var(--primary)" : "3px solid transparent",
                      background: selected ? "var(--primary-subtle)" : "transparent",
                    }}
                    onClick={() => setActiveDocId(doc.id)}
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <span className="mono rounded-md px-2 py-0.5 text-xs font-bold" style={{ background: "var(--surface-3)" }}>
                        {doc.doc_type}
                      </span>
                      <span className={`app-badge app-badge-sq tone-${meta.tone}`}>
                        {meta.label}
                      </span>
                      <span className="mono t-tiny ml-auto">{doc.revision}</span>
                    </div>
                    <div className="text-[12.5px] font-medium">{doc.title}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="t-tiny mono ml-auto">{doc.item_count} 要件</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="app-card-pad">
            {!activeDoc ? (
              <div className="flex items-center justify-center py-20 text-sm" style={{ color: "var(--text-3)" }}>
                左側から文書を選択してください
              </div>
            ) : (
              <>
                <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div>
                    <div className="mb-2 flex items-center gap-2">
                      <span className="mono rounded-md px-2 py-1 text-xs font-bold" style={{ background: "var(--surface-3)" }}>
                        {activeDoc.doc_type}
                      </span>
                      <span className="mono text-[12.5px]" style={{ color: "var(--text-2)" }}>
                        {activeDoc.revision}
                      </span>
                      <span className={`app-badge app-badge-sq tone-${(statusMeta[activeDoc.status] ?? statusMeta.draft).tone}`}>
                        {(statusMeta[activeDoc.status] ?? statusMeta.draft).label}
                      </span>
                    </div>
                    <h2 className="t-h1">{activeDoc.title}</h2>
                    {activeDoc.description && (
                      <p className="t-sec mt-1 max-w-2xl">{activeDoc.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="app-btn app-btn-sm" title="ブラウザの印刷ダイアログからPDF保存できます" onClick={() => window.print()}>
                      <Download className="h-3.5 w-3.5" />
                      PDF
                    </button>
                    <button
                      className="app-btn app-btn-sm"
                      onClick={() => {
                        if (window.confirm(`文書「${activeDoc.title}」を削除しますか？`)) {
                          deleteDoc.mutate(activeDoc.id);
                        }
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      削除
                    </button>
                  </div>
                </div>

                <div className="mb-5 grid gap-3 sm:grid-cols-4">
                  <div className="rounded-xl p-3" style={{ background: "var(--surface-2)" }}>
                    <div className="t-label mb-2">要件数</div>
                    <div className="text-sm font-semibold">{activeDoc.item_count} 件</div>
                  </div>
                  <div className="rounded-xl p-3 sm:col-span-3" style={{ background: "var(--surface-2)" }}>
                    <div className="t-label mb-2">関連文書</div>
                    <span className="app-badge app-badge-sq tone-info">
                      <LinkIcon className="h-3 w-3" />
                      EIR / BEP / MIDP
                    </span>
                  </div>
                </div>

                <div className="mb-3 flex items-center justify-between">
                  <div className="t-h2">要求事項明細</div>
                  <span className="t-tiny">何を / いつ / どのように / 誰のために</span>
                </div>

                {addingItem && (
                  <div className="mb-4">
                    <ItemForm
                      projectId={effectiveProjectId}
                      doc={activeDoc}
                      initial={null}
                      onCancel={() => setAddingItem(false)}
                    />
                  </div>
                )}

                <div className="overflow-hidden rounded-xl border" style={{ borderColor: "var(--border)" }}>
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
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeDoc.items.length === 0 && !addingItem ? (
                          <tr>
                            <td colSpan={7} className="py-8 text-center text-sm" style={{ color: "var(--text-3)" }}>
                              要求事項がありません
                            </td>
                          </tr>
                        ) : (
                          activeDoc.items.map((item) => {
                            const im = itemStatusMeta[item.status] ?? itemStatusMeta.not_met;
                            if (editingItemNo === item.item_no) {
                              return (
                                <tr key={item.id}>
                                  <td colSpan={7} className="p-3">
                                    <ItemForm
                                      projectId={effectiveProjectId}
                                      doc={activeDoc}
                                      itemId={item.id}
                                      initial={{
                                        item_no: item.item_no,
                                        what: item.what,
                                        when_required: item.when_required ?? "",
                                        how_required: item.how_required ?? "",
                                        for_whom: item.for_whom ?? "",
                                        status: item.status,
                                      }}
                                      onCancel={() => setEditingItemNo(null)}
                                    />
                                  </td>
                                </tr>
                              );
                            }
                            return (
                              <tr key={item.id}>
                                <td><span className="mono text-xs font-semibold">{item.item_no}</span></td>
                                <td className="font-medium">{item.what}</td>
                                <td>{item.when_required ?? "—"}</td>
                                <td>{item.how_required ?? "—"}</td>
                                <td>{item.for_whom ?? "—"}</td>
                                <td>
                                  <span className={`app-badge app-badge-sq tone-${im.tone}`}>
                                    <CheckCircle className="h-3 w-3" />
                                    {im.label}
                                  </span>
                                </td>
                                <td>
                                  <div className="flex items-center gap-1">
                                    <button className="rounded p-1.5 hover:bg-black/5 dark:hover:bg-white/10" onClick={() => setEditingItemNo(item.item_no)} title="編集">
                                      <Pencil className="h-3.5 w-3.5" />
                                    </button>
                                    <button
                                      className="rounded p-1.5 hover:bg-black/5 dark:hover:bg-white/10"
                                      onClick={() => {
                                        if (window.confirm("この要求事項を削除しますか？")) {
                                          deleteItem.mutate(item.id);
                                        }
                                      }}
                                      title="削除"
                                    >
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="mt-4 flex justify-end">
                  <button className="app-btn" onClick={() => setAddingItem(true)}>
                    <Plus className="h-4 w-4" />
                    要件を追加
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showCreate && (
        <DocCreateDialog projectId={effectiveProjectId} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
