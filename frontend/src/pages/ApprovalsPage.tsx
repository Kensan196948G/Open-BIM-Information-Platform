import { useState } from "react";
import { Check, Clock, ExternalLink, RotateCcw, X } from "lucide-react";
import { approvals, userById } from "@/lib/designData";
import { Avatar, SecurityPill, StatePill, fmtDate } from "@/components/design/Primitives";

export default function ApprovalsPage() {
  const [tasks, setTasks] = useState([...approvals]);
  const [activeId, setActiveId] = useState(tasks[0]?.id);
  const [comment, setComment] = useState("");
  const active = tasks.find((task) => task.id === activeId) ?? tasks[0];

  const complete = () => {
    if (!active) return;
    const next = tasks.filter((task) => task.id !== active.id);
    setTasks(next);
    setActiveId(next[0]?.id);
    setComment("");
  };

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">承認タスク</h1>
          <p className="t-sec mt-1">check / review / approve · authorise 承認点</p>
        </div>
        <span className="app-badge app-badge-sq tone-warning h-7">
          <Clock className="h-3.5 w-3.5" />
          {tasks.length} 件
        </span>
      </div>

      {tasks.length === 0 ? (
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
              <span className="app-badge app-badge-sq tone-warning">{tasks.length} 件</span>
            </div>
            {tasks.map((task) => {
              const selected = task.id === active?.id;
              return (
                <button
                  key={task.id}
                  className="block w-full border-b p-4 text-left"
                  style={{
                    borderColor: "var(--border-faint)",
                    borderLeft: selected ? "3px solid var(--primary)" : "3px solid transparent",
                    background: selected ? "var(--primary-subtle)" : "transparent",
                  }}
                  onClick={() => setActiveId(task.id)}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span className={`app-badge app-badge-sq tone-${task.priority === "high" ? "danger" : "warning"}`}>
                      優先度 {task.priority === "high" ? "高" : "中"}
                    </span>
                    <span className="t-tiny ml-auto">期限 {fmtDate(task.due)}</span>
                  </div>
                  <div className="truncate text-sm font-semibold" style={{ color: "var(--text)" }}>{task.title}</div>
                  <div className="mono t-tiny truncate">{task.identifier}</div>
                  <div className="mt-2 flex items-center gap-2">
                    <Avatar user={task.requestedBy} size={20} />
                    <span className="t-tiny">{userById[task.requestedBy].name}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {active && (
            <div className="app-card-pad">
              <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                <div className="min-w-0">
                  <div className="mono truncate text-[15px] font-semibold">{active.identifier}</div>
                  <div className="t-sec mt-1">{active.title}</div>
                </div>
                <button className="app-btn app-btn-sm">
                  <ExternalLink className="h-3.5 w-3.5" />
                  コンテナを開く
                </button>
              </div>

              <div className="mb-5 grid gap-3 sm:grid-cols-3">
                <div className="flex items-center gap-2 rounded-xl p-4" style={{ background: "var(--surface-2)" }}>
                  <StatePill state={active.from} />
                  <span style={{ color: "var(--text-3)" }}>→</span>
                  <StatePill state={active.to} />
                </div>
                <div className="rounded-xl p-4" style={{ background: "var(--surface-2)" }}>
                  <div className="t-label mb-2">承認点</div>
                  <span className="app-badge app-badge-sq tone-info">{active.stage}</span>
                </div>
                <div className="rounded-xl p-4" style={{ background: "var(--surface-2)" }}>
                  <div className="t-label mb-2">情報分類</div>
                  <SecurityPill level={active.security} />
                </div>
              </div>

              <div className="t-label mb-3">レビュー チェックリスト</div>
              <div className="mb-5 grid gap-2">
                {[
                  "命名規則 ISO 19650-2 に適合",
                  "必須メタデータを充足",
                  "情報分類とアクセス権限の整合",
                  "関連コンテナ・参照文書の整合性",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-3 rounded-lg border p-3" style={{ borderColor: "var(--border)" }}>
                    <span className="flex h-5 w-5 items-center justify-center rounded-md tone-success">
                      <Check className="h-3 w-3" />
                    </span>
                    <span className="flex-1 text-[12.5px]">{item}</span>
                    <span className="app-badge app-badge-sq tone-success">確認済</span>
                  </div>
                ))}
              </div>

              <label className="mb-4 block">
                <div className="mb-1 text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>承認コメント</div>
                <textarea className="app-field h-20 py-2" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="コメントを記入..." />
              </label>
              <div className="flex flex-wrap gap-2">
                <button className="app-btn app-btn-primary h-10 flex-1" onClick={complete}>
                  <Check className="h-4 w-4" />
                  承認して公開
                </button>
                <button className="app-btn h-10" onClick={complete}>
                  <RotateCcw className="h-4 w-4" />
                  差戻し
                </button>
                <button className="app-btn h-10" onClick={complete} style={{ color: "var(--danger-fg)", background: "var(--danger-bg)", borderColor: "var(--danger-bg)" }}>
                  <X className="h-4 w-4" />
                  却下
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
