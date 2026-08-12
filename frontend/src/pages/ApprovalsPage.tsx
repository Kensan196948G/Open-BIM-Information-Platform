import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock, RotateCcw, X } from "lucide-react";
import { actOnApproval, listMyPendingApprovals } from "@/api/workflows";
import { StatePill } from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";
import type { ContainerState } from "@/types";

const ACT_LABEL: Record<string, string> = {
  approved: "承認",
  returned: "差戻し",
  rejected: "却下",
};

const CHECKLIST = [
  "命名規則 ISO 19650-2 に適合",
  "必須メタデータ（Status / Revision / Classification）充足",
  "情報分類とアクセス権限の整合",
  "関連コンテナ・参照文書の整合性",
];

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [projectFilter, setProjectFilter] = useState("all");
  const [toast, setToast] = useState("");

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["workflows-mine"],
    queryFn: listMyPendingApprovals,
  });

  const projects = useMemo(
    () => [...new Set(tasks.map((t) => t.project_id))],
    [tasks],
  );
  const shown =
    projectFilter === "all"
      ? tasks
      : tasks.filter((t) => t.project_id === projectFilter);
  const active =
    tasks.find((t) => t.approval_id === activeId) ?? shown[0] ?? null;

  const actMutation = useMutation({
    mutationFn: ({
      workflowId,
      approvalId,
      result,
    }: {
      workflowId: string;
      approvalId: string;
      result: "approved" | "returned" | "rejected";
    }) => actOnApproval(workflowId, approvalId, result, comment || undefined),
    onSuccess: (_data, variables) => {
      const label = ACT_LABEL[variables.result] ?? "処理";
      setToast(`${active?.container_identifier ?? "タスク"} を${label}しました`);
      setComment("");
      setActiveId(null);
      queryClient.invalidateQueries({ queryKey: ["workflows-mine"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-containers"] });
      setTimeout(() => setToast(""), 2600);
    },
  });

  if (isLoading) {
    return <div className="p-6 t-sec">読み込み中...</div>;
  }

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">承認タスク</h1>
          <p className="t-sec mt-1">
            check / review / approve · authorise 承認点
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            className="rounded-lg border px-3 py-2 text-[13px]"
            style={{
              background: "var(--surface-2)",
              borderColor: "var(--border)",
              color: "var(--text)",
            }}
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            aria-label="プロジェクトで絞り込み"
          >
            <option value="all">すべてのプロジェクト</option>
            {projects.map((id) => (
              <option key={id} value={id}>
                {tasks.find((t) => t.project_id === id)?.project_name ?? id}
              </option>
            ))}
          </select>
        </div>
      </div>

      {shown.length === 0 ? (
        <div className="app-card-pad py-16 text-center">
          <Check className="mx-auto mb-3 h-10 w-10" style={{ color: "var(--success)" }} />
          <div className="t-h2">承認待ちのタスクはありません</div>
          <div className="t-sec mt-1">すべてのレビューが完了しています。</div>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
          <div className="app-card overflow-hidden">
            <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
              <span className="t-h2">キュー</span>
              <span className="app-badge app-badge-sq tone-warning">
                <Clock className="h-3 w-3" />
                {shown.length} 件
              </span>
            </div>
            <div style={{ maxHeight: "calc(100vh - 220px)", overflowY: "auto" }}>
              {shown.map((task) => {
                const selected = task.approval_id === active?.approval_id;
                return (
                  <button
                    key={task.approval_id}
                    className="block w-full border-b p-4 text-left"
                    style={{
                      borderColor: "var(--border-faint)",
                      background: selected ? "var(--surface-2)" : "transparent",
                    }}
                    onClick={() => setActiveId(task.approval_id)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-[13px] font-semibold" style={{ color: "var(--text)" }}>
                          {task.container_title ?? task.project_name}
                        </div>
                        <div className="mono mt-0.5 truncate text-[11.5px]" style={{ color: "var(--text-3)" }}>
                          {task.container_identifier ?? task.target_id}
                        </div>
                      </div>
                      <span className="mono shrink-0 text-[10px]" style={{ color: "var(--text-3)" }}>
                        {task.approval_stage}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <span className="t-tiny truncate">{task.project_name}</span>
                      {task.container_state && <StatePill state={task.container_state as ContainerState} />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {active && (
            <div className="app-card overflow-hidden">
              <div className="flex items-start justify-between gap-3 border-b px-4 py-4" style={{ borderColor: "var(--border)" }}>
                <div className="min-w-0">
                  <div className="mono truncate text-sm font-semibold" style={{ color: "var(--text)" }}>
                    {active.container_identifier ?? active.target_id}
                  </div>
                  <div className="mt-1 truncate text-[13px]" style={{ color: "var(--text-2)" }}>
                    {active.container_title ?? active.project_name}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="app-badge app-badge-sq">{active.project_name}</span>
                    <span className="app-badge app-badge-sq">{active.approval_stage}</span>
                    {active.container_state && <StatePill state={active.container_state as ContainerState} />}
                    {active.created_at && <span className="t-tiny">作成 {fmtDate(active.created_at, true)}</span>}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 p-4 lg:grid-cols-2">
                <div>
                  <div className="t-label mb-2">チェックリスト（ISO 19650 レビュー）</div>
                  <div className="space-y-2">
                    {CHECKLIST.map((item) => (
                      <div key={item} className="flex gap-2 rounded-lg p-2.5" style={{ background: "var(--surface-2)" }}>
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0" style={{ color: "var(--success)" }} />
                        <span className="text-[12px]" style={{ color: "var(--text-2)" }}>{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="t-label mb-2 block" htmlFor="approval-comment">
                    コメント
                  </label>
                  <textarea
                    id="approval-comment"
                    className="min-h-[110px] w-full rounded-lg border px-3 py-2 text-[13px]"
                    style={{
                      background: "var(--surface-2)",
                      borderColor: "var(--border)",
                      color: "var(--text)",
                    }}
                    placeholder="レビュー結果・指摘事項を記入"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                  />
                  <div className="mt-3 grid gap-2">
                    <button
                      className="app-btn app-btn-primary"
                      disabled={actMutation.isPending}
                      onClick={() =>
                        actMutation.mutate({
                          workflowId: active.workflow_id,
                          approvalId: active.approval_id,
                          result: "approved",
                        })
                      }
                    >
                      <Check className="h-4 w-4" />
                      承認して公開
                    </button>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        className="app-btn"
                        disabled={actMutation.isPending}
                        onClick={() =>
                          actMutation.mutate({
                            workflowId: active.workflow_id,
                            approvalId: active.approval_id,
                            result: "returned",
                          })
                        }
                      >
                        <RotateCcw className="h-4 w-4" />
                        差戻し
                      </button>
                      <button
                        className="app-btn"
                        disabled={actMutation.isPending}
                        onClick={() =>
                          actMutation.mutate({
                            workflowId: active.workflow_id,
                            approvalId: active.approval_id,
                            result: "rejected",
                          })
                        }
                      >
                        <X className="h-4 w-4" />
                        却下
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {toast && (
        <div
          role="status"
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium shadow-lg"
          style={{ background: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--text)" }}
        >
          <Check className="h-4 w-4" />
          {toast}
        </div>
      )}
    </div>
  );
}
