import { api } from "@/lib/api";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
}

export interface Permission {
  id: string;
  code: string;
  description: string | null;
  category: string;
}

export interface Role {
  id: string;
  organization_id: string | null;
  name: string;
  description: string | null;
  is_system_role: boolean;
  permissions: Permission[];
}

export interface RoleCreate {
  name: string;
  description?: string;
}

export interface RoleUpdate {
  name?: string;
  description?: string;
}

export const rbacApi = {
  listOrganizations: () =>
    api.get<Organization[]>("/organizations").then((r) => r.data),

  listPermissions: () =>
    api.get<Permission[]>("/permissions").then((r) => r.data),

  listRoles: (orgId: string) =>
    api.get<Role[]>(`/organizations/${orgId}/roles`).then((r) => r.data),

  createRole: (orgId: string, body: RoleCreate) =>
    api.post<Role>(`/organizations/${orgId}/roles`, body).then((r) => r.data),

  updateRole: (roleId: string, body: RoleUpdate) =>
    api.patch<Role>(`/roles/${roleId}`, body).then((r) => r.data),

  deleteRole: (roleId: string) => api.delete(`/roles/${roleId}`),

  assignPermission: (roleId: string, permissionId: string) =>
    api
      .post<Role>(`/roles/${roleId}/permissions`, {
        permission_id: permissionId,
      })
      .then((r) => r.data),

  revokePermission: (roleId: string, permissionId: string) =>
    api.delete(`/roles/${roleId}/permissions/${permissionId}`),
};
