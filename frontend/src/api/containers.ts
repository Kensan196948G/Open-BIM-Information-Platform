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

export async function getDownloadUrl(
  projectId: string,
  containerId: string,
  fileId: string,
): Promise<string> {
  const res = await api.get<{ download_url: string }>(
    `/projects/${projectId}/containers/${containerId}/files/${fileId}/download-url`,
  );
  return res.data.download_url;
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
