import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ClipboardCheck,
  Clock,
  FileWarning,
} from "lucide-react";
import { reportsApi } from "@/api/reports";
import { api } from "@/lib/api";
import type { PaginatedResponse, Project } from "@/types";

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
        <div
          className="mono text-[28px] font-semibold leading-none"
          style={{ color: "var(--text)" }}
        >
          {value}
          {unit && (
            <span
              className="ml-1 text-[13px] font-medium"
              style={{ color: "var(--text-3)" }}
            >
              {unit}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

const violationTypeLabel: Record<string, string> = {
  naming_non_compliant: "命名規則違反",
  rejected: "却下",
};

export default function ReportsPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [thresholdHours, setThresholdHours] = useState<number>(72);

  const { data: projectsData } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
    select: (data) => data.items,
  });

  const projects = projectsData ?? [];
  const projectId = selectedProjectId || projects[0]?.id || "";

  const { data: namingViolations, isLoading: namingLoading } = useQuery({
    queryKey: ["reports", "naming-violations", projectId],
    queryFn: () => reportsApi.getNamingViolations(projectId),
    enabled: !!projectId,
  });

  const { data: approvalDelays, isLoading: delaysLoading } = useQuery({
    queryKey: ["reports", "approval-delays", projectId, thresholdHours],
    queryFn: () => reportsApi.getApprovalDelays(projectId, thresholdHours),
    enabled: !!projectId,
  });

  const { data: requirementsStatus, isLoading: reqLoading } = useQuery({
    queryKey: ["reports", "requirements-status", projectId],
    queryFn: () => reportsApi.getRequirementsStatus(projectId),
    enabled: !!projectId,
  });

  const avgFulfillment = useMemo(() => {
    const items = requirementsStatus?.items ?? [];
    if (items.length === 0) return 0;
    const sum = items.reduce((acc, i) => acc + i.fulfillment_rate, 0);
    return Math.round((sum / items.length) * 100);
  }, [requirementsStatus]);

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">監査・コンプライアンスレポート</h1>
          <p className="t-sec mt-1">
            命名規則違反・却下、承認遅延、要求充足率の集計
          </p>
        </div>
        <select
          className="rounded-lg border px-3 py-2 text-sm"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border)",
            color: "var(--text)",
          }}
          value={projectId}
          onChange={(e) => setSelectedProjectId(e.target.value)}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.code} · {p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <KpiCard
          icon={FileWarning}
          label="命名違反・却下"
          value={namingViolations?.total ?? 0}
          unit="件"
          color="var(--danger-fg, #dc2626)"
        />
        <KpiCard
          icon={Clock}
          label={`承認遅延（${thresholdHours}h超）`}
          value={approvalDelays?.total ?? 0}
          unit="件"
          color="var(--warning)"
        />
        <KpiCard
          icon={ClipboardCheck}
          label="要求事項 平均充足率"
          value={avgFulfillment}
          unit="%"
          color="var(--success)"
        />
      </div>

      {!projectId && (
        <div
          className="app-card-pad text-center text-sm"
          style={{ color: "var(--text-3)" }}
        >
          表示できるプロジェクトがありません。
        </div>
      )}

      {projectId && (
        <>
          {/* 命名規則違反・却下レポート */}
          <div className="app-card mb-4 overflow-hidden">
            <div
              className="flex items-center justify-between border-b px-4 py-3"
              style={{ borderColor: "var(--border)" }}
            >
              <span className="t-h2">命名規則違反・却下コンテナ</span>
              <span className="t-tiny">{namingViolations?.total ?? 0} 件</span>
            </div>
            {namingLoading ? (
              <div
                className="px-4 py-8 text-center text-sm"
                style={{ color: "var(--text-3)" }}
              >
                読み込み中...
              </div>
            ) : (namingViolations?.items.length ?? 0) === 0 ? (
              <div
                className="px-4 py-8 text-center text-sm"
                style={{ color: "var(--text-3)" }}
              >
                違反・却下されたコンテナはありません
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="app-table min-w-[860px]">
                  <thead>
                    <tr>
                      <th>識別子</th>
                      <th>タイトル</th>
                      <th>種別</th>
                      <th>理由</th>
                      <th>日時</th>
                      <th>現在の担当者</th>
                    </tr>
                  </thead>
                  <tbody>
                    {namingViolations?.items.map((item) => (
                      <tr key={`${item.container_id}-${item.violation_type}`}>
                        <td className="mono text-xs">{item.identifier}</td>
                        <td className="font-medium">{item.title}</td>
                        <td>
                          <span
                            className={`app-badge app-badge-sq ${item.violation_type === "rejected" ? "tone-danger" : "tone-warning"}`}
                          >
                            <AlertTriangle className="h-3 w-3" />
                            {violationTypeLabel[item.violation_type] ??
                              item.violation_type}
                          </span>
                        </td>
                        <td>{item.reason ?? "—"}</td>
                        <td className="mono text-xs">
                          {item.occurred_at ?? "—"}
                        </td>
                        <td className="mono text-xs">
                          {item.current_assignee_id ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 承認遅延レポート */}
          <div className="app-card mb-4 overflow-hidden">
            <div
              className="flex items-center justify-between border-b px-4 py-3"
              style={{ borderColor: "var(--border)" }}
            >
              <span className="t-h2">承認遅延ワークフロー</span>
              <label
                className="flex items-center gap-2 text-xs"
                style={{ color: "var(--text-3)" }}
              >
                閾値（時間）
                <input
                  type="number"
                  min={1}
                  className="app-field h-8 w-20"
                  value={thresholdHours}
                  onChange={(e) =>
                    setThresholdHours(Number(e.target.value) || 72)
                  }
                />
              </label>
            </div>
            {delaysLoading ? (
              <div
                className="px-4 py-8 text-center text-sm"
                style={{ color: "var(--text-3)" }}
              >
                読み込み中...
              </div>
            ) : (approvalDelays?.items.length ?? 0) === 0 ? (
              <div
                className="px-4 py-8 text-center text-sm"
                style={{ color: "var(--text-3)" }}
              >
                遅延している承認ワークフローはありません
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="app-table min-w-[860px]">
                  <thead>
                    <tr>
                      <th>ワークフロー種別</th>
                      <th>対象コンテナ</th>
                      <th>経過時間</th>
                      <th>担当者</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvalDelays?.items.map((item) => (
                      <tr key={item.workflow_id}>
                        <td>{item.workflow_type}</td>
                        <td className="mono text-xs">
                          {item.container_identifier ?? item.target_id}
                          {item.container_title
                            ? ` · ${item.container_title}`
                            : ""}
                        </td>
                        <td>
                          <span className="app-badge app-badge-sq tone-warning">
                            <Clock className="h-3 w-3" />
                            {item.elapsed_hours}h
                          </span>
                        </td>
                        <td className="mono text-xs">
                          {item.assignees
                            .map((a) => a.assignee_id)
                            .join(", ") || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 要求事項充足率レポート */}
          <div className="app-card overflow-hidden">
            <div
              className="flex items-center justify-between border-b px-4 py-3"
              style={{ borderColor: "var(--border)" }}
            >
              <span className="t-h2">要求事項 充足状況</span>
              <span className="t-tiny">
                {requirementsStatus?.total ?? 0} 文書
              </span>
            </div>
            {reqLoading ? (
              <div
                className="px-4 py-8 text-center text-sm"
                style={{ color: "var(--text-3)" }}
              >
                読み込み中...
              </div>
            ) : (requirementsStatus?.items.length ?? 0) === 0 ? (
              <div
                className="px-4 py-8 text-center text-sm"
                style={{ color: "var(--text-3)" }}
              >
                要求文書がありません
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="app-table min-w-[860px]">
                  <thead>
                    <tr>
                      <th>文書種別</th>
                      <th>タイトル</th>
                      <th>改訂</th>
                      <th>充足</th>
                      <th>一部充足</th>
                      <th>未充足</th>
                      <th>充足率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requirementsStatus?.items.map((item) => (
                      <tr key={item.document_id}>
                        <td>
                          <span
                            className="mono rounded-md px-2 py-0.5 text-xs font-bold"
                            style={{ background: "var(--surface-3)" }}
                          >
                            {item.doc_type}
                          </span>
                        </td>
                        <td className="font-medium">{item.title}</td>
                        <td className="mono text-xs">{item.revision}</td>
                        <td>{item.met_count}</td>
                        <td>{item.partial_count}</td>
                        <td>{item.not_met_count}</td>
                        <td className="mono text-xs">
                          {Math.round(item.fulfillment_rate * 100)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
