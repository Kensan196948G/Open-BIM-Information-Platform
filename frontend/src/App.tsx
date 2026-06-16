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
import NamingRulesPage from "@/pages/NamingRulesPage";
import RBACPage from "@/pages/RBACPage";
import SettingsPage from "@/pages/SettingsPage";
import Layout from "@/components/Layout";

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
        <Route
          path="projects/:projectId/naming-rules"
          element={<NamingRulesPage />}
        />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="requirements" element={<RequirementsPage />} />
        <Route path="audit-logs" element={<AuditLogsPage />} />
        <Route path="settings/roles" element={<RBACPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
