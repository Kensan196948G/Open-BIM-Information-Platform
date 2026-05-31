import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/hooks/useAuthStore";
import {
  Building2,
  FolderOpen,
  ClipboardList,
  LayoutDashboard,
  LogOut,
} from "lucide-react";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "ダッシュボード" },
  { to: "/projects", icon: FolderOpen, label: "プロジェクト" },
  { to: "/audit-logs", icon: ClipboardList, label: "監査ログ" },
];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Building2 className="w-6 h-6 text-blue-400" />
            <div>
              <p className="text-sm font-bold leading-tight">Open BIM</p>
              <p className="text-xs text-slate-400">情報基盤</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-700 hover:text-white"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-slate-700">
          <div className="px-3 py-2 text-xs text-slate-400 truncate">
            {user?.full_name}
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 rounded-lg"
          >
            <LogOut className="w-4 h-4" />
            ログアウト
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
