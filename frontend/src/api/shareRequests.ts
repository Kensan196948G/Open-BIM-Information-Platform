import { api } from "@/lib/api";

export type ShareRequestStatus =
  "pending" | "approved" | "rejected" | "revoked" | "expired";

export interface ShareRequest {
  id: string;
  container_id: string;
  requested_by_user_id: string;
  approved_by_user_id: string | null;
  reason: string | null;
  status: ShareRequestStatus;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShareRequestApproveResponse extends ShareRequest {
  token: string;
  share_url_path: string;
}

export interface ShareRequestListResponse {
  items: ShareRequest[];
  total: number;
}

function basePath(projectId: string, containerId: string): string {
  return `/projects/${projectId}/containers/${containerId}/share-requests`;
}

export const shareRequestsApi = {
  list: (
    projectId: string,
    containerId: string,
  ): Promise<ShareRequestListResponse> =>
    api
      .get<ShareRequestListResponse>(basePath(projectId, containerId))
      .then((r) => r.data),

  create: (
    projectId: string,
    containerId: string,
    reason?: string | null,
  ): Promise<ShareRequest> =>
    api
      .post<ShareRequest>(basePath(projectId, containerId), { reason })
      .then((r) => r.data),

  approve: (
    projectId: string,
    containerId: string,
    shareRequestId: string,
    expiresInHours = 72,
  ): Promise<ShareRequestApproveResponse> =>
    api
      .post<ShareRequestApproveResponse>(
        `${basePath(projectId, containerId)}/${shareRequestId}/approve`,
        { expires_in_hours: expiresInHours },
      )
      .then((r) => r.data),

  reject: (
    projectId: string,
    containerId: string,
    shareRequestId: string,
    reason?: string | null,
  ): Promise<ShareRequest> =>
    api
      .post<ShareRequest>(
        `${basePath(projectId, containerId)}/${shareRequestId}/reject`,
        { reason },
      )
      .then((r) => r.data),

  revoke: (
    projectId: string,
    containerId: string,
    shareRequestId: string,
  ): Promise<ShareRequest> =>
    api
      .post<ShareRequest>(
        `${basePath(projectId, containerId)}/${shareRequestId}/revoke`,
        {},
      )
      .then((r) => r.data),
};
