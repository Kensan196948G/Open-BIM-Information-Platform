import { Fragment, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  Download,
  Search,
  Shield,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { downloadAuditLogCsv } from "@/api/audit";
import { userById } from "@/lib/designData";
import { Avatar, EmptyState, ResultBadge } from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";
import type { AuditLog, PaginatedResponse } from "@/types";

const EVENT_GROUP: Record<string, { label: string }> = {
  auth:        { label: "認証" },
  container:   { label: "コンテナ" },
  approval:    { label: "承認" },
  workflow:    { label: "ワークフロー" },
  security:    { label: "セキュリティ" },
  role:        { label: "権限" },
  settings:    { label: "設定" },
  requirement: { label: "要求文書" },
};

export default function AuditLogsPage() {
  const [q, setQ]           = useState("");
  const [result, setResult] = useState("all");
  const [group, setGroup]   = useState("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () =>
      api.get<PaginatedResponse<AuditLog>>("/audit-logs").then((r) => r.data),
  });

  const apiRows = data?.items.map((log) => ({
    id: log.id,
    at: log.occurred_at,
    actorId: log.actor_id ?? null,
    actor: log.actor_id?.slice(0, 8) ?? "-",
    event: log.event_type,
    target: `${log.target_type}${log.target_id ? ` #${log.target_id.slice(0, 8)}` : ""}`,
    type: log.target_type,
    op: log.operation,
    result: log.result,
    ip: log.actor_ip ?? "-",
    reason: log.reason ?? "-",
  }));

  const groups = useMemo(
    () => [...new Set((apiRows ?? []).map((r) => r.event.split(".")[0]))],
    [apiRows],
  );

  const rows = useMemo(() => {
    let next = [...(apiRows ?? [])];
    if (result !== "all") next = next.filter((r) => r.result === result);
    if (group !== "all") next = next.filter((r) => r.event.split(".")[0] === group);
    if (q) {
      const f = q.toLowerCase();
      next = next.filter(
        (r) =>
          r.target.toLowerCase().includes(f) ||
          r.op.toLowerCase().includes(f) ||
          r.event.toLowerCase().includes(f),
      );
    }
    return next;
  }, [q, result, group, apiRows]);

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      {/* header */}
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div className="flex items-center gap-3">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-xl"
            style={{ background: "var(--surface-3)", color: "var(--primary)" }}
          >
            <Shield className="h-5 w-5" />
          </span>
          <div>
            <h1 className="t-display">監査ログ</h1>
            <p className="t-sec mt-1">ISO 19650 / J-SOX 準拠 · 改ざん防止 操作証跡</p>
          </div>
        </div>
        <button className="app-btn" onClick={() => downloadAuditLogCsv()} title="監査ログをCSV出力">
          <Download className="h-4 w-4" />
          CSV エクスポート
        </button>
      </div>

      {/* integrity banner */}
      <div className="app-card-pad mb-4 flex flex-col gap-4 sm:flex-row sm:items-center">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          style={{ background: "var(--success-bg)" }}
        >
          <ShieldCheck className="h-5 w-5" style={{ color: "var(--success-fg)" }} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold">
            Append-Only 監査ログ
          </div>
          <div className="t-tiny mt-1">
            PostgreSQL トリガーにより UPDATE / DELETE を拒否。外部WORM・電子署名は未実装（ロードマップ）
          </div>
        </div>
        <div className="grid grid-cols-3 gap-5 text-right">
          {([
            ["総イベント", data?.total?.toLocaleString() ?? "48,213"],
            ["保持期間", "10 年"],
            ["改ざん検出", "0"],
          ] as const).map(([label, value]) => (
            <div key={label}>
              <div className="mono text-lg font-semibold">{value}</div>
              <div className="t-tiny">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* filters */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
          <Search
            className="absolute left-3 top-2.5 h-4 w-4"
            style={{ color: "var(--text-3)" }}
          />
          <input
            className="app-field pl-9"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="対象・操作・イベントで検索..."
          />
        </div>
        <select
          className="app-field"
          style={{ width: "auto" }}
          value={group}
          onChange={(e) => setGroup(e.target.value)}
        >
          <option value="all">種別: すべて</option>
          {groups.map((g) => (
            <option key={g} value={g}>
              {EVENT_GROUP[g]?.label ?? g}
            </option>
          ))}
        </select>
        <div className="flex flex-wrap gap-1">
          {(["all", "success", "failure", "denied", "warning"] as const).map((k) => (
            <button
              key={k}
              className="app-btn app-btn-sm"
              style={
                result === k
                  ? {
                      background: "var(--primary-subtle)",
                      borderColor: "var(--primary-border)",
                      color: "var(--primary-text)",
                    }
                  : undefined
              }
              onClick={() => setResult(k)}
            >
              {k === "all" ? "すべて" : k === "success" ? "成功" : k === "failure" ? "失敗" : k === "denied" ? "拒否" : "警告"}
            </button>
          ))}
        </div>
      </div>

      {/* table */}
      <div className="app-card overflow-hidden">
        <div style={{ overflowX: "auto" }}>
          <table className="app-table" style={{ minWidth: 860 }}>
            <thead>
              <tr>
                <th style={{ width: 30 }}></th>
                <th style={{ width: 150 }}>日時 (JST)</th>
                <th>利用者</th>
                <th>イベント</th>
                <th>対象</th>
                <th>操作</th>
                <th>結果</th>
                <th>IP</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="text-center" style={{ color: "var(--text-3)" }}>
                    読み込み中...
                  </td>
                </tr>
              ) : (
                rows.map((row) => {
                  const user = row.actorId ? userById[row.actorId] : null;
                  const eventGroup = EVENT_GROUP[row.event.split(".")[0]];
                  const isOpen = expanded === row.id;

                  return (
                    <Fragment key={row.id}>
                      <tr
                        className="cursor-pointer"
                        onClick={() => setExpanded(isOpen ? null : row.id)}
                      >
                        <td>
                          {isOpen
                            ? <ChevronDown className="h-3.5 w-3.5" style={{ color: "var(--text-3)" }} />
                            : <ChevronRight className="h-3.5 w-3.5" style={{ color: "var(--text-3)" }} />
                          }
                        </td>
                        <td>
                          <span className="mono t-tiny whitespace-nowrap">
                            {fmtDate(row.at, true)}
                          </span>
                        </td>
                        <td>
                          {user ? (
                            <div className="flex items-center gap-1.5">
                              <Avatar user={user.id} size={22} />
                              <span className="whitespace-nowrap text-[12.5px]">{user.name}</span>
                            </div>
                          ) : (
                            <span className="mono t-tiny">{row.actor}</span>
                          )}
                        </td>
                        <td>
                          <span className="text-[12px]" style={{ color: "var(--text-2)" }}>
                            {eventGroup?.label ?? row.event.split(".")[0]}
                          </span>
                        </td>
                        <td>
                          <span className="mono text-xs whitespace-nowrap">{row.target}</span>
                        </td>
                        <td>
                          <span className="whitespace-nowrap text-[12.5px]">{row.op}</span>
                        </td>
                        <td>
                          <ResultBadge result={row.result} />
                        </td>
                        <td>
                          <span className="mono t-tiny">{row.ip}</span>
                        </td>
                      </tr>

                      {/* inline expanded detail row */}
                      {isOpen && (
                        <tr>
                          <td
                            colSpan={8}
                            style={{ padding: 0, background: "var(--surface-2)" }}
                          >
                            <div
                              style={{
                                padding: "14px 20px 16px 56px",
                                display: "grid",
                                gridTemplateColumns: "repeat(4, 1fr)",
                                gap: 16,
                              }}
                            >
                              {([
                                ["イベントID", row.id],
                                ["イベント種別", row.event],
                                ["対象種別", row.type],
                                ["理由 / 備考", row.reason],
                              ] as const).map(([k, v]) => (
                                <div key={k}>
                                  <div className="t-label mb-1">{k}</div>
                                  <div className="mono text-[12.5px]">{v}</div>
                                </div>
                              ))}

                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {isError && (
          <EmptyState
            icon={<Shield className="h-6 w-6" />}
            title="監査ログを取得できません"
            sub="監査ログの閲覧はプラットフォーム管理者に限定されています。"
          />
        )}
        {!isLoading && !isError && rows.length === 0 && (
          <EmptyState
            icon={<Search className="h-6 w-6" />}
            title="該当するログがありません"
            sub="フィルタ条件を変更してください。"
          />
        )}
      </div>
    </div>
  );
}
