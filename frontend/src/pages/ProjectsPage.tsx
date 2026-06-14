import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Calendar,
  Clock,
  FolderOpen,
  Package,
  Plus,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { Avatar } from "@/components/design/Primitives";
import { demoProjects, designUsers } from "@/lib/designData";
import type { PaginatedResponse, Project, ProjectStatus } from "@/types";

const STATUS_META: Record<
  ProjectStatus,
  { tone: string; label: string; dot: string }
> = {
  active: { tone: "success", label: "稼働中", dot: "var(--published-dot)" },
  suspended: { tone: "warning", label: "停止中", dot: "var(--archived-dot)" },
  completed: { tone: "info", label: "完了", dot: "var(--shared-dot)" },
  archived: { tone: "neutral", label: "アーカイブ", dot: "var(--wip-dot)" },
};

const CDE_STATES = ["wip", "shared", "published", "archived"] as const;
const CDE_LABELS: Record<string, string> = {
  wip: "WIP",
  shared: "Shared",
  published: "Published",
  archived: "Archived",
};

function projectDist(index: number) {
  const vals = [22 + index * 3, 17, 49, 12];
  const total = vals.reduce((a, b) => a + b, 0);
  return vals.map((v) => ({ pct: (v / total) * 100, count: v * 8 }));
}

function ProjectDetail({
  project,
  index,
  onClose,
}: {
  project: Project;
  index: number;
  onClose: () => void;
}) {
  const status = STATUS_META[project.status];
  const dist = projectDist(index);
  const members = designUsers.slice(0, 4 + (index % 3));
  const containers = (420 + index * 86).toLocaleString();
  const compliance = 91 + (index % 7);
  const pendingApprovals = index < 2 ? index + 2 : 0;

  const recentActivity = [
    {
      action: "コンテナ共有申請",
      user: designUsers[index % 5].name,
      at: "2時間前",
    },
    {
      action: "命名規則更新",
      user: designUsers[(index + 1) % 5].name,
      at: "5時間前",
    },
    { action: "承認完了", user: designUsers[(index + 2) % 5].name, at: "昨日" },
    {
      action: "新規コンテナ作成",
      user: designUsers[(index + 3) % 5].name,
      at: "昨日",
    },
  ];

  return (
    <div
      className="flex h-full flex-col overflow-hidden"
      style={{ borderLeft: "1px solid var(--border)" }}
    >
      {/* header */}
      <div
        className="flex shrink-0 items-start justify-between gap-3 p-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="mono flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)] text-xs font-bold text-white">
              {project.code}
            </span>
            <h2
              className="truncate text-[15px] font-semibold"
              style={{ color: "var(--text)" }}
            >
              {project.name}
            </h2>
          </div>
          <p className="t-sec mt-1 text-xs line-clamp-2">
            {project.description || project.applied_standard}
          </p>
        </div>
        <button
          className="shrink-0 rounded-lg p-1 transition-colors hover:bg-[var(--surface-3)]"
          onClick={onClose}
        >
          <X className="h-4 w-4" style={{ color: "var(--text-3)" }} />
        </button>
      </div>

      {/* scrollable body */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {/* status badges */}
        <div className="flex flex-wrap gap-2">
          <span className={`app-badge app-badge-sq tone-${status.tone}`}>
            <span className="app-dot" style={{ background: status.dot }} />
            {status.label}
          </span>
          <span className="app-badge app-badge-sq">
            <Calendar className="h-3 w-3" />
            {project.start_date} 〜 {project.end_date}
          </span>
          {pendingApprovals > 0 && (
            <span className="app-badge app-badge-sq tone-warning">
              <Clock className="h-3 w-3" />
              承認待ち {pendingApprovals}
            </span>
          )}
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-3 gap-2">
          {[
            {
              icon: <Package className="h-4 w-4" />,
              value: containers,
              label: "コンテナ",
            },
            {
              icon: <Users className="h-4 w-4" />,
              value: String(members.length),
              label: "メンバー",
            },
            {
              icon: <TrendingUp className="h-4 w-4" />,
              value: `${compliance}%`,
              label: "命名適合率",
            },
          ].map(({ icon, value, label }) => (
            <div
              key={label}
              className="rounded-xl p-3 text-center"
              style={{ background: "var(--surface-2)" }}
            >
              <div
                className="mb-1 flex justify-center"
                style={{ color: "var(--primary)" }}
              >
                {icon}
              </div>
              <div
                className="mono text-base font-bold"
                style={{ color: "var(--text)" }}
              >
                {value}
              </div>
              <div className="t-tiny">{label}</div>
            </div>
          ))}
        </div>

        {/* CDE 状態分布 */}
        <div>
          <div className="t-tiny mb-2 font-medium">CDE 状態分布</div>
          <div className="flex h-2.5 overflow-hidden rounded-full">
            {CDE_STATES.map((state, i) => (
              <div
                key={state}
                style={{
                  width: `${dist[i].pct}%`,
                  background: `var(--${state}-dot)`,
                }}
              />
            ))}
          </div>
          <div className="mt-2 grid grid-cols-4 gap-1">
            {CDE_STATES.map((state, i) => (
              <div key={state} className="text-center">
                <div
                  className="mono text-xs font-semibold"
                  style={{ color: "var(--text)" }}
                >
                  {dist[i].count.toLocaleString()}
                </div>
                <div className="flex items-center justify-center gap-1 t-tiny">
                  <span
                    className="inline-block h-1.5 w-1.5 rounded-full"
                    style={{ background: `var(--${state}-dot)` }}
                  />
                  {CDE_LABELS[state]}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 命名適合率 */}
        <div>
          <div className="mb-1 flex justify-between">
            <span className="t-tiny font-medium">命名適合率</span>
            <span
              className="mono text-[11.5px] font-bold"
              style={{ color: "var(--success-fg)" }}
            >
              {compliance}%
            </span>
          </div>
          <div className="bar">
            <i
              style={{ width: `${compliance}%`, background: "var(--success)" }}
            />
          </div>
        </div>

        {/* メンバー */}
        <div>
          <div className="t-tiny mb-2 font-medium">プロジェクトメンバー</div>
          <div className="space-y-2">
            {members.map((u) => (
              <div key={u.id} className="flex items-center gap-2">
                <Avatar user={u} size={26} />
                <div className="min-w-0 flex-1">
                  <div
                    className="truncate text-xs font-medium"
                    style={{ color: "var(--text)" }}
                  >
                    {u.name}
                  </div>
                  <div className="t-tiny truncate">
                    {u.role} · {u.org}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 最近の活動 */}
        <div>
          <div className="t-tiny mb-2 font-medium">最近の活動</div>
          <div className="space-y-2">
            {recentActivity.map((a, i) => (
              <div key={i} className="flex items-start gap-2">
                <span
                  className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: "var(--primary)" }}
                />
                <div className="min-w-0 flex-1">
                  <span className="text-xs" style={{ color: "var(--text)" }}>
                    {a.action}
                  </span>
                  <span className="t-sec text-xs"> — {a.user}</span>
                </div>
                <span className="t-tiny shrink-0">{a.at}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* footer actions */}
      <div
        className="shrink-0 p-4 pt-3"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <Link
          className="app-btn app-btn-primary w-full justify-center"
          to={`/projects/${project.id}/containers`}
        >
          <FolderOpen className="h-4 w-4" />
          コンテナ一覧を開く
        </Link>
      </div>
    </div>
  );
}

export default function ProjectsPage() {
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<ProjectStatus | "all">("all");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (body: { name: string; code: string }) =>
      api.post<Project>("/projects", body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setName("");
      setCode("");
    },
  });

  const projects = data?.items?.length
    ? data.items
    : import.meta.env.VITE_MOCK_MODE === "true"
      ? demoProjects
      : [];
  const shown = projects.filter((p) => filter === "all" || p.status === filter);
  const selectedProject = shown.find((p) => p.id === selectedId) ?? null;
  const selectedIndex = shown.findIndex((p) => p.id === selectedId);

  return (
    <div className="flex h-full flex-col" style={{ minHeight: 0 }}>
      {/* top bar */}
      <div className="shrink-0 px-5 pb-3 pt-5 sm:px-6">
        <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <h1 className="t-display">プロジェクト</h1>
            <p className="t-sec mt-1">
              全 {data?.total ?? projects.length} 件 · ISO 19650 情報管理
            </p>
          </div>
          <button
            className="app-btn app-btn-primary"
            onClick={() => setShowForm(true)}
          >
            <Plus className="h-4 w-4" />
            新規プロジェクト
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {(["all", "active", "suspended", "completed"] as const).map((key) => (
            <button
              key={key}
              className="app-btn app-btn-sm"
              style={
                filter === key
                  ? {
                      background: "var(--primary-subtle)",
                      borderColor: "var(--primary-border)",
                      color: "var(--primary-text)",
                    }
                  : undefined
              }
              onClick={() => setFilter(key)}
            >
              {key === "all" ? "すべて" : STATUS_META[key].label}
              <span className="mono text-[11px] opacity-70">
                {key === "all"
                  ? projects.length
                  : projects.filter((p) => p.status === key).length}
              </span>
            </button>
          ))}
        </div>
      </div>

      {showForm && (
        <div className="shrink-0 px-5 pb-3 sm:px-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate({ name, code });
            }}
            className="app-card-pad"
          >
            <div className="t-h2 mb-3">新規プロジェクト</div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="app-field"
                required
                placeholder="プロジェクト名"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <input
                className="app-field mono"
                required
                placeholder="プロジェクトコード (例: PROJ-001)"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>
            <div className="mt-3 flex gap-2">
              <button
                className="app-btn app-btn-primary"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? "作成中..." : "作成"}
              </button>
              <button
                type="button"
                className="app-btn"
                onClick={() => setShowForm(false)}
              >
                キャンセル
              </button>
            </div>
          </form>
        </div>
      )}

      {/* main content area: list + detail */}
      <div
        className="flex min-h-0 flex-1 gap-0 overflow-hidden px-5 pb-5 sm:px-6 sm:pb-6"
        style={{
          display: "grid",
          gridTemplateColumns: selectedProject ? "380px 1fr" : "1fr",
        }}
      >
        {/* project list */}
        <div
          className="overflow-y-auto pr-4"
          style={selectedProject ? { paddingRight: "1rem" } : {}}
        >
          {isLoading ? (
            <div
              className="app-card py-14 text-center"
              style={{ color: "var(--text-3)" }}
            >
              読み込み中...
            </div>
          ) : shown.length === 0 ? (
            <div
              className="app-card py-16 text-center"
              style={{ color: "var(--text-3)" }}
            >
              <FolderOpen className="mx-auto mb-3 h-12 w-12" />
              プロジェクトがありません。
            </div>
          ) : (
            <div className="space-y-3">
              {shown.map((project, index) => {
                const status = STATUS_META[project.status];
                const dist = projectDist(index);
                const isSelected = selectedId === project.id;
                return (
                  <button
                    key={project.id}
                    className="app-card w-full overflow-hidden text-left transition-all"
                    style={
                      isSelected
                        ? {
                            borderColor: "var(--primary-border)",
                            background: "var(--primary-subtle)",
                          }
                        : undefined
                    }
                    onClick={() =>
                      setSelectedId(isSelected ? null : project.id)
                    }
                  >
                    <div className="flex gap-3 p-4">
                      <span className="mono flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-xs font-bold text-white">
                        {project.code}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h2
                            className="truncate text-[14px] font-semibold"
                            style={{ color: "var(--text)" }}
                          >
                            {project.name}
                          </h2>
                          <span
                            className={`app-badge app-badge-sq tone-${status.tone}`}
                          >
                            <span
                              className="app-dot"
                              style={{ background: status.dot }}
                            />
                            {status.label}
                          </span>
                        </div>
                        <p className="t-sec mt-0.5 line-clamp-1 text-xs">
                          {project.description || project.applied_standard}
                        </p>
                      </div>
                    </div>

                    <div className="px-4 pb-3">
                      <div className="mb-1 flex justify-between">
                        <span className="t-tiny">CDE 状態</span>
                        <span className="t-tiny mono">
                          {(420 + index * 86).toLocaleString()} コンテナ
                        </span>
                      </div>
                      <div className="flex h-1.5 overflow-hidden rounded-full">
                        {CDE_STATES.map((state, i) => (
                          <div
                            key={state}
                            style={{
                              width: `${dist[i].pct}%`,
                              background: `var(--${state}-dot)`,
                            }}
                          />
                        ))}
                      </div>
                    </div>

                    <div
                      className="flex items-center gap-3 border-t px-4 py-2.5"
                      style={{ borderColor: "var(--border)" }}
                    >
                      <div className="flex items-center -space-x-2">
                        {designUsers.slice(0, 3).map((u) => (
                          <Avatar key={u.id} user={u} size={22} />
                        ))}
                      </div>
                      <span className="t-tiny flex-1">
                        {project.start_date} 〜 {project.end_date}
                      </span>
                      {index < 2 && (
                        <span className="app-badge app-badge-sq tone-warning h-6 text-[11px]">
                          <Clock className="h-2.5 w-2.5" />
                          承認 {index + 2}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* right detail panel */}
        {selectedProject && (
          <div className="app-card min-h-0 overflow-hidden">
            <ProjectDetail
              project={selectedProject}
              index={selectedIndex}
              onClose={() => setSelectedId(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
