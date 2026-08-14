import { useState } from "react";
import {
  Bell,
  Building2,
  CheckCircle2,
  Key,
  Loader2,
  Lock,
  Save,
  Settings,
  Shield,
  User,
} from "lucide-react";
import { useAuthStore } from "@/hooks/useAuthStore";
import { api } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";

type Tab = "profile" | "org" | "notifications" | "security";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "profile", label: "プロフィール", icon: <User className="h-4 w-4" /> },
  {
    id: "org",
    label: "組織・メンバー",
    icon: <Building2 className="h-4 w-4" />,
  },
  {
    id: "notifications",
    label: "通知設定",
    icon: <Bell className="h-4 w-4" />,
  },
  {
    id: "security",
    label: "セキュリティ",
    icon: <Shield className="h-4 w-4" />,
  },
];

function ProfileTab() {
  const user = useAuthStore((s) => s.user);
  if (!user) return null;
  const initials = user.full_name?.slice(0, 1) || user.username?.slice(0, 1) || "?";
  return (
    <div className="space-y-6">
      <div className="app-card-pad">
        <div className="t-h2 mb-4">基本情報</div>
        <div className="flex items-start gap-5">
          <div
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-2xl font-bold text-white"
            style={{ background: "var(--primary)" }}
          >
            {initials}
          </div>
          <div className="flex-1 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="t-tiny mb-1 block">氏名</label>
                <input className="app-field" defaultValue={user.full_name} readOnly />
              </div>
              <div>
                <label className="t-tiny mb-1 block">メールアドレス</label>
                <input
                  className="app-field"
                  type="email"
                  defaultValue={user.email}
                  readOnly
                />
              </div>
              <div>
                <label className="t-tiny mb-1 block">ユーザー名</label>
                <input className="app-field mono" defaultValue={user.username} readOnly />
              </div>
            </div>
            <p className="t-tiny">
              プロフィール変更は管理者（組織・SSO設定）が行います。
              {user.is_platform_admin ? " プラットフォーム管理者" : ""}
            </p>
          </div>
        </div>
      </div>

      <div className="app-card-pad">
        <div className="t-h2 mb-4">パスワード変更</div>
        <PasswordChangeForm />
      </div>
    </div>
  );
}

function PasswordChangeForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<{
    kind: "ok" | "err";
    text: string;
  } | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      await api.post("/auth/change-password", {
        current_password: current,
        new_password: next,
        new_password_confirm: confirm,
      });
    },
    onSuccess: () => {
      setMessage({ kind: "ok", text: "パスワードを更新しました。" });
      setCurrent("");
      setNext("");
      setConfirm("");
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "パスワードを更新できませんでした。";
      setMessage({ kind: "err", text: detail });
    },
  });

  const canSubmit =
    current.length > 0 && next.length >= 8 && next === confirm && !mutation.isPending;

  return (
    <div className="space-y-3">
      {message && (
        <p
          className="text-xs"
          style={{
            color:
              message.kind === "ok" ? "var(--success-fg)" : "var(--danger-fg)",
          }}
        >
          {message.kind === "ok" ? (
            <CheckCircle2 className="mr-1 inline h-3.5 w-3.5" />
          ) : null}
          {message.text}
        </p>
      )}
      <div>
        <label className="t-tiny mb-1 block">現在のパスワード</label>
        <input
          className="app-field"
          type="password"
          placeholder="••••••••"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="t-tiny mb-1 block">新しいパスワード（8文字以上）</label>
          <input
            className="app-field"
            type="password"
            placeholder="••••••••"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </div>
        <div>
          <label className="t-tiny mb-1 block">確認</label>
          <input
            className="app-field"
            type="password"
            placeholder="••••••••"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </div>
      </div>
      <button
        className="app-btn app-btn-sm"
        disabled={!canSubmit}
        title={canSubmit ? undefined : "入力内容を確認してください"}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Lock className="h-3.5 w-3.5" />
        )}
        パスワードを更新
      </button>
    </div>
  );
}

function OrgTab() {
  const { data: orgs = [] } = useQuery({
    queryKey: ["organizations"],
    queryFn: () =>
      api
        .get<
          Array<{
            id: string;
            name: string;
            slug: string;
            description: string | null;
            is_active: boolean;
          }>
        >("/organizations")
        .then((r) => r.data),
  });
  return (
    <div className="space-y-5">
      <div className="app-card-pad">
        <div className="t-h2 mb-1">組織設定</div>
        <p className="t-sec mb-4 text-xs">
          組織名・識別コード・適用規格を管理します。
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {orgs.length === 0 && <p className="t-sec">所属組織がありません。</p>}
          {orgs.map((org) => (
            <div
              key={org.id}
              className="rounded-xl border p-3"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="text-sm font-semibold">{org.name}</div>
              <div className="mono t-tiny">{org.slug}</div>
              {org.description && <div className="t-tiny mt-1">{org.description}</div>}
              <span className={`app-badge app-badge-sq ${org.is_active ? "tone-success" : "tone-neutral"}`}>
                {org.is_active ? "有効" : "無効"}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="app-card overflow-hidden">
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="t-h2">メンバー管理</div>
        </div>
        <div className="px-4 py-4">
          <p className="t-sec text-xs">
            利用者の有効化・無効化・組織割当はプラットフォーム管理者向け管理API
            （GET/PATCH /api/v1/admin/users）で実施します。管理UIはロードマップに含まれます。
          </p>
        </div>
      </div>
    </div>
  );
}

function NotificationsTab() {
  return (
    <div className="app-card-pad space-y-4">
      <div className="t-h2 mb-2">通知設定</div>
      <p className="t-sec text-xs">
        アプリ内通知は常時有効です（承認依頼・承認結果・コンテナ状態変更を自動通知）。
        メール通知は本番展開（Phase 1）で Exchange Online / SMTP 連携とあわせて提供予定です。
      </p>
      <div
        className="rounded-lg p-3 text-xs"
        style={{ background: "var(--surface-2)" }}
      >
        <div className="mb-2 flex items-center gap-2">
          <Bell className="h-4 w-4" style={{ color: "var(--primary)" }} />
          <span className="font-medium">アプリ内通知（実装済み）</span>
        </div>
        <ul className="list-inside list-disc space-y-1 t-sec">
          <li>承認依頼（承認者へ自動通知）</li>
          <li>承認結果（申請者へ自動通知）</li>
          <li>コンテナ状態変更（作成者へ自動通知）</li>
          <li>未読バッジ・一覧・既読管理（ヘッダーのベルアイコン）</li>
        </ul>
      </div>
      <div
        className="rounded-lg p-3 text-xs"
        style={{ background: "var(--surface-2)" }}
      >
        <div className="mb-2 flex items-center gap-2">
          <Save className="h-4 w-4" style={{ color: "var(--text-3)" }} />
          <span className="font-medium">メール通知（未実装）</span>
        </div>
        <p className="t-sec">
          承認依頼・ダイジェスト等のメール配信はロードマップ（Phase 1）に含まれます。
        </p>
      </div>
    </div>
  );
}

function SecurityTab() {
  return (
    <div className="space-y-5">
      <div className="app-card-pad">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="h-5 w-5" style={{ color: "var(--primary)" }} />
          <div className="t-h2">セキュリティ概要</div>
        </div>
        <p className="t-sec mb-4 text-xs">
          多要素認証・APIトークン・セッション管理は本番展開（Phase 1-2）で
          導入予定です。現在の認証方式は JWT（アクセス+リフレッシュトークン）です。
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            {
              label: "認証方式",
              value: "JWT",
              tone: "info",
            },
            {
              label: "自己登録",
              value: "開発環境のみ",
              tone: "warning",
            },
            {
              label: "監査ログ",
              value: "Append-Only",
              tone: "success",
            },
          ].map(({ label, value, tone }) => (
            <div key={label} className="app-card-pad py-3">
              <div className={`mono text-xl font-bold tone-${tone}`}>
                {value}
              </div>
              <div className="t-tiny mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="app-card-pad">
        <div className="t-h2 mb-3">多要素認証 (MFA)</div>
        <div
          className="flex items-center justify-between rounded-lg p-3"
          style={{ background: "var(--surface-2)" }}
        >
          <div>
            <div className="text-sm font-semibold">TOTP 認証アプリ</div>
            <div className="t-sec text-xs">
              Google Authenticator / Authy（未実装・本番導入時に対応）
            </div>
          </div>
          <span className="app-badge app-badge-sq text-xs" style={{ opacity: 0.7 }}>
            未設定
          </span>
        </div>
        <p className="t-tiny mt-2">
          本番環境では Entra ID / HENNGE などの IdP 側で MFA を強制します（設計方針）。
        </p>
      </div>

      <div className="app-card-pad">
        <div className="t-h2 mb-3">アクセストークン</div>
        <p className="t-sec mb-3 text-xs">
          API アクセス用の長期トークンは未実装です（本番展開時に提供予定）。
        </p>
        <button className="app-btn app-btn-sm" disabled title="未実装">
          <Key className="h-3.5 w-3.5" />
          新しいトークンを発行
        </button>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("profile");

  return (
    <div className="mx-auto max-w-[1100px] p-5 sm:p-6">
      <div className="mb-5 flex items-center gap-3">
        <span
          className="flex h-10 w-10 items-center justify-center rounded-xl"
          style={{ background: "var(--surface-3)", color: "var(--primary)" }}
        >
          <Settings className="h-5 w-5" />
        </span>
        <div>
          <h1 className="t-display">設定</h1>
          <p className="t-sec mt-0.5 text-xs">
            命名規則マスタ・属性定義・ロール権限の管理
          </p>
        </div>
      </div>

      <div
        className="flex gap-1 border-b mb-5"
        style={{ borderColor: "var(--border)" }}
      >
        {TABS.map(({ id, label, icon }) => (
          <button
            key={id}
            className="flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium transition-colors -mb-px border-b-2"
            style={
              tab === id
                ? {
                    color: "var(--primary-text)",
                    borderColor: "var(--primary)",
                  }
                : { color: "var(--text-3)", borderColor: "transparent" }
            }
            onClick={() => setTab(id)}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      {tab === "profile" && <ProfileTab />}
      {tab === "org" && <OrgTab />}
      {tab === "notifications" && <NotificationsTab />}
      {tab === "security" && <SecurityTab />}
    </div>
  );
}
