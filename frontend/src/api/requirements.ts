import { api } from "@/lib/api";

export type DocumentType =
  | "OIR"
  | "AIR"
  | "PIR"
  | "EIR"
  | "BEP"
  | "MIDP"
  | "TIDP"
  | "Other";

export type DocumentStatus =
  | "draft"
  | "under_review"
  | "approved"
  | "superseded"
  | "withdrawn";

export type ItemStatus = "not_met" | "partial" | "met";

export interface RequirementItem {
  id: string;
  document_id: string;
  sequence_number: number;
  what: string;
  when_required: string | null;
  how: string | null;
  who: string | null;
  status: ItemStatus;
  notes: string | null;
}

export interface RequirementsDocument {
  id: string;
  project_id: string;
  document_type: DocumentType;
  title: string;
  description: string | null;
  revision: string;
  status: DocumentStatus;
  owner_id: string;
  created_at: string;
  updated_at: string;
  item_count: number;
  items: RequirementItem[];
}

export interface RequirementsDocumentCreate {
  document_type: DocumentType;
  title: string;
  description?: string;
  revision?: string;
  status?: DocumentStatus;
}

export interface RequirementsDocumentUpdate {
  title?: string;
  description?: string;
  revision?: string;
  status?: DocumentStatus;
}

export interface RequirementsDocumentListResponse {
  items: RequirementsDocument[];
  total: number;
}

export const requirementsApi = {
  listDocuments: (
    projectId: string,
  ): Promise<RequirementsDocumentListResponse> =>
    api
      .get<RequirementsDocumentListResponse>(
        `/projects/${projectId}/requirements`,
      )
      .then((r) => r.data),

  getDocument: (
    projectId: string,
    docId: string,
  ): Promise<RequirementsDocument> =>
    api
      .get<RequirementsDocument>(`/projects/${projectId}/requirements/${docId}`)
      .then((r) => r.data),

  createDocument: (
    projectId: string,
    body: RequirementsDocumentCreate,
  ): Promise<RequirementsDocument> =>
    api
      .post<RequirementsDocument>(`/projects/${projectId}/requirements`, body)
      .then((r) => r.data),

  updateDocument: (
    projectId: string,
    docId: string,
    body: RequirementsDocumentUpdate,
  ): Promise<RequirementsDocument> =>
    api
      .patch<RequirementsDocument>(
        `/projects/${projectId}/requirements/${docId}`,
        body,
      )
      .then((r) => r.data),

  deleteDocument: (projectId: string, docId: string): Promise<void> =>
    api
      .delete(`/projects/${projectId}/requirements/${docId}`)
      .then(() => undefined),
};
