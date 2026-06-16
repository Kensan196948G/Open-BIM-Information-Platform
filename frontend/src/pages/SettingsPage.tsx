import { useState } from "react";
import {
  Bell,
  Building2,
  Key,
  Lock,
  Save,
  Settings,
  Shield,
  Tag,
  User,
  Users,
} from "lucide-react";
import { Avatar } from "@/components/design/Primitives";
import { designUsers } from "@/lib/designData";

type Tab = "profile" | "org" | "notifications" | "security" | "rbac";

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
  { id: "rbac", label: "ロール・権限", icon: <Key className="h-4 w-4" /> },
];

const ROLES = [
  {
    id: "admin",
    name: "システム管理者",
    desc: "全機能への完全アクセス",
    color: "#e0483b",
    perms: [
      "プロジェクト管理",
      "ユーザー管理",
      "監査ログ閲覧",
      "承認操作",
      "コンテナ全操作",
    ],
  },
  {
    id: "bim_manager",
    name: "BIM マネージャー",
    desc: "情報管理・承認操作",
    color: "#2c63e6",
    perms: ["プロジェクト管理", "承認操作", "コンテナ全操作", "監査ログ閲覧"],
  },
  {
    id: "designer",
    name: "設計担当",
    desc: "コンテナ作成・共有",
    color: "#14a85f",
    perms: ["コンテナ作成", "コンテナ共有申請", "要求文書閲覧"],
  },
  {
    id: "viewer",
    name: "閲覧者",
    desc: "読み取り専用",
    color: "#9b59b6",
    perms: ["コンテナ閲覧", "要求文書閲覧"],
  },
];

function ProfileTab() {
  const me = designUsers[0];
  return (
    <div className="space-y-6">
      <div className="app-card-pad">
        <div className="t-h2 mb-4">基本情報</div>
        <div className="flex items-start gap-5">
          <div
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-2xl font-bold text-white"
            style={{ background: me.color }}
          >
            {me.initials}
          </div>
          <div className="flex-1 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="t-tiny mb-1 block">氏名</label>
                <input className="app-field" defaultValue={me.name} />
              </div>
              <div>
                <label className="t-tiny mb-1 block">表示名 (イニシャル)</label>
                <input className="app-field mono" defaultValue={me.initials} />
              </div>
              <div>
                <label className="t-tiny mb-1 block">メールアドレス</label>
                <input
                  className="app-field"
                  type="email"
                  defaultValue="k.sato@taisei-design.co.jp"
                />
              </div>
              <div>
                <label className="t-tiny mb-1 block">所属組織</label>
                <input className="app-field" defaultValue={me.org} />
              </div>
              <div>
                <label className="t-tiny mb-1 block">役職・ロール</label>
                <input className="app-field" defaultValue={me.role} />
              </div>
              <div>
                <label className="t-tiny mb-1 block">言語</label>
                <select className="app-field">
                  <option value="ja">日本語</option>
                  <option value="en">English</option>
                </select>
              </div>
            </div>
            <button className="app-btn app-btn-primary app-btn-sm">
              <Save className="h-3.5 w-3.5" />
              保存
            </button>
          </div>
        </div>
      </div>

      <div className="app-card-pad">
        <div className="t-h2 mb-4">パスワード変更</div>
        <div className="space-y-3">
          <div>
            <label className="t-tiny mb-1 block">現在のパスワード</label>
            <input
              className="app-field"
              type="password"
              placeholder="••••••••"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="t-tiny mb-1 block">新しいパスワード</label>
              <input
                className="app-field"
                type="password"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="t-tiny mb-1 block">確認</label>
              <input
                className="app-field"
                type="password"
                placeholder="••••••••"
              />
            </div>
          </div>
          <button className="app-btn app-btn-sm">
            <Lock className="h-3.5 w-3.5" />
            パスワードを更新
          </button>
        </div>
      </div>
    </div>
  );
}

function OrgTab() {
  return (
    <div className="space-y-5">
      <div className="app-card-pad">
        <div className="t-h2 mb-1">組織設定</div>
        <p className="t-sec mb-4 text-xs">
          組織名・識別コード・適用規格を管理します。
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            ["組織名", "大成設計株式会社"],
            ["組織コード", "ORG-TKO"],
            ["適用規格", "ISO 19650-2:2018"],
            ["タイムゾーン", "Asia/Tokyo (JST +09:00)"],
          ].map(([label, val]) => (
            <div key={label}>
              <label className="t-tiny mb-1 block">{label}</label>
              <input className="app-field" defaultValue={val} />
            </div>
          ))}
        </div>
        <button className="app-btn app-btn-primary app-btn-sm mt-3">
          <Save className="h-3.5 w-3.5" />
          保存
        </button>
      </div>

      <div className="app-card overflow-hidden">
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="t-h2">メンバー管理</div>
          <button className="app-btn app-btn-sm">
            <Users className="h-3.5 w-3.5" />
            招待
          </button>
        </div>
        <table className="app-table">
          <thead>
            <tr>
              <th>メンバー</th>
              <th>役職</th>
              <th>所属</th>
              <th>ロール</th>
              <th>状態</th>
            </tr>
          </thead>
          <tbody>
            {designUsers.map((u, i) => (
              <tr key={u.id}>
                <td>
                  <div className="flex items-center gap-2">
                    <Avatar user={u} size={28} />
                    <span className="text-sm font-medium">{u.name}</span>
                  </div>
                </td>
                <td>
                  <span className="t-sec text-xs">{u.role}</span>
                </td>
                <td>
                  <span className="t-sec text-xs">{u.org}</span>
                </td>
                <td>
                  <span
                    className="app-badge app-badge-sq"
                    style={{ fontSize: 11 }}
                  >
                    {i === 0 ? "管理者" : i < 3 ? "BIM管理" : "設計担当"}
                  </span>
                </td>
                <td>
                  <span
                    className="app-badge app-badge-sq tone-success"
                    style={{ fontSize: 11 }}
                  >
                    アクティブ
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NotificationsTab() {
  const [settings, setSettings] = useState({
    approval_request: true,
    approval_done: true,
    container_shared: true,
    container_published: false,
    naming_violation: true,
    security_alert: true,
    weekly_report: false,
    digest_email: true,
  });

  const toggle = (k: keyof typeof settings) =>
    setSettings((s) => ({ ...s, [k]: !s[k] }));

  const items: { key: keyof typeof settings; label: string; desc: string }[] = [
    {
      key: "approval_request",
      label: "承認依頼",
      desc: "承認タスクが届いたとき",
    },
    {
      key: "approval_done",
      label: "承認完了",
      desc: "自分の申請が承認・差し戻しされたとき",
    },
    {
      key: "container_shared",
      label: "コンテナ共有",
      desc: "コンテナが Shared 状態に遷移したとき",
    },
    {
      key: "container_published",
      label: "コンテナ発行",
      desc: "コンテナが Published になったとき",
    },
    {
      key: "naming_violation",
      label: "命名規則違反",
      desc: "命名エラーが検出されたとき",
    },
    {
      key: "security_alert",
      label: "セキュリティ警告",
      desc: "不審なアクセスが検出されたとき",
    },
    {
      key: "weekly_report",
      label: "週次レポート",
      desc: "毎週月曜日にサマリーをメール送信",
    },
    {
      key: "digest_email",
      label: "ダイジェストメール",
      desc: "1 日 1 回まとめてメール送信",
    },
  ];

  return (
    <div className="app-card-pad space-y-4">
      <div className="t-h2 mb-2">通知設定</div>
      {items.map(({ key, label, desc }) => (
        <div
          key={key}
          className="flex items-center justify-between gap-4 py-2"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div>
            <div
              className="text-sm font-medium"
              style={{ color: "var(--text)" }}
            >
              {label}
            </div>
            <div className="t-sec text-xs">{desc}</div>
          </div>
          <button
            className="relative h-6 w-11 shrink-0 rounded-full transition-colors"
            style={{
              background: settings[key] ? "var(--primary)" : "var(--surface-3)",
            }}
            onClick={() => toggle(key)}
          >
            <span
              className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform"
              style={{ left: settings[key] ? "calc(100% - 1.375rem)" : "2px" }}
            />
          </button>
        </div>
      ))}
      <button className="app-btn app-btn-primary app-btn-sm">
        <Save className="h-3.5 w-3.5" />
        保存
      </button>
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
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            {
              label: "最終ログイン",
              value: "2026-06-14 09:32",
              tone: "success",
            },
            { label: "アクティブセッション", value: "1", tone: "info" },
            { label: "ログイン失敗 (30日)", value: "0", tone: "success" },
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
            <div className="t-sec text-xs">Google Authenticator / Authy</div>
          </div>
          <span className="app-badge tone-success app-badge-sq text-xs">
            有効
          </span>
        </div>
        <button className="app-btn app-btn-sm mt-3">設定を変更</button>
      </div>

      <div className="app-card-pad">
        <div className="t-h2 mb-3">アクセストークン</div>
        <p className="t-sec mb-3 text-xs">
          API アクセス用の長期トークンを管理します。
        </p>
        <div className="space-y-2">
          {[
            {
              name: "CI/CD Pipeline",
              created: "2026-05-01",
              last: "2026-06-14",
            },
            {
              name: "BIM Connector v2",
              created: "2026-03-15",
              last: "2026-06-13",
            },
          ].map((t) => (
            <div
              key={t.name}
              className="flex items-center justify-between rounded-lg px-3 py-2"
              style={{ background: "var(--surface-2)" }}
            >
              <div>
                <div className="text-sm font-medium">{t.name}</div>
                <div className="t-tiny">
                  作成: {t.created} · 最終利用: {t.last}
                </div>
              </div>
              <button
                className="app-btn app-btn-sm"
                style={{
                  color: "var(--danger-fg)",
                  borderColor: "var(--danger-border)",
                }}
              >
                失効
              </button>
            </div>
          ))}
        </div>
        <button className="app-btn app-btn-sm mt-3">
          <Key className="h-3.5 w-3.5" />
          新しいトークンを発行
        </button>
      </div>
    </div>
  );
}

function RbacTab() {
  const [selected, setSelected] = useState<string | null>(ROLES[0].id);
  const role = ROLES.find((r) => r.id === selected);

  return (
    <div className="flex gap-4" style={{ minHeight: 400 }}>
      <div className="w-52 shrink-0 space-y-1">
        {ROLES.map((r) => (
          <button
            key={r.id}
            className="w-full rounded-xl px-3 py-2.5 text-left transition-colors"
            style={
              selected === r.id
                ? {
                    background: "var(--primary-subtle)",
                    color: "var(--primary-text)",
                  }
                : { color: "var(--text)" }
            }
            onClick={() => setSelected(r.id)}
          >
            <div className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ background: r.color }}
              />
              <span className="text-sm font-medium">{r.name}</span>
            </div>
          </button>
        ))}
      </div>

      {role && (
        <div className="app-card-pad flex-1 space-y-4">
          <div className="flex items-center gap-3">
            <span
              className="h-3.5 w-3.5 rounded-full"
              style={{ background: role.color }}
            />
            <div>
              <div className="font-semibold" style={{ color: "var(--text)" }}>
                {role.name}
              </div>
              <div className="t-sec text-xs">{role.desc}</div>
            </div>
          </div>
          <div>
            <div className="t-tiny mb-2">付与されている権限</div>
            <div className="flex flex-wrap gap-2">
              {role.perms.map((p) => (
                <span
                  key={p}
                  className="app-badge app-badge-sq flex items-center gap-1.5"
                  style={{ fontSize: 12 }}
                >
                  <Tag className="h-3 w-3" />
                  {p}
                </span>
              ))}
            </div>
          </div>
          <div
            className="t-sec rounded-lg p-3 text-xs"
            style={{ background: "var(--surface-2)" }}
          >
            ロール権限の変更はシステム管理者のみ可能です。変更は監査ログに記録されます。
          </div>
        </div>
      )}
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
      {tab === "rbac" && <RbacTab />}
    </div>
  );
}
