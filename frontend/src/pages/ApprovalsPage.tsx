import { useEffect, useState } from "react";
import { Check, Clock, ExternalLink, RotateCcw, X } from "lucide-react";
import { approvals, userById } from "@/lib/designData";
import { Avatar, SecurityPill, StatePill } from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";

type Priority = "all" | "high" | "medium" | "low";

const PRIO_META = {
  high:   { tone: "danger",  label: "高" },
  medium: { tone: "warning", label: "中" },
  low:    { tone: "neutral", label: "低" },
} as const;

const ACT_LABEL: Record<string, string> = {
  approve: "承認",
  return:  "差戻し",
  reject:  "却下",
};

const CHECKLIST = [
  "命名規則 ISO 19650-2 に適合",
  "必須メタデータ（Status / Revision / Classification）充足",
  "情報分類とアクセス権限の整合",
  "関連コンテナ・参照文書の整合性",
];

export default function ApprovalsPage() {
  const [tasks, setTasks]   = useState([...approvals]);
  const [activeId, setActiveId] = useState(tasks[0]?.id);
  const [comment, setComment]   = useState("");
  const [filter, setFilter]     = useState<Priority>("all");
  const [toast, setToast]       = useState("");

  const shown  = tasks.filter((t) => filter === "all" || t.priority === filter);
  const active = tasks.find((t) => t.id === activeId) ?? shown[0];

  // keep activeId in sync when filter changes
  useEffect(() => {
    if (active && shown.find((t) => t.id === active.id)) return;
    setActiveId(shown[0]?.id);
  }, [filter]);

  const act = (result: "approve" | "return" | "reject") => {
    if (!active) return;
    setToast(`${active.identifier} を${ACT_LABEL[result]}しました`);
    const rest = tasks.filter((t) => t.id !== active.id);
    setTasks(rest);
    setActiveId(rest[0]?.id);
    setComment("");
    setTimeout(() => setToast(""), 2600);
  };

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      {/* header */}
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">承認タスク</h1>
          <p className="t-sec mt-1">check / review / approve · authorise 承認点</p>
        </div>
        {/* priority filter */}
        <div className="flex flex-wrap gap-2">
          {(["all", "high", "medium", "low"] as const).map((k) => (
            <button
              key={k}
              className="app-btn app-btn-sm"
              style={
                filter === k
                  ? { background: "var(--primary-subtle)", borderColor: "var(--primary-border)", color: "var(--primary-text)" }
                  : undefined
              }
              onClick={() => setFilter(k)}
            >
              {k === "all" ? "すべて" : `優先度 ${PRIO_META[k].label}`}
            </button>
          ))}
        </div>
      </div>

      {tasks.length === 0 ? (
        <div className="app-card-pad py-16 text-center">
          <Check className="mx-auto mb-3 h-10 w-10" style={{ color: "var(--success)" }} />
          <div className="t-h2">承認待ちのタスクはありません</div>
          <div className="t-sec mt-1">すべてのレビューが完了しています。</div>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
          {/* queue */}
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
                const prio = PRIO_META[task.priority as keyof typeof PRIO_META] ?? PRIO_META.low;
                const selected = task.id === active?.id;
                return (
                  <button
                    key={task.id}
                    className="block w-full border-b p-4 text-left"
                    style={{
                      borderColor: "var(--border-faint)",
                      borderLeft: selected ? "2.5px solid var(--primary)" : "2.5px solid transparent",
                      background: selected ? "var(--primary-subtle)" : "transparent",
                    }}
                    onClick={() => setActiveId(task.id)}
                  >
                    <div className="mb-1.5 flex items-center gap-2">
                      <span className={`app-badge app-badge-sq tone-${prio.tone}`} style={{ height: 18 }}>
                        優先度 {prio.label}
                      </span>
                      <span className="t-tiny ml-auto">期限 {fmtDate(task.due)}</span>
                    </div>
                    <div className="truncate text-[13px] font-semibold" style={{ color: "var(--text)" }}>
                      {task.title}
                    </div>
                    <div className="mono t-tiny truncate mt-0.5">{task.identifier}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <Avatar user={task.requestedBy} size={20} />
                      <span className="t-tiny">{userById[task.requestedBy]?.name}</span>
                      <span className="mono t-tiny ml-auto">{task.from}</span>
                    </div>
                  </button>
                );
              })}
              {shown.length === 0 && (
                <div className="py-10 text-center t-sec text-sm">
                  該当するタスクがありません
                </div>
              )}
            </div>
          </div>

          {/* detail */}
          {active && (
            <div className="app-card-pad" key={active.id}>
              {/* top row */}
              <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                <div className="min-w-0">
                  <div className="mono truncate text-[15px] font-semibold">{active.identifier}</div>
                  <div className="t-sec mt-1">{active.title}</div>
                </div>
                <button className="app-btn app-btn-sm shrink-0">
                  <ExternalLink className="h-3.5 w-3.5" />
                  コンテナを開く
                </button>
              </div>

              {/* transition + stage + security */}
              <div className="mb-5 flex flex-wrap gap-3">
                <div className="flex flex-1 items-center gap-3 rounded-xl p-4" style={{ minWidth: 200, background: "var(--surface-2)" }}>
                  <StatePill state={active.from} jp />
                  <span style={{ color: "var(--text-3)" }}>→</span>
                  <StatePill state={active.to} jp />
                </div>
                <div className="rounded-xl p-4" style={{ background: "var(--surface-2)" }}>
                  <div className="t-label mb-2">承認点</div>
                  <span className="app-badge app-badge-sq tone-info" style={{ height: 22 }}>{active.stage}</span>
                </div>
                <div className="rounded-xl p-4" style={{ background: "var(--surface-2)" }}>
                  <div className="t-label mb-2">情報分類</div>
                  <SecurityPill level={active.security} />
                </div>
              </div>

              {/* checklist */}
              <div className="t-label mb-3">レビュー チェックリスト</div>
              <div className="mb-5 grid gap-2">
                {CHECKLIST.map((item) => (
                  <div
                    key={item}
                    className="flex items-center gap-2.5 rounded-[9px] border p-2.5"
                    style={{ borderColor: "var(--border)" }}
                  >
                    <span
                      className="flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-md"
                      style={{ background: "var(--success-bg)" }}
                    >
                      <Check className="h-3 w-3" style={{ color: "var(--success-fg)" }} />
                    </span>
                    <span className="flex-1 text-[12.5px]">{item}</span>
                    <span className="app-badge app-badge-sq tone-success" style={{ height: 18 }}>確認済</span>
                  </div>
                ))}
              </div>

              {/* requester */}
              <div
                className="mb-5 flex items-center gap-2.5 rounded-[10px] p-3"
                style={{ background: "var(--surface-2)" }}
              >
                <Avatar user={active.requestedBy} size={30} />
                <div className="flex-1 min-w-0">
                  <div className="text-[12.5px]">
                    <b>{userById[active.requestedBy]?.name}</b> がレビューを依頼
                  </div>
                  <div className="t-tiny">
                    {userById[active.requestedBy]?.org} · {fmtDate(active.requestedAt, true)}
                  </div>
                </div>
              </div>

              {/* comment */}
              <div className="mb-4">
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>承認コメント</span>
                  <span className="t-tiny">承認・差戻し・却下いずれの場合も監査ログに記録されます。</span>
                </div>
                <textarea
                  className="app-field h-20 resize-none py-2"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="コメントを記入…"
                />
              </div>

              {/* actions */}
              <div className="flex flex-wrap gap-2.5">
                <button
                  className="app-btn app-btn-primary h-10 flex-1 justify-center"
                  onClick={() => act("approve")}
                >
                  <Check className="h-4 w-4" />
                  承認して公開
                </button>
                <button className="app-btn h-10" onClick={() => act("return")}>
                  <RotateCcw className="h-[15px] w-[15px]" />
                  差戻し
                </button>
                <button
                  className="app-btn h-10"
                  onClick={() => act("reject")}
                  style={{ color: "var(--danger-fg)", background: "var(--danger-bg)", borderColor: "var(--danger-bg)" }}
                >
                  <X className="h-[15px] w-[15px]" />
                  却下
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* toast */}
      {toast && (
        <div
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl px-5 py-3 text-sm font-medium shadow-lg"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-strong)",
            color: "var(--text)",
            animation: "fade-in 0.2s ease",
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}
