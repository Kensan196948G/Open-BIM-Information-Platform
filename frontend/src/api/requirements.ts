import { api } from "@/lib/api";

export type DocumentType =
  | "OIR"
  | "AIR"
  | "PIR"
  | "EIR"
  | "BEP"
  | "MIDP"
  | "TIDP"
  | "InformationProtocol"
  | "Supplementary";

export type DocumentStatus =
  "draft" | "under_review" | "approved" | "superseded" | "withdrawn";

export type ItemStatus = "not_met" | "partial" | "met";

export interface RequirementItem {
  id: string;
  document_id: string;
  item_no: string;
  what: string;
  when_required: string | null;
  how_required: string | null;
  for_whom: string | null;
  acceptance_criteria: string | null;
  responsible_user_id: string | null;
  status: ItemStatus;
  notes: string | null;
  due_date: string | null;
  milestone_name: string | null;
}

export interface RequirementsDocument {
  id: string;
  project_id: string;
  owner_user_id: string | null;
  doc_type: DocumentType;
  title: string;
  description: string | null;
  revision: string;
  status: DocumentStatus;
  effective_from: string | null;
  effective_to: string | null;
  created_at: string;
  updated_at: string;
  item_count: number;
  items: RequirementItem[];
}

export interface RequirementsDocumentCreate {
  doc_type: DocumentType;
  title: string;
  description?: string | null;
  revision?: string;
  status?: DocumentStatus;
}

export interface RequirementItemCreate {
  item_no: string;
  what: string;
  when_required?: string | null;
  how_required?: string | null;
  for_whom?: string | null;
  acceptance_criteria?: string | null;
  status?: ItemStatus;
  notes?: string | null;
  due_date?: string | null;
  milestone_name?: string | null;
}

export interface RequirementItemUpdate {
  item_no?: string;
  what?: string;
  when_required?: string | null;
  how_required?: string | null;
  for_whom?: string | null;
  acceptance_criteria?: string | null;
  status?: ItemStatus;
  notes?: string | null;
  due_date?: string | null;
  milestone_name?: string | null;
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
    body: Partial<RequirementsDocumentCreate>,
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

  createItem: (
    projectId: string,
    docId: string,
    body: RequirementItemCreate,
  ): Promise<RequirementItem> =>
    api
      .post<RequirementItem>(
        `/projects/${projectId}/requirements/${docId}/items`,
        body,
      )
      .then((r) => r.data),

  updateItem: (
    projectId: string,
    docId: string,
    itemId: string,
    body: RequirementItemUpdate,
  ): Promise<RequirementItem> =>
    api
      .patch<RequirementItem>(
        `/projects/${projectId}/requirements/${docId}/items/${itemId}`,
        body,
      )
      .then((r) => r.data),

  deleteItem: (
    projectId: string,
    docId: string,
    itemId: string,
  ): Promise<void> =>
    api
      .delete(`/projects/${projectId}/requirements/${docId}/items/${itemId}`)
      .then(() => undefined),
};
