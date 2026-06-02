import type { ReactNode } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle,
  Eye,
  Lock,
} from "lucide-react";
import { userById, type DesignUser } from "@/lib/designData";
import type { ContainerState, SecurityLevel } from "@/types";

const stateMeta: Record<ContainerState, { label: string; jp: string; cls: string }> = {
  WIP: { label: "WIP", jp: "作業中", cls: "wip" },
  Shared: { label: "Shared", jp: "共有", cls: "shared" },
  Published: { label: "Published", jp: "公開承認", cls: "published" },
  Archived: { label: "Archived", jp: "保管", cls: "archived" },
};

const securityMeta: Record<SecurityLevel, { label: string; tone: string }> = {
  public: { label: "公開", tone: "neutral" },
  limited: { label: "限定公開", tone: "info" },
  confidential: { label: "機密", tone: "warning" },
  restricted: { label: "要保護", tone: "danger" },
};

export function StatePill({ state, jp = false }: { state: ContainerState; jp?: boolean }) {
  const meta = stateMeta[state];
  return (
    <span
      className="app-badge"
      style={{ background: `var(--${meta.cls}-bg)`, color: `var(--${meta.cls}-fg)` }}
    >
      <span className="app-dot" style={{ background: `var(--${meta.cls}-dot)` }} />
      {meta.label}
      {jp ? ` · ${meta.jp}` : ""}
    </span>
  );
}

export function SecurityPill({ level }: { level: SecurityLevel }) {
  const meta = securityMeta[level];
  const Icon = level === "public" ? Eye : Lock;
  return (
    <span className={`app-badge app-badge-sq tone-${meta.tone}`}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

export function NamingBadge({ status }: { status: "pass" | "warn" | "fail" }) {
  const meta = {
    pass: { tone: "success", label: "適合", icon: CheckCircle },
    warn: { tone: "warning", label: "警告", icon: AlertTriangle },
    fail: { tone: "danger", label: "不適合", icon: AlertCircle },
  }[status];
  const Icon = meta.icon;
  return (
    <span className={`app-badge app-badge-sq tone-${meta.tone}`}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

export function ResultBadge({ result }: { result: string }) {
  const meta =
    {
      success: { tone: "success", label: "成功", icon: CheckCircle },
      failure: { tone: "danger", label: "失敗", icon: AlertCircle },
      denied: { tone: "warning", label: "拒否", icon: Lock },
      warning: { tone: "warning", label: "警告", icon: AlertTriangle },
    }[result] ?? { tone: "neutral", label: result, icon: Check };
  const Icon = meta.icon;
  return (
    <span className={`app-badge app-badge-sq tone-${meta.tone}`}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

export function Avatar({ user, size = 28 }: { user?: DesignUser | string | null; size?: number }) {
  const resolved = typeof user === "string" ? userById[user] : user;
  if (!resolved) return null;
  return (
    <span
      title={`${resolved.name} · ${resolved.role}`}
      style={{ width: size, height: size, background: resolved.color, fontSize: size * 0.42 }}
      className="inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
    >
      {resolved.initials}
    </span>
  );
}

export function EmptyState({ icon, title, sub }: { icon: ReactNode; title: string; sub?: string }) {
  return (
    <div className="py-14 text-center" style={{ color: "var(--text-3)" }}>
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl" style={{ background: "var(--surface-3)" }}>
        {icon}
      </div>
      <div className="text-sm font-semibold" style={{ color: "var(--text-2)" }}>
        {title}
      </div>
      {sub && <div className="mt-1 text-xs">{sub}</div>}
    </div>
  );
}

export function fmtDate(value: string | null | undefined, withTime = false) {
  if (!value) return "-";
  const d = new Date(value);
  const base = `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
  if (!withTime) return base;
  return `${base} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function relTime(value: string | null | undefined) {
  if (!value) return "-";
  const diff = (Date.now() - new Date(value).getTime()) / 1000;
  if (diff < 3600) return `${Math.max(1, Math.floor(diff / 60))}分前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}時間前`;
  return `${Math.floor(diff / 86400)}日前`;
}
