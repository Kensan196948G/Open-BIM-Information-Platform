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
