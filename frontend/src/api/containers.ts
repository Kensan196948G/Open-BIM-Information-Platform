import { api } from "@/lib/api";
import type { ContainerFile, InformationContainer, PaginatedResponse } from "@/types";

export async function listFiles(
  projectId: string,
  containerId: string,
): Promise<ContainerFile[]> {
  const res = await api.get<{ items: ContainerFile[]; total: number }>(
    `/projects/${projectId}/containers/${containerId}/files`,
  );
  return res.data.items;
}

export async function deleteFile(
  projectId: string,
  containerId: string,
  fileId: string,
): Promise<void> {
  await api.delete(`/projects/${projectId}/containers/${containerId}/files/${fileId}`);
}

export async function downloadFile(
  projectId: string,
  containerId: string,
  fileId: string,
): Promise<Blob> {
  const res = await api.get<Blob>(
    `/projects/${projectId}/containers/${containerId}/files/${fileId}/download`,
    { responseType: "blob" },
  );
  return res.data;
}

export class DownloadHttpError extends Error {
  constructor(readonly status: number) {
    super(`Download failed (${status})`);
    this.name = "DownloadHttpError";
  }
}

async function fetchDownload(path: string): Promise<Response> {
  const request = (token: string | null) =>
    fetch(path, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  let response = await request(localStorage.getItem("access_token"));
  if (response.status === 401) {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      const refreshed = await api.post<{ access_token: string; refresh_token: string }>(
        "/auth/refresh",
        { refresh_token: refreshToken },
      );
      localStorage.setItem("access_token", refreshed.data.access_token);
      localStorage.setItem("refresh_token", refreshed.data.refresh_token);
      response = await request(refreshed.data.access_token);
    }
  }
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
  }
  if (!response.ok) throw new DownloadHttpError(response.status);
  return response;
}

export async function downloadFileToWritable(
  projectId: string,
  containerId: string,
  fileId: string,
  writable: FileSystemWritableFileStream,
): Promise<void> {
  try {
    const path = `/api/v1/projects/${encodeURIComponent(projectId)}/containers/${encodeURIComponent(containerId)}/files/${encodeURIComponent(fileId)}/download`;
    const response = await fetchDownload(path);
    if (!response.body) throw new Error("Download stream is unavailable");
    await response.body.pipeTo(writable);
  } catch (error) {
    // A failed fetch before pipeTo starts otherwise leaves the temporary save
    // handle open. abort() also preserves an existing destination file.
    await writable.abort(error).catch(() => undefined);
    throw error;
  }
}

export async function listContainers(
  projectId: string,
  params?: { state?: string; page?: number; size?: number },
): Promise<PaginatedResponse<InformationContainer>> {
  const res = await api.get<PaginatedResponse<InformationContainer>>(
    `/projects/${projectId}/containers`,
    { params },
  );
  return res.data;
}

export interface ContainerRevisionItem {
  id: string;
  revision_code: string;
  version_code: string;
  change_reason: string | null;
  change_summary: string | null;
  created_by: string;
  created_at: string | null;
  file: {
    id: string;
    original_filename: string;
    file_size_bytes: number;
    checksum_sha256: string;
  } | null;
}

export async function listContainerRevisions(
  projectId: string,
  containerId: string,
): Promise<ContainerRevisionItem[]> {
  const res = await api.get<ContainerRevisionItem[]>(
    `/projects/${projectId}/containers/${containerId}/revisions`,
  );
  return res.data;
}
