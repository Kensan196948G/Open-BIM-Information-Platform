import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Box,
  Check,
  CheckCircle2,
  ExternalLink,
  FileText,
  Plus,
  Search,
  Shield,
  Upload,
  X,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { demoContainers, demoInformationContainers } from "@/lib/designData";
import {
  EmptyState,
  NamingBadge,
  SecurityPill,
  StatePill,
} from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";
import type {
  ContainerState,
  InformationContainer,
  PaginatedResponse,
} from "@/types";

const stateTabs: Array<ContainerState | "all"> = [
  "all",
  "WIP",
  "Shared",
  "Published",
  "Archived",
];

const transitions: Partial<
  Record<ContainerState, { action: string; label: string; next: ContainerState; icon: typeof ArrowRight }>
> = {
  WIP: { action: "submit", label: "提出", next: "Shared", icon: ArrowRight },
  Shared: { action: "approve", label: "承認", next: "Published", icon: Check },
  Published: { action: "archive", label: "保管", next: "Archived", icon: ArrowRight },
};

// map demoContainers by id for enriched preview data
const demoContainerMap = Object.fromEntries(demoContainers.map((c) => [c.id, c]));

function namingStatus(container: InformationContainer): "pass" | "warn" | "fail" {
  if (container.naming_valid) return "pass";
  return container.naming_issues?.includes("不足") ? "fail" : "warn";
}

const CDE_META: Record<ContainerState, { color: string; label: string }> = {
  WIP: { color: "var(--wip-dot, #f59e0b)", label: "WIP" },
  Shared: { color: "var(--shared-dot, #3b82f6)", label: "Shared" },
  Published: { color: "var(--published-dot, #10b981)", label: "Published" },
  Archived: { color: "var(--archived-dot, #6b7280)", label: "Archived" },
};

function ContainerPreview({
  container,
  projectId,
  onClose,
}: {
  container: InformationContainer;
  projectId: string;
  onClose: () => void;
}) {
  const demo = demoContainerMap[container.id];
  const status = namingStatus(container);
  const meta = CDE_META[container.current_state];

  const infoRows = [
    { label: "識別子", value: container.identifier, mono: true },
    { label: "タイトル", value: container.title, mono: false },
    { label: "種別", value: container.container_type, mono: false },
    { label: "改訂", value: container.current_revision, mono: true },
    ...(demo
      ? [
          { label: "担当組織", value: demo.org, mono: false },
          { label: "ファイル形式", value: demo.ext, mono: true },
          { label: "サイズ", value: demo.size, mono: true },
          { label: "分野", value: demo.discipline, mono: false },
          { label: "更新日時", value: fmtDate(demo.updated, true), mono: true },
        ]
      : []),
  ];

  return (
    <div
      className="flex h-full flex-col overflow-hidden"
      style={{ borderLeft: "1px solid var(--border)" }}
    >
      {/* header */}
      <div
        className="flex shrink-0 items-center justify-between gap-3 p-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Box className="h-4 w-4 shrink-0" style={{ color: "var(--primary)" }} />
          <span className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>
            コンテナ詳細
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatePill state={container.current_state} />
          <button
            className="rounded-lg p-1 transition-colors hover:bg-[var(--surface-3)]"
            onClick={onClose}
          >
            <X className="h-4 w-4" style={{ color: "var(--text-3)" }} />
          </button>
        </div>
      </div>

      {/* scrollable body */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {/* CDE state badge */}
        <div
          className="flex items-center gap-3 rounded-xl px-4 py-3"
          style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
        >
          <span
            className="h-2.5 w-2.5 rounded-full shrink-0"
            style={{ background: meta.color }}
          />
          <div>
            <div className="text-xs font-semibold" style={{ color: "var(--text)" }}>
              CDE 状態: {meta.label}
            </div>
            <div className="t-tiny mt-0.5">ISO 19650 準拠管理下</div>
          </div>
        </div>

        {/* metadata table */}
        <div>
          <div className="t-tiny mb-2 font-medium">基本情報</div>
          <div
            className="overflow-hidden rounded-xl"
            style={{ border: "1px solid var(--border)" }}
          >
            {infoRows.map(({ label, value, mono }, i) => (
              <div
                key={label}
                className="flex gap-3 px-3 py-2"
                style={{
                  background: i % 2 === 0 ? "var(--surface-2)" : undefined,
                  borderBottom:
                    i < infoRows.length - 1 ? "1px solid var(--border)" : undefined,
                }}
              >
                <span className="t-tiny w-24 shrink-0 pt-0.5">{label}</span>
                <span
                  className={`text-xs break-all ${mono ? "mono" : ""}`}
                  style={{ color: "var(--text)" }}
                >
                  {value ?? "-"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* security & naming */}
        <div className="grid grid-cols-2 gap-3">
          <div
            className="rounded-xl p-3 space-y-1.5"
            style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5" style={{ color: "var(--text-3)" }} />
              <span className="t-tiny font-medium">セキュリティ</span>
            </div>
            <SecurityPill level={container.security_level} />
          </div>
          <div
            className="rounded-xl p-3 space-y-1.5"
            style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" style={{ color: "var(--text-3)" }} />
              <span className="t-tiny font-medium">命名規則</span>
            </div>
            <NamingBadge status={status} />
          </div>
        </div>

        {/* naming issues */}
        {container.naming_issues && (
          <div
            className="flex items-start gap-2 rounded-xl px-3 py-2"
            style={{
              background: "var(--warning-bg, #fffbeb)",
              border: "1px solid var(--warning, #f59e0b)",
            }}
          >
            <AlertTriangle
              className="h-4 w-4 mt-0.5 shrink-0"
              style={{ color: "var(--warning-fg, #d97706)" }}
            />
            <span className="text-xs" style={{ color: "var(--warning-fg, #d97706)" }}>
              {container.naming_issues}
            </span>
          </div>
        )}

        {/* integrity status */}
        <div
          className="flex items-center gap-2 rounded-xl px-3 py-2"
          style={
            container.naming_valid
              ? { background: "var(--success-subtle)", border: "1px solid var(--success-border)" }
              : { background: "var(--surface-2)", border: "1px solid var(--border)" }
          }
        >
          {container.naming_valid ? (
            <>
              <CheckCircle2
                className="h-4 w-4 shrink-0"
                style={{ color: "var(--success-fg)" }}
              />
              <span className="text-xs font-medium" style={{ color: "var(--success-fg)" }}>
                命名規則 OK — 全チェック通過
              </span>
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4 shrink-0" style={{ color: "var(--text-3)" }} />
              <span className="text-xs" style={{ color: "var(--text-2)" }}>
                命名規則に問題があります
              </span>
            </>
          )}
        </div>

        {/* open detail link */}
        <Link
          to={`/projects/${projectId}/containers/${container.id}`}
          className="app-btn app-btn-primary flex w-full items-center justify-center gap-2"
        >
          <ExternalLink className="h-4 w-4" />
          コンテナ詳細を開く
        </Link>
      </div>
    </div>
  );
}

export default function ContainersPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [stateFilter, setStateFilter] = useState<ContainerState | "all">(
    (searchParams.get("state") as ContainerState | null) ?? "all",
  );
  const [q, setQ] = useState("");
  const [namingOnly, setNamingOnly] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [title, setTitle] = useState("");
  const [previewId, setPreviewId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["containers", projectId],
    queryFn: () =>
      api
        .get<PaginatedResponse<InformationContainer>>(`/projects/${projectId}/containers`)
        .then((r) => r.data),
    enabled: !!projectId && projectId !== "demo",
  });

  const sourceItems = useMemo(
    () => projectId === "demo" ? demoInformationContainers : (data?.items ?? []),
    [projectId, data?.items],
  );
  const sourceTotal =
    projectId === "demo" ? demoInformationContainers.length : (data?.total ?? 0);
  const loading = projectId === "demo" ? false : isLoading;

  const createMutation = useMutation({
    mutationFn: (body: { identifier: string; title: string }) =>
      api.post(`/projects/${projectId}/containers`, body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["containers", projectId] });
      setShowForm(false);
      setIdentifier("");
      setTitle("");
    },
  });

  const transitionMutation = useMutation({
    mutationFn: ({
      containerId,
      action,
      targetState,
    }: {
      containerId: string;
      action: string;
      targetState: ContainerState;
    }) =>
      api.post(`/projects/${projectId}/containers/${containerId}/transition`, {
        action,
        target_state: targetState,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["containers", projectId] });
    },
  });

  const rows = useMemo(() => {
    let next = sourceItems;
    if (stateFilter !== "all") next = next.filter((c) => c.current_state === stateFilter);
    if (namingOnly) next = next.filter((c) => !c.naming_valid);
    if (q) {
      const f = q.toLowerCase();
      next = next.filter(
        (c) =>
          c.identifier.toLowerCase().includes(f) ||
          c.title.toLowerCase().includes(f),
      );
    }
    return next;
  }, [namingOnly, q, sourceItems, stateFilter]);

  const counts = Object.fromEntries(
    stateTabs.map((state) => [
      state,
      state === "all"
        ? sourceItems.length
        : sourceItems.filter((c) => c.current_state === state).length,
    ]),
  );

  const previewContainer = rows.find((c) => c.id === previewId) ?? null;

  return (
    <div className="flex h-full flex-col" style={{ minHeight: 0 }}>
      {/* page header */}
      <div className="shrink-0 px-5 pt-5 pb-0 sm:px-6">
        <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <h1 className="t-display">情報コンテナ</h1>
            <p className="t-sec mt-1">CDE 管理下の全 {sourceTotal} 件</p>
          </div>
          <div className="flex gap-2">
            <button className="app-btn" onClick={() => navigate(`/projects/${projectId}/upload`)}>
              <Upload className="h-4 w-4" />
              アップロード
            </button>
            <button className="app-btn app-btn-primary" onClick={() => setShowForm(true)}>
              <Plus className="h-4 w-4" />
              コンテナ登録
            </button>
          </div>
        </div>

        <div className="mb-0 flex gap-1 overflow-x-auto border-b" style={{ borderColor: "var(--border)" }}>
          {stateTabs.map((state) => {
            const active = stateFilter === state;
            return (
              <button
                key={state}
                onClick={() => setStateFilter(state)}
                className="relative flex items-center gap-2 px-3 py-2 text-[13px]"
                style={{ color: active ? "var(--text)" : "var(--text-2)", fontWeight: active ? 600 : 450 }}
              >
                {state !== "all" && <span className="app-dot" style={{ background: `var(--${state.toLowerCase()}-dot)` }} />}
                {state === "all" ? "すべて" : state}
                <span className="mono text-[11px]" style={{ color: "var(--text-3)" }}>{counts[state]}</span>
                {active && <span className="absolute inset-x-0 bottom-[-1px] h-0.5 rounded bg-[var(--primary)]" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* filters + form */}
      <div className="shrink-0 px-5 pt-4 sm:px-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="relative min-w-[240px] flex-1 sm:max-w-sm">
            <Search className="absolute left-3 top-2.5 h-4 w-4" style={{ color: "var(--text-3)" }} />
            <input className="app-field pl-9" value={q} onChange={(e) => setQ(e.target.value)} placeholder="識別子・タイトルで検索..." />
          </div>
          <button
            className="app-btn"
            onClick={() => setNamingOnly(!namingOnly)}
            style={namingOnly ? { background: "var(--warning-bg)", borderColor: "var(--warning)", color: "var(--warning-fg)" } : undefined}
          >
            <AlertTriangle className="h-4 w-4" />
            命名要対応
          </button>
        </div>

        {showForm && (
          <form
            className="app-card-pad mb-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (projectId === "demo") {
                setShowForm(false);
                setIdentifier("");
                setTitle("");
              } else {
                createMutation.mutate({ identifier, title });
              }
            }}
          >
            <div className="t-h2 mb-3">新規情報コンテナ</div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input className="app-field mono" required placeholder="識別子 (例: PRJ-XXX-A-01-DOC-001)" value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
              <input className="app-field" required placeholder="タイトル" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div className="mt-3 flex gap-2">
              <button className="app-btn app-btn-primary" disabled={createMutation.isPending}>
                {createMutation.isPending ? "登録中..." : "登録"}
              </button>
              <button type="button" className="app-btn" onClick={() => setShowForm(false)}>
                キャンセル
              </button>
            </div>
          </form>
        )}
      </div>

      {/* main content: table + preview panel */}
      <div
        className="min-h-0 flex-1 overflow-hidden px-5 pb-5 sm:px-6 sm:pb-6"
        style={{
          display: "grid",
          gridTemplateColumns: previewContainer ? "1fr 360px" : "1fr",
          gap: "1rem",
        }}
      >
        {/* table */}
        <div className="app-card min-h-0 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-auto">
            <table className="app-table min-w-[860px]">
              <thead>
                <tr>
                  <th>識別子 / タイトル</th>
                  <th>種別</th>
                  <th>状態</th>
                  <th>改訂</th>
                  <th>命名</th>
                  <th>分類</th>
                  <th style={{ width: 130 }} />
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center" style={{ color: "var(--text-3)" }}>
                      読み込み中...
                    </td>
                  </tr>
                ) : (
                  rows.map((container) => {
                    const transition = transitions[container.current_state];
                    const ActionIcon = transition?.icon;
                    const isSelected = previewId === container.id;
                    return (
                      <tr
                        key={container.id}
                        className="cursor-pointer"
                        style={isSelected ? { background: "var(--primary-subtle)" } : undefined}
                        onClick={() => setPreviewId(isSelected ? null : container.id)}
                      >
                        <td className="max-w-[360px]">
                          <div className="mono truncate text-[12.5px] font-semibold" style={{ color: "var(--text)" }}>{container.identifier}</div>
                          <div className="truncate text-xs" style={{ color: "var(--text-2)" }}>{container.title}</div>
                        </td>
                        <td>
                          <span className="inline-flex items-center gap-2 text-[12.5px]" style={{ color: "var(--text-2)" }}>
                            <FileText className="h-4 w-4" />
                            {container.container_type}
                          </span>
                        </td>
                        <td><StatePill state={container.current_state} /></td>
                        <td><span className="mono text-[12.5px]">{container.current_revision}</span></td>
                        <td><NamingBadge status={namingStatus(container)} /></td>
                        <td><SecurityPill level={container.security_level} /></td>
                        <td onClick={(e) => e.stopPropagation()}>
                          {transition && ActionIcon ? (
                            <button
                              className="app-btn app-btn-sm"
                              disabled={transitionMutation.isPending}
                              onClick={() => {
                                if (projectId !== "demo") {
                                  transitionMutation.mutate({
                                    containerId: container.id,
                                    action: transition.action,
                                    targetState: transition.next,
                                  });
                                }
                              }}
                            >
                              <ActionIcon className="h-3.5 w-3.5" />
                              {transition.label}
                            </button>
                          ) : (
                            <span className="t-tiny">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
          {!loading && rows.length === 0 && (
            <EmptyState icon={<Box className="h-6 w-6" />} title="該当するコンテナがありません" sub="フィルタ条件を変更してください。" />
          )}
          <div className="shrink-0 border-t px-4 py-2 text-right" style={{ borderColor: "var(--border)" }}>
            <Link className="app-btn app-btn-ghost app-btn-sm" to={`/projects/${projectId}/upload`}>
              命名規則ビルダーで登録する
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* right preview panel */}
        {previewContainer && projectId && (
          <div className="app-card min-h-0 overflow-hidden">
            <ContainerPreview
              container={previewContainer}
              projectId={projectId}
              onClose={() => setPreviewId(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
