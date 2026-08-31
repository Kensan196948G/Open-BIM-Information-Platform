import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router";
import { api } from "@/lib/api";
import { useAuthStore } from "@/hooks/useAuthStore";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import ProjectsPage from "@/pages/ProjectsPage";
import ContainersPage from "@/pages/ContainersPage";
import AuditLogsPage from "@/pages/AuditLogsPage";
import ContainerDetailPage from "@/pages/ContainerDetailPage";
import UploadPage from "@/pages/UploadPage";
import ApprovalsPage from "@/pages/ApprovalsPage";
import RequirementsPage from "@/pages/RequirementsPage";
import NamingRulesPage from "@/pages/NamingRulesPage";
import NotificationsPage from "@/pages/NotificationsPage";
import RBACPage from "@/pages/RBACPage";
import SettingsPage from "@/pages/SettingsPage";
import Layout from "@/components/Layout";

/**
 * MVP 公開デモ用の自動ログイン。
 *
 * サーバーが AUTH_BYPASS=true で動いている場合だけ
 * POST /auth/demo-login がトークンを返す。無効な環境では 404 になるので
 * 何もせず、従来どおりログイン画面へ遷移する。
 */
function useDemoLogin(enabled: boolean) {
  const setAuth = useAuthStore((s) => s.setAuth);
  const [tried, setTried] = useState(!enabled);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    api
      .post("/auth/demo-login")
      .then(async ({ data }) => {
        const me = await api.get("/auth/me", {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        if (!cancelled) setAuth(data.access_token, me.data, data.refresh_token);
      })
      .catch(() => {
        /* バイパス無効（404）や一時障害。通常のログイン画面へ委ねる */
      })
      .finally(() => {
        if (!cancelled) setTried(true);
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, setAuth]);

  return tried;
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const demoTried = useDemoLogin(!token);
  // デモログインの判定が終わるまではログイン画面へ飛ばさない（ちらつき防止）
  if (!token && !demoTried) return null;
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route
          path="projects/:projectId/containers"
          element={<ContainersPage />}
        />
        <Route
          path="projects/:projectId/containers/:containerId"
          element={<ContainerDetailPage />}
        />
        <Route path="projects/:projectId/upload" element={<UploadPage />} />
        <Route
          path="projects/:projectId/naming-rules"
          element={<NamingRulesPage />}
        />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="requirements" element={<RequirementsPage />} />
        <Route path="audit-logs" element={<AuditLogsPage />} />
        <Route path="settings/roles" element={<RBACPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
