import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Clock, FolderOpen, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Avatar } from "@/components/design/Primitives";
import { designUsers } from "@/lib/designData";
import type { PaginatedResponse, Project, ProjectStatus } from "@/types";

const STATUS_META: Record<ProjectStatus, { tone: string; label: string; dot: string }> = {
  active: { tone: "success", label: "稼働中", dot: "var(--published-dot)" },
  suspended: { tone: "warning", label: "停止中", dot: "var(--archived-dot)" },
  completed: { tone: "info", label: "完了", dot: "var(--shared-dot)" },
  archived: { tone: "neutral", label: "アーカイブ", dot: "var(--wip-dot)" },
};

export default function ProjectsPage() {
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<ProjectStatus | "all">("all");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
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

  const projects = data?.items ?? [];
  const shown = projects.filter((p) => filter === "all" || p.status === filter);

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">プロジェクト</h1>
          <p className="t-sec mt-1">全 {data?.total ?? 0} 件 · ISO 19650 情報管理</p>
        </div>
        <button className="app-btn app-btn-primary" onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4" />
          新規プロジェクト
        </button>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
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
              {key === "all" ? projects.length : projects.filter((p) => p.status === key).length}
            </span>
          </button>
        ))}
      </div>

      {showForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate({ name, code });
          }}
          className="app-card-pad mb-5"
        >
          <div className="t-h2 mb-3">新規プロジェクト</div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input className="app-field" required placeholder="プロジェクト名" value={name} onChange={(e) => setName(e.target.value)} />
            <input className="app-field mono" required placeholder="プロジェクトコード (例: PROJ-001)" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="mt-3 flex gap-2">
            <button className="app-btn app-btn-primary" disabled={createMutation.isPending}>
              {createMutation.isPending ? "作成中..." : "作成"}
            </button>
            <button type="button" className="app-btn" onClick={() => setShowForm(false)}>
              キャンセル
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="app-card py-14 text-center" style={{ color: "var(--text-3)" }}>読み込み中...</div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {shown.map((project, index) => {
            const status = STATUS_META[project.status];
            const dist = [22 + index * 3, 17, 49, 12];
            const total = dist.reduce((a, b) => a + b, 0);
            return (
              <div key={project.id} className="app-card overflow-hidden">
                <div className="flex gap-3 p-4">
                  <span className="mono flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-sm font-bold text-white">
                    {project.code}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h2 className="truncate text-[15px] font-semibold" style={{ color: "var(--text)" }}>{project.name}</h2>
                      <span className={`app-badge app-badge-sq tone-${status.tone}`}>
                        <span className="app-dot" style={{ background: status.dot }} />
                        {status.label}
                      </span>
                    </div>
                    <p className="t-sec mt-1 line-clamp-2">
                      {project.description || project.applied_standard}
                    </p>
                  </div>
                </div>

                <div className="px-4 pb-3">
                  <div className="mb-1 flex justify-between">
                    <span className="t-tiny">CDE 状態分布</span>
                    <span className="t-tiny mono">{(420 + index * 86).toLocaleString()} コンテナ</span>
                  </div>
                  <div className="flex h-2 overflow-hidden rounded-full">
                    {(["wip", "shared", "published", "archived"] as const).map((state, i) => (
                      <div key={state} style={{ width: `${(dist[i] / total) * 100}%`, background: `var(--${state}-dot)` }} />
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-3 border-t px-4 py-3" style={{ borderColor: "var(--border)" }}>
                  <div className="min-w-[130px] flex-1">
                    <div className="mb-1 flex justify-between">
                      <span className="t-tiny">命名適合率</span>
                      <span className="mono text-[11.5px] font-bold" style={{ color: "var(--success-fg)" }}>94%</span>
                    </div>
                    <div className="bar"><i style={{ width: "94%", background: "var(--success)" }} /></div>
                  </div>
                  <div className="hidden items-center -space-x-2 sm:flex">
                    {designUsers.slice(0, 4).map((u) => <Avatar key={u.id} user={u} size={24} />)}
                  </div>
                  <Link className="app-btn app-btn-sm" to={`/projects/${project.id}/containers`}>
                    開く
                  </Link>
                  {index < 2 && (
                    <span className="app-badge app-badge-sq tone-warning h-7">
                      <Clock className="h-3 w-3" />
                      承認 {index + 2}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
          {shown.length === 0 && (
            <div className="app-card py-16 text-center" style={{ color: "var(--text-3)" }}>
              <FolderOpen className="mx-auto mb-3 h-12 w-12" />
              プロジェクトがありません。
            </div>
          )}
        </div>
      )}
    </div>
  );
}
