import type { AuditLog, NamingRuleResponse, Project } from "@/types";
import {
  auditLogs,
  containersByProject,
  demoContainers,
  demoNamingRule,
  demoProjects,
} from "./designData";

// ---------------------------------------------------------------------------
// Helper — build a NamingRuleResponse for any project id
// ---------------------------------------------------------------------------

function namingRuleForProject(projectId: string): NamingRuleResponse {
  return { ...demoNamingRule, id: `nr-${projectId}`, project_id: projectId };
}

// ---------------------------------------------------------------------------
// Helper — containers for a given project id
// ---------------------------------------------------------------------------

function containersForProject(projectId: string) {
  const items = containersByProject[projectId] ?? demoContainers;
  return { items, total: items.length, page: 1, size: 50 };
}

// ---------------------------------------------------------------------------
// Public function
// ---------------------------------------------------------------------------

/**
 * Returns mock response data for a given API URL + method, or `undefined`
 * when the route is not recognised (allowing the real response to pass through).
 */
export function getMockResponse(
  url: string,
  method: string,
  requestData?: unknown,
): unknown {
  const m = method.toLowerCase();

  // POST /auth/login
  if (url === "/auth/login" && m === "post") {
    return { access_token: "demo-token-2026", token_type: "bearer" };
  }

  // GET /auth/me
  if (url === "/auth/me" && m === "get") {
    return {
      id: "u1",
      email: "demo@example.com",
      username: "bim_manager",
      full_name: "佐藤 健一",
      is_active: true,
      is_platform_admin: false,
    };
  }

  // GET /projects
  if (url === "/projects" && m === "get") {
    return {
      items: demoProjects,
      total: demoProjects.length,
      page: 1,
      size: 20,
    };
  }

  // POST /projects
  if (url === "/projects" && m === "post") {
    const body = requestData as Record<string, unknown> | null | undefined;
    const parsed =
      typeof body === "string"
        ? (JSON.parse(body) as Record<string, unknown>)
        : (body ?? {});
    const newProject: Project = {
      id: `proj-${Date.now()}`,
      organization_id: "org-demo",
      name: String(parsed["name"] ?? "新規プロジェクト"),
      code: String(parsed["code"] ?? "NEW"),
      description: String(parsed["description"] ?? ""),
      status: "active",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: null,
      applied_standard: "ISO 19650-2:2018",
    };
    return newProject;
  }

  // GET /projects/{id}/containers
  const containersGetMatch = url.match(/^\/projects\/([^/]+)\/containers$/);
  if (containersGetMatch && m === "get") {
    const projectId = containersGetMatch[1];
    return containersForProject(projectId ?? "demo");
  }

  // POST /projects/{id}/containers
  const containersPostMatch = url.match(/^\/projects\/([^/]+)\/containers$/);
  if (containersPostMatch && m === "post") {
    const projectId = containersPostMatch[1] ?? "demo";
    const body = requestData as Record<string, unknown> | null | undefined;
    const parsed =
      typeof body === "string"
        ? (JSON.parse(body) as Record<string, unknown>)
        : (body ?? {});
    return {
      id: `c-${Date.now()}`,
      project_id: projectId,
      identifier: String(
        parsed["identifier"] ??
          `${projectId.toUpperCase()}-ARC-XX-ZZ-DR-A-0001`,
      ),
      title: String(parsed["title"] ?? "新規コンテナ"),
      container_type: parsed["container_type"] ?? "document",
      current_state: "WIP",
      current_revision: "P01.00",
      current_branch: null,
      security_level: parsed["security_level"] ?? "limited",
      naming_valid: true,
      naming_issues: null,
      created_by: "u1",
    };
  }

  // POST /projects/{id}/containers/{cid}/transition
  const transitionMatch = url.match(
    /^\/projects\/([^/]+)\/containers\/([^/]+)\/transition$/,
  );
  if (transitionMatch && m === "post") {
    const body = requestData as Record<string, unknown> | null | undefined;
    const parsed =
      typeof body === "string"
        ? (JSON.parse(body) as Record<string, unknown>)
        : (body ?? {});
    const containerId = transitionMatch[2] ?? "";
    const existing = demoContainers.find((c) => c.id === containerId);
    return {
      id: containerId,
      project_id: transitionMatch[1] ?? "demo",
      identifier: existing?.identifier ?? containerId,
      title: existing?.title ?? "",
      container_type: existing?.type ?? "document",
      current_state: parsed["to_state"] ?? "Shared",
      current_revision: existing?.revision ?? "P01.00",
      current_branch: null,
      security_level: existing?.security ?? "limited",
      naming_valid: existing?.naming === "pass",
      naming_issues: existing?.issue ?? null,
      created_by: existing?.owner ?? "u1",
    };
  }

  // GET /audit-logs
  if (url === "/audit-logs" && m === "get") {
    const items: AuditLog[] = auditLogs;
    return { items, total: items.length, page: 1, size: 50 };
  }

  // GET /naming-rules/projects/{id}
  const namingRuleMatch = url.match(/^\/naming-rules\/projects\/([^/]+)$/);
  if (namingRuleMatch && m === "get") {
    const projectId = namingRuleMatch[1] ?? "demo";
    return namingRuleForProject(projectId);
  }

  // Route not recognised — return undefined so caller can pass through
  return undefined;
}
