import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import {
  ArrowRight,
  Box,
  Calendar,
  Check,
  CheckCircle,
  Download,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { approvals, demoContainers, demoProject, stateOrder } from "@/lib/designData";
import { Avatar, StatePill } from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";
import type { ContainerState, PaginatedResponse, Project } from "@/types";

function stateCount(state: ContainerState) {
  return demoContainers.filter((c) => c.state === state).length;
}

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
        <span className="app-badge app-badge-sq tone-success">+6.2%</span>
      </div>
    </div>
  );
}

function CdeFlow({ projectId }: { projectId?: string }) {
  const navigate = useNavigate();
  const total = demoContainers.length;
  return (
    <div className="app-card-pad">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="t-h2">CDE 状態フロー</div>
          <div className="t-tiny mt-1">
            ISO 19650-2 · Common Data Environment ワークフロー
          </div>
        </div>
        <button
          className="app-btn app-btn-ghost app-btn-sm"
          onClick={() => projectId && navigate(`/projects/${projectId}/containers`)}
        >
          コンテナ一覧 <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="grid gap-3 md:grid-cols-[1fr_32px_1fr_32px_1fr_32px_1fr]">
        {stateOrder.map((state, index) => {
          const count = stateCount(state);
          const key = state.toLowerCase();
          return (
            <div className="contents" key={state}>
              <button
                className="rounded-xl border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-md"
                style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
                onClick={() => projectId && navigate(`/projects/${projectId}/containers?state=${state}`)}
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
                  <i style={{ width: `${(count / total) * 100}%`, background: `var(--${key}-dot)` }} />
                </div>
              </button>
              {index < stateOrder.length - 1 && (
                <div className="hidden items-center justify-center md:flex">
                  <ArrowRight className="h-4 w-4" style={{ color: "var(--text-3)" }} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
  });
  const project = projects?.items[0] ?? demoProject;

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">ダッシュボード</h1>
          <p className="t-sec mt-1">{project.name} · ISO 19650 BIM 情報管理状況</p>
        </div>
        <div className="flex gap-2">
          <button className="app-btn app-btn-sm">
            <Calendar className="h-3.5 w-3.5" />
            過去30日
          </button>
          <button className="app-btn app-btn-sm">
            <Download className="h-3.5 w-3.5" />
            レポート出力
          </button>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard icon={Box} label="情報コンテナ" value={demoContainers.length} unit="件" color="var(--primary)" />
        <KpiCard icon={CheckCircle} label="承認待ち" value={approvals.length} unit="件" color="var(--warning)" />
        <KpiCard icon={ShieldCheck} label="命名規則 適合率" value="94" unit="%" color="var(--success)" />
        <KpiCard icon={Check} label="今週の公開" value={stateCount("Published")} unit="件" color="var(--published-dot)" />
      </div>

      <div className="mb-4">
        <CdeFlow projectId={project.id} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr_1fr]">
        <div className="app-card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="t-h2">承認待ちタスク</div>
            <span className="app-badge app-badge-sq tone-warning">{approvals.length} 件</span>
          </div>
          {approvals.map((task) => (
            <div key={task.id} className="flex gap-3 border-t px-4 py-3" style={{ borderColor: "var(--border-faint)" }}>
              <Avatar user={task.requestedBy} size={30} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-[12.5px] font-semibold" style={{ color: "var(--text)" }}>{task.title}</div>
                <div className="mono truncate text-[11.5px]" style={{ color: "var(--text-3)" }}>{task.identifier}</div>
                <div className="mt-1 flex gap-2">
                  <StatePill state={task.from} />
                  <ArrowRight className="h-4 w-4" style={{ color: "var(--text-3)" }} />
                  <StatePill state={task.to} />
                </div>
              </div>
              <div className="shrink-0 text-right">
                <span className={`app-badge app-badge-sq tone-${task.priority === "high" ? "danger" : "warning"}`}>
                  優先度 {task.priority === "high" ? "高" : "中"}
                </span>
                <div className="t-tiny mt-1">期限 {fmtDate(task.due)}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="app-card-pad">
          <div className="t-h2 mb-3">最近のアクティビティ</div>
          <div className="space-y-3">
            {demoContainers.slice(0, 5).map((container) => (
              <div key={container.id} className="flex gap-3">
                <Avatar user={container.owner} size={28} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[12.5px]" style={{ color: "var(--text-2)" }}>
                    <span className="mono font-semibold" style={{ color: "var(--text)" }}>{container.identifier}</span>
                    を更新
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <StatePill state={container.state} />
                    <span className="t-tiny">{container.updated.slice(5, 16).replace("T", " ")}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="app-card-pad">
          <div className="mb-3 flex items-center justify-between">
            <div className="t-h2">情報分類の内訳</div>
            <ShieldCheck className="h-4 w-4" style={{ color: "var(--text-3)" }} />
          </div>
          {["public", "limited", "confidential", "restricted"].map((level) => {
            const count = demoContainers.filter((c) => c.security === level).length;
            return (
              <div key={level} className="mb-3 flex items-center justify-between">
                <span className="t-sec">{level}</span>
                <span className="mono text-sm font-semibold">{count}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
