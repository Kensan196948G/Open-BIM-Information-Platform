import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Box,
  Check,
  FileText,
  Plus,
  Search,
  Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import { demoInformationContainers } from "@/lib/designData";
import {
  EmptyState,
  NamingBadge,
  SecurityPill,
  StatePill,
} from "@/components/design/Primitives";
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

function namingStatus(container: InformationContainer): "pass" | "warn" | "fail" {
  if (container.naming_valid) return "pass";
  return container.naming_issues?.includes("不足") ? "fail" : "warn";
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
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["containers", projectId],
    queryFn: () =>
      api
        .get<PaginatedResponse<InformationContainer>>(`/projects/${projectId}/containers`)
        .then((r) => r.data),
    enabled: !!projectId && projectId !== "demo",
  });

  const sourceItems =
    projectId === "demo" ? demoInformationContainers : (data?.items ?? []);
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

  return (
    <div className="mx-auto max-w-[1360px] p-5 sm:p-6">
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

      <div className="mb-4 flex gap-1 overflow-x-auto border-b" style={{ borderColor: "var(--border)" }}>
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

      <div className="app-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="app-table min-w-[980px]">
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
                  return (
                    <tr key={container.id} className="cursor-pointer" onClick={() => navigate(`/projects/${projectId}/containers/${container.id}`)}>
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
      </div>

      <div className="mt-4 text-right">
        <Link className="app-btn app-btn-ghost app-btn-sm" to={`/projects/${projectId}/upload`}>
          命名規則ビルダーで登録する
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
