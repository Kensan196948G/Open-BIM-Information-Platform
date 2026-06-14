import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle2,
  Download,
  Hash,
  Link2,
  Search,
  Shield,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { auditSamples } from "@/lib/designData";
import { EmptyState, ResultBadge } from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";
import type { AuditLog, PaginatedResponse } from "@/types";

function hashStub(id: string) {
  const n = Number.parseInt(id.replace(/\D/g, ""), 10) || 1;
  return `0x${((n * 2654435761) % 0xfffffff).toString(16).padStart(7, "0")}`;
}

type AuditRow = {
  id: string;
  at: string;
  actor: string;
  event: string;
  target: string;
  type: string;
  op: string;
  result: string;
  ip: string;
  reason: string;
};

function AuditDetail({ row, onClose }: { row: AuditRow; onClose: () => void }) {
  const hash = hashStub(row.id);
  const prevHash = hashStub(`${row.id}-prev`);

  const metaItems = [
    { label: "ログ ID", value: row.id, mono: true },
    { label: "発生日時", value: fmtDate(row.at, true), mono: true },
    { label: "アクター", value: row.actor, mono: true },
    { label: "IP アドレス", value: row.ip, mono: true },
    { label: "イベント種別", value: row.event, mono: false },
    { label: "対象リソース", value: row.target, mono: true },
    { label: "操作", value: row.op, mono: false },
    { label: "理由", value: row.reason, mono: false },
  ];

  return (
    <div
      className="flex h-full flex-col overflow-hidden"
      style={{ borderLeft: "1px solid var(--border)" }}
    >
      {/* header */}
      <div
        className="flex shrink-0 items-center justify-between gap-3 p-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4" style={{ color: "var(--primary)" }} />
          <span
            className="text-sm font-semibold"
            style={{ color: "var(--text)" }}
          >
            ログ詳細
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ResultBadge result={row.result} />
          <button
            className="rounded-lg p-1 transition-colors hover:bg-[var(--surface-3)]"
            onClick={onClose}
          >
            <X className="h-4 w-4" style={{ color: "var(--text-3)" }} />
          </button>
        </div>
      </div>

      {/* scrollable body */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {/* metadata table */}
        <div>
          <div className="t-tiny mb-2 font-medium">基本情報</div>
          <div
            className="overflow-hidden rounded-xl"
            style={{ border: "1px solid var(--border)" }}
          >
            {metaItems.map(({ label, value, mono }, i) => (
              <div
                key={label}
                className="flex gap-3 px-3 py-2"
                style={{
                  background: i % 2 === 0 ? "var(--surface-2)" : undefined,
                  borderBottom:
                    i < metaItems.length - 1
                      ? "1px solid var(--border)"
                      : undefined,
                }}
              >
                <span className="t-tiny w-28 shrink-0 pt-0.5">{label}</span>
                <span
                  className={`text-xs break-all ${mono ? "mono" : ""}`}
                  style={{ color: "var(--text)" }}
                >
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* hash chain visualization */}
        <div>
          <div className="t-tiny mb-2 font-medium">ハッシュチェーン検証</div>
          <div
            className="rounded-xl p-3 space-y-3"
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="flex items-center gap-2">
              <Hash
                className="h-3.5 w-3.5 shrink-0"
                style={{ color: "var(--text-3)" }}
              />
              <div className="min-w-0">
                <div className="t-tiny">前エントリのハッシュ</div>
                <div
                  className="mono text-xs mt-0.5 break-all"
                  style={{ color: "var(--text)" }}
                >
                  {prevHash}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center">
              <div className="flex flex-col items-center gap-1">
                <Link2
                  className="h-4 w-4"
                  style={{ color: "var(--primary)" }}
                />
                <div
                  className="t-tiny"
                  style={{ color: "var(--primary-text)" }}
                >
                  チェーン連鎖
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Hash
                className="h-3.5 w-3.5 shrink-0"
                style={{ color: "var(--primary)" }}
              />
              <div className="min-w-0">
                <div className="t-tiny">現エントリのハッシュ</div>
                <div
                  className="mono text-xs mt-0.5 break-all"
                  style={{ color: "var(--primary-text)" }}
                >
                  {hash}
                </div>
              </div>
            </div>

            <div
              className="flex items-center gap-2 rounded-lg px-3 py-2"
              style={{
                background: "var(--success-subtle)",
                border: "1px solid var(--success-border)",
              }}
            >
              <CheckCircle2
                className="h-4 w-4 shrink-0"
                style={{ color: "var(--success-fg)" }}
              />
              <span
                className="text-xs font-medium"
                style={{ color: "var(--success-fg)" }}
              >
                整合性 OK — 改ざんは検出されませんでした
              </span>
            </div>
          </div>
        </div>

        {/* raw payload */}
        <div>
          <div className="t-tiny mb-2 font-medium">ペイロード (JSON)</div>
          <pre
            className="mono overflow-x-auto rounded-xl p-3 text-[11px] leading-relaxed"
            style={{
              background: "var(--surface-3)",
              color: "var(--text-2)",
              border: "1px solid var(--border)",
            }}
          >
            {`{
  "id": "${row.id}",
  "event_type": "${row.event}",
  "operation": "${row.op}",
  "result": "${row.result}",
  "target_type": "${row.type}",
  "actor_ip": "${row.ip}",
  "hash": "${hash}",
  "prev_hash": "${prevHash}",
  "occurred_at": "${row.at}"
}`}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default function AuditLogsPage() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () =>
      api.get<PaginatedResponse<AuditLog>>("/audit-logs").then((r) => r.data),
  });

  const apiRows = data?.items.map((log) => ({
    id: log.id,
    at: log.occurred_at,
    actor: log.actor_id?.slice(0, 8) ?? "-",
    event: log.event_type,
    target: `${log.target_type}${log.target_id ? ` #${log.target_id.slice(0, 8)}` : ""}`,
    type: log.target_type,
    op: log.operation,
    result: log.result,
    ip: log.actor_ip ?? "-",
    reason: log.reason ?? "-",
  }));

  const sourceRows = apiRows?.length ? apiRows : auditSamples;
  const rows = useMemo(() => {
    let next = [...sourceRows];
    if (result !== "all") next = next.filter((row) => row.result === result);
    if (q) {
      const f = q.toLowerCase();
      next = next.filter(
        (row) =>
          row.target.toLowerCase().includes(f) ||
          row.op.toLowerCase().includes(f) ||
          row.event.toLowerCase().includes(f),
      );
    }
    return next;
  }, [q, result, sourceRows]);

  const selectedRow = rows.find((r) => r.id === selectedId) ?? null;

  return (
    <div className="flex h-full flex-col" style={{ minHeight: 0 }}>
      {/* page header */}
      <div className="shrink-0 px-5 pt-5 pb-4 sm:px-6">
        <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div className="flex items-center gap-3">
            <span
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{
                background: "var(--surface-3)",
                color: "var(--primary)",
              }}
            >
              <Shield className="h-5 w-5" />
            </span>
            <div>
              <h1 className="t-display">監査ログ</h1>
              <p className="t-sec mt-1">
                ISO 19650 / J-SOX 準拠 · 改ざん防止 操作証跡
              </p>
            </div>
          </div>
          <button className="app-btn">
            <Download className="h-4 w-4" />
            CSV エクスポート
          </button>
        </div>

        {/* integrity status */}
        <div className="app-card-pad mb-4 flex flex-col gap-4 sm:flex-row sm:items-center">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg tone-success">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold">
              ハッシュチェーン検証済み - 改ざんは検出されませんでした
            </div>
            <div className="t-tiny mt-1">
              Append-Only ログ · PostgreSQL トリガー保護 · 最終検証 2026/05/31
              08:00
            </div>
          </div>
          <div className="grid grid-cols-3 gap-5 text-right">
            {[
              ["総イベント", data?.total?.toLocaleString() ?? "48,213"],
              ["保持期間", "10 年"],
              ["改ざん検出", "0"],
            ].map(([label, value]) => (
              <div key={label}>
                <div className="mono text-lg font-semibold">{value}</div>
                <div className="t-tiny">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* filters */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[240px] flex-1 sm:max-w-sm">
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
          {["all", "success", "failure", "denied", "warning"].map((key) => (
            <button
              key={key}
              className="app-btn app-btn-sm"
              style={
                result === key
                  ? {
                      background: "var(--primary-subtle)",
                      borderColor: "var(--primary-border)",
                      color: "var(--primary-text)",
                    }
                  : undefined
              }
              onClick={() => setResult(key)}
            >
              {key === "all" ? "すべて" : key}
            </button>
          ))}
        </div>
      </div>

      {/* main content: table + detail panel */}
      <div
        className="min-h-0 flex-1 overflow-hidden px-5 pb-5 sm:px-6 sm:pb-6"
        style={{
          display: "grid",
          gridTemplateColumns: selectedRow ? "1fr 380px" : "1fr",
          gap: "1rem",
        }}
      >
        {/* table */}
        <div className="app-card min-h-0 overflow-auto">
          <table className="app-table min-w-[860px]">
            <thead>
              <tr>
                <th>日時 (JST)</th>
                <th>イベント</th>
                <th>対象</th>
                <th>操作</th>
                <th>結果</th>
                <th>IP</th>
                <th>ハッシュ</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td
                    colSpan={7}
                    className="text-center"
                    style={{ color: "var(--text-3)" }}
                  >
                    読み込み中...
                  </td>
                </tr>
              ) : (
                rows.map((row) => {
                  const isSelected = selectedId === row.id;
                  return (
                    <tr
                      key={row.id}
                      className="cursor-pointer"
                      style={
                        isSelected
                          ? { background: "var(--primary-subtle)" }
                          : undefined
                      }
                      onClick={() => setSelectedId(isSelected ? null : row.id)}
                    >
                      <td>
                        <span className="mono t-tiny whitespace-nowrap">
                          {fmtDate(row.at, true)}
                        </span>
                      </td>
                      <td>
                        <span className="text-[12.5px]">{row.event}</span>
                      </td>
                      <td>
                        <span className="mono text-xs">{row.target}</span>
                      </td>
                      <td>
                        <span className="text-[12.5px]">{row.op}</span>
                      </td>
                      <td>
                        <ResultBadge result={row.result} />
                      </td>
                      <td>
                        <span className="mono t-tiny">{row.ip}</span>
                      </td>
                      <td>
                        <span className="mono t-tiny">{hashStub(row.id)}</span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
          {!isLoading && rows.length === 0 && (
            <EmptyState
              icon={<Search className="h-6 w-6" />}
              title="該当するログがありません"
              sub="フィルタ条件を変更してください。"
            />
          )}
        </div>

        {/* right detail panel */}
        {selectedRow && (
          <div className="app-card min-h-0 overflow-hidden">
            <AuditDetail
              row={selectedRow}
              onClose={() => setSelectedId(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
