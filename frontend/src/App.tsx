import { Navigate, Route, Routes } from "react-router-dom";
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
import Layout from "@/components/Layout";
import { Settings } from "lucide-react";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
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
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="requirements" element={<RequirementsPage />} />
        <Route path="audit-logs" element={<AuditLogsPage />} />
        <Route
          path="settings"
          element={
            <div className="mx-auto max-w-4xl p-6">
              <div className="app-card-pad py-16 text-center">
                <Settings className="mx-auto mb-3 h-10 w-10" style={{ color: "var(--text-3)" }} />
                <div className="t-h2">設定</div>
                <div className="t-sec mt-1">
                  命名規則マスタ、属性定義、ロール権限の管理画面です。
                </div>
              </div>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
