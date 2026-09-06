import { api } from "@/lib/api";
import type {
  ContainerFile,
  InformationContainer,
  PaginatedResponse,
} from "@/types";

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
  await api.delete(
    `/projects/${projectId}/containers/${containerId}/files/${fileId}`,
  );
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

// ─── Revision diff (Issue #52) ─────────────────────────────────────────────

export interface RevisionDiffFileMeta {
  id: string | null;
  original_filename: string | null;
  content_type: string | null;
  file_size_bytes: number | null;
  checksum_sha256: string | null;
}

export interface RevisionDiffTextField {
  field: string;
  from_value: string | null;
  to_value: string | null;
  changed: boolean;
  diff_lines: string[];
}

export interface RevisionDiffFileComparison {
  from_file: RevisionDiffFileMeta | null;
  to_file: RevisionDiffFileMeta | null;
  original_filename_changed: boolean;
  content_type_changed: boolean;
  file_size_bytes_changed: boolean;
  checksum_sha256_changed: boolean;
  identical: boolean;
}

export interface RevisionDiffSummary {
  id: string;
  revision_code: string;
  version_code: string | null;
  change_reason: string | null;
  change_summary: string | null;
  created_by: string;
  created_at: string;
  file: RevisionDiffFileMeta | null;
}

export interface RevisionDiffResponse {
  container_id: string;
  from_revision: RevisionDiffSummary;
  to_revision: RevisionDiffSummary;
  text_diffs: RevisionDiffTextField[];
  file_diff: RevisionDiffFileComparison;
}

export async function getContainerRevisionDiff(
  projectId: string,
  containerId: string,
  fromRevisionId: string,
  toRevisionId: string,
): Promise<RevisionDiffResponse> {
  const res = await api.get<RevisionDiffResponse>(
    `/projects/${projectId}/containers/${containerId}/revisions/diff`,
    {
      params: {
        from_revision_id: fromRevisionId,
        to_revision_id: toRevisionId,
      },
    },
  );
  return res.data;
}
