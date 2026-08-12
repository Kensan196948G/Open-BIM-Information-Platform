import {
  Outlet,
  NavLink,
  useLocation,
  useNavigate,
  useParams,
} from "react-router";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/hooks/useAuthStore";
import { api } from "@/lib/api";
import {
  Bell,
  Box,
  CheckCircle,
  ChevronsUpDown,
  ClipboardList,
  FileText,
  FolderOpen,
  Layers,
  LayoutDashboard,
  LogOut,
  Moon,
  Search,
  Settings,
  Settings2,
  Sun,
  Upload,
} from "lucide-react";
import type { PaginatedResponse, Project } from "@/types";

const navGroups = [
  {
    label: null,
    items: [
      {
        id: "dashboard",
        to: "/dashboard",
        icon: LayoutDashboard,
        label: "ダッシュボード",
      },
      {
        id: "projects",
        to: "/projects",
        icon: FolderOpen,
        label: "プロジェクト",
      },
    ],
  },
  {
    label: "情報管理",
    items: [
      { id: "containers", to: "containers", icon: Box, label: "情報コンテナ" },
      { id: "upload", to: "upload", icon: Upload, label: "アップロード" },
      {
        id: "naming-rules",
        to: "naming-rules",
        icon: Settings2,
        label: "命名規則設定",
      },
      {
        id: "approvals",
        to: "/approvals",
        icon: CheckCircle,
        label: "承認タスク",
      },
      {
        id: "requirements",
        to: "/requirements",
        icon: FileText,
        label: "要求文書 (EIR/BEP)",
      },
    ],
  },
  {
    label: "統制・監査",
    items: [
      {
        id: "audit",
        to: "/audit-logs",
        icon: ClipboardList,
        label: "監査ログ",
      },
      { id: "settings", to: "/settings", icon: Settings, label: "設定" },
      {
        id: "rbac",
        to: "/settings/roles",
        icon: Settings2,
        label: "ロール管理",
      },
    ],
  },
];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const { projectId } = useParams<{ projectId?: string }>();
  const [theme, setTheme] = useState(
    () => localStorage.getItem("obim-theme") || "light",
  );

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
  });

  const activeProject = useMemo(() => {
    const idFromPath =
      projectId ?? location.pathname.match(/\/projects\/([^/]+)/)?.[1];
    return (
      projects?.items.find((p) => p.id === idFromPath) ??
      projects?.items[0] ??
      null
    );
  }, [location.pathname, projectId, projects?.items]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("obim-theme", theme);
  }, [theme]);

  const handleLogout = async () => {
    const accessToken = localStorage.getItem("access_token");
    const refreshToken = localStorage.getItem("refresh_token");
    if (accessToken) {
      try {
        await api.post(
          "/auth/logout",
          { refresh_token: refreshToken },
          { headers: { Authorization: `Bearer ${accessToken}` } },
        );
      } catch {
        // best-effort: local session is cleared regardless
      }
    }
    logout();
    navigate("/login");
  };

  const resolveTo = (to: string) => {
    if (to === "containers") {
      return activeProject?.id
        ? `/projects/${activeProject.id}/containers`
        : "/projects";
    }
    if (to === "upload") {
      return activeProject?.id
        ? `/projects/${activeProject.id}/upload`
        : "/projects";
    }
    return to;
  };

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: "var(--bg)", color: "var(--text)" }}
    >
      <aside
        className="hidden w-[248px] shrink-0 flex-col border-r lg:flex"
        style={{ background: "var(--sidebar)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2 px-4 pb-2 pt-3">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ background: "var(--text)", color: "var(--bg)" }}
          >
            <Layers className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-bold">Open BIM</p>
            <p
              className="text-[10px] tracking-[0.06em]"
              style={{ color: "var(--text-3)" }}
            >
              情報基盤 · ISO 19650
            </p>
          </div>
        </div>

        <div className="px-3 pb-2 pt-1">
          <button
            className="flex w-full items-center gap-2 rounded-[10px] border p-2 text-left shadow-sm"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
            }}
          >
            <span className="mono flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)] text-xs font-bold text-white">
              {activeProject?.code ?? "BIM"}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[12.5px] font-semibold">
                {activeProject?.name ?? "プロジェクト未選択"}
              </span>
              <span
                className="block truncate text-[10.5px]"
                style={{ color: "var(--text-3)" }}
              >
                {activeProject?.applied_standard ?? "ISO 19650"}
              </span>
            </span>
            <ChevronsUpDown
              className="h-4 w-4"
              style={{ color: "var(--text-3)" }}
            />
          </button>
        </div>

        <nav className="flex-1 overflow-auto px-2 pb-3">
          {navGroups.map((group, groupIndex) => (
            <div key={groupIndex} className="mb-3">
              {group.label && (
                <div
                  className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.06em]"
                  style={{ color: "var(--text-3)" }}
                >
                  {group.label}
                </div>
              )}
              {group.items.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={label}
                  to={resolveTo(to)}
                  className={({ isActive }) =>
                    `mb-0.5 flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors ${
                      isActive ? "font-semibold" : "font-medium"
                    }`
                  }
                  style={({ isActive }) => ({
                    background: isActive
                      ? "var(--primary-subtle)"
                      : "transparent",
                    color: isActive ? "var(--primary-text)" : "var(--text-2)",
                  })}
                >
                  <Icon className="h-4 w-4" />
                  <span className="flex-1">{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="px-3 pb-3">
          <div className="app-card p-3">
            <div className="mb-2 flex items-center justify-between">
              <span
                className="text-[11px] font-medium"
                style={{ color: "var(--text-2)" }}
              >
                命名規則 適合率
              </span>
              <span
                className="mono text-[12px] font-bold"
                style={{ color: "var(--success-fg)" }}
              >
                94%
              </span>
            </div>
            <div className="bar">
              <i style={{ width: "94%", background: "var(--success)" }} />
            </div>
          </div>
        </div>

        <div
          className="flex items-center gap-2 border-t p-3"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-xs font-semibold text-white">
            {user?.full_name?.slice(0, 1) ?? "U"}
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-[12.5px] font-semibold">
              {user?.full_name ?? "User"}
            </div>
            <div className="text-[10.5px]" style={{ color: "var(--text-3)" }}>
              BIMマネージャー
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="app-btn app-btn-ghost app-btn-icon app-btn-sm"
            title="ログアウト"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header
          className="flex h-14 shrink-0 items-center gap-3 border-b px-4 backdrop-blur"
          style={{ background: "var(--topbar)", borderColor: "var(--border)" }}
        >
          <div className="min-w-0 flex-1 text-[13px]">
            <span style={{ color: "var(--text-3)" }}>
              {activeProject ? `${activeProject.code} · ${activeProject.name}` : "BIM 情報基盤"}
            </span>
            <span className="mx-2" style={{ color: "var(--text-3)" }}>
              /
            </span>
            <span className="font-semibold">
              {pageTitle(location.pathname)}
            </span>
          </div>
          <button
            className="hidden h-[34px] w-60 items-center gap-2 rounded-lg border px-3 text-[13px] md:flex"
            style={{
              background: "var(--surface-2)",
              borderColor: "var(--border)",
              color: "var(--text-3)",
            }}
          >
            <Search className="h-4 w-4" />
            <span className="flex-1 text-left">検索...</span>
            <span
              className="mono rounded border px-1 text-[10px]"
              style={{ borderColor: "var(--border-strong)" }}
            >
              ⌘K
            </span>
          </button>
          <button
            className="app-btn app-btn-ghost app-btn-icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            title="テーマ切替"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </button>
          <button className="app-btn app-btn-ghost app-btn-icon" title="通知">
            <Bell className="h-4 w-4" />
          </button>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function pageTitle(pathname: string) {
  if (pathname.includes("upload")) return "アップロード";
  if (pathname.includes("containers")) return "情報コンテナ";
  if (pathname.includes("approvals")) return "承認タスク";
  if (pathname.includes("requirements")) return "要求文書";
  if (pathname.includes("audit-logs")) return "監査ログ";
  if (pathname.includes("projects")) return "プロジェクト";
  if (pathname.includes("settings")) return "設定";
  return "ダッシュボード";
}
