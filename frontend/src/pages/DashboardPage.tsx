import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  ArrowRight,
  Box,
  CheckCircle,
  FileText,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { listMyPendingApprovals } from "@/api/workflows";
import { listContainers } from "@/api/containers";
import { StatePill } from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";
import type { ContainerState, PaginatedResponse, Project } from "@/types";

const STATE_ORDER: ContainerState[] = ["WIP", "Shared", "Published", "Archived"];

function KpiCard({
  icon: Icon,
  label,
  value,
  unit,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  unit?: string;
  color: string;
}) {
  return (
    <div className="app-card-pad">
      <div className="flex items-center gap-2">
        <span
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: "var(--surface-3)", color }}
        >
          <Icon className="h-4 w-4" />
        </span>
        <span className="t-sec font-medium">{label}</span>
      </div>
      <div className="mt-4 flex items-end justify-between">
        <div className="mono text-[28px] font-semibold leading-none" style={{ color: "var(--text)" }}>
          {value}
          {unit && <span className="ml-1 text-[13px] font-medium" style={{ color: "var(--text-3)" }}>{unit}</span>}
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: projectsData } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
  });
  const project = projectsData?.items[0];

  const { data: containersData } = useQuery({
    queryKey: ["dashboard-containers", project?.id],
    queryFn: () => listContainers(project!.id, { size: 100 }),
    enabled: !!project,
  });
  const { data: pendingApprovals } = useQuery({
    queryKey: ["workflows-mine"],
    queryFn: listMyPendingApprovals,
  });

  const containers = containersData?.items ?? [];
  const total = containersData?.total ?? containers.length;
  const countByState = (state: ContainerState) =>
    containers.filter((c) => c.current_state === state).length;
  const namedContainers = containers.filter((c) => c.naming_valid).length;
  const compliance =
    containers.length > 0 ? Math.round((namedContainers / containers.length) * 100) : 0;
  const bySecurity = (level: string) =>
    containers.filter((c) => c.security_level === level).length;
  const recent = [...containers]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 6);

  if (!project) {
    return (
      <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
        <h1 className="t-display">ダッシュボード</h1>
        <div className="app-card-pad mt-4">
          表示できるプロジェクトがありません。管理者に組織・プロジェクトの設定を依頼してください。
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">ダッシュボード</h1>
          <p className="t-sec mt-1">{project.name} · ISO 19650 BIM 情報管理状況</p>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard icon={Box} label="情報コンテナ" value={total} unit="件" color="var(--primary)" />
        <KpiCard icon={CheckCircle} label="承認待ち" value={pendingApprovals?.length ?? 0} unit="件" color="var(--warning)" />
        <KpiCard icon={ShieldCheck} label="命名規則 適合率" value={compliance} unit="%" color="var(--success)" />
        <KpiCard icon={FileText} label="公開済み" value={countByState("Published")} unit="件" color="var(--published-dot)" />
      </div>

      <div className="mb-4">
        <div className="app-card-pad">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <div className="t-h2">CDE 状態フロー</div>
              <div className="t-tiny mt-1">
                ISO 19650-2 · Common Data Environment ワークフロー
              </div>
            </div>
            <Link className="app-btn app-btn-ghost app-btn-sm" to={`/projects/${project.id}/containers`}>
              コンテナ一覧 <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="grid gap-3 md:grid-cols-[1fr_32px_1fr_32px_1fr_32px_1fr]">
            {STATE_ORDER.map((state, index) => {
              const count = countByState(state);
              return (
                <div className="contents" key={state}>
                  <Link
                    className="rounded-xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md"
                    style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
                    to={`/projects/${project.id}/containers?state=${state}`}
                  >
                    <StatePill state={state} />
                    <div className="mono mt-3 text-[30px] font-semibold" style={{ color: "var(--text)" }}>
                      {count}
                    </div>
                    <div className="t-tiny mt-1">
                      {state === "WIP" && "作業中"}
                      {state === "Shared" && "共有・レビュー"}
                      {state === "Published" && "公開承認済み"}
                      {state === "Archived" && "保管"}
                    </div>
                    <div className="bar mt-3">
                      <i
                        style={{
                          width: `${total > 0 ? (count / total) * 100 : 0}%`,
                          background: `var(--${state.toLowerCase()}-dot)`,
                        }}
                      />
                    </div>
                  </Link>
                  {index < STATE_ORDER.length - 1 && (
                    <div className="hidden items-center justify-center md:flex">
                      <ArrowRight className="h-4 w-4" style={{ color: "var(--text-3)" }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr_1fr]">
        <div className="app-card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="t-h2">承認待ちタスク</div>
            <span className="app-badge app-badge-sq tone-warning">{pendingApprovals?.length ?? 0} 件</span>
          </div>
          {!pendingApprovals?.length ? (
            <div className="px-4 py-8 text-center t-sec">承認待ちのタスクはありません。</div>
          ) : (
            pendingApprovals.slice(0, 8).map((task) => (
              <Link
                key={task.approval_id}
                to="/approvals"
                className="flex gap-3 border-t px-4 py-3 transition hover:bg-[var(--surface-2)]"
                style={{ borderColor: "var(--border-faint)" }}
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[12.5px] font-semibold" style={{ color: "var(--text)" }}>
                    {task.container_title ?? task.project_name}
                  </div>
                  <div className="mono truncate text-[11.5px]" style={{ color: "var(--text-3)" }}>
                    {task.container_identifier ?? task.target_id}
                  </div>
                  <div className="mt-1 flex gap-2">
                    {task.container_state && <StatePill state={task.container_state as ContainerState} />}
                    <span className="t-tiny">{task.project_name}</span>
                  </div>
                </div>
                {task.created_at && (
                  <div className="t-tiny mt-1 shrink-0">作成 {fmtDate(task.created_at)}</div>
                )}
              </Link>
            ))
          )}
        </div>

        <div className="app-card-pad">
          <div className="t-h2 mb-3">最近更新されたコンテナ</div>
          <div className="space-y-3">
            {recent.map((container) => (
              <Link
                key={container.id}
                className="flex gap-3"
                to={`/projects/${project.id}/containers/${container.id}`}
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[12.5px]" style={{ color: "var(--text-2)" }}>
                    <span className="mono font-semibold" style={{ color: "var(--text)" }}>
                      {container.identifier}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <StatePill state={container.current_state} />
                    <span className="t-tiny">{fmtDate(container.updated_at, true)}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="app-card-pad">
          <div className="mb-3 flex items-center justify-between">
            <div className="t-h2">情報分類の内訳</div>
            <ShieldCheck className="h-4 w-4" style={{ color: "var(--text-3)" }} />
          </div>
          {["public", "limited", "confidential", "restricted"].map((level) => (
            <div key={level} className="mb-3 flex items-center justify-between">
              <span className="t-sec">{level}</span>
              <span className="mono text-sm font-semibold">{bySecurity(level)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
