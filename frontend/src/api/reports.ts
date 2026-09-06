import { api } from "@/lib/api";

export type ViolationType = "naming_non_compliant" | "rejected";

export interface NamingViolationItem {
  container_id: string;
  identifier: string;
  title: string;
  violation_type: ViolationType;
  reason: string | null;
  occurred_at: string | null;
  current_state: string;
  current_assignee_id: string | null;
}

export interface NamingViolationsResponse {
  items: NamingViolationItem[];
  total: number;
}

export interface ApprovalDelayAssignee {
  assignee_id: string;
  task_type: string;
  status: string;
}

export interface ApprovalDelayItem {
  workflow_id: string;
  workflow_type: string;
  target_type: string;
  target_id: string;
  container_identifier: string | null;
  container_title: string | null;
  created_at: string;
  elapsed_hours: number;
  assignees: ApprovalDelayAssignee[];
}

export interface ApprovalDelaysResponse {
  items: ApprovalDelayItem[];
  total: number;
  threshold_hours: number;
}

export interface RequirementsStatusItem {
  document_id: string;
  doc_type: string;
  title: string;
  revision: string;
  met_count: number;
  partial_count: number;
  not_met_count: number;
  total_count: number;
  fulfillment_rate: number;
}

export interface RequirementsStatusResponse {
  items: RequirementsStatusItem[];
  total: number;
}

export const reportsApi = {
  getNamingViolations: (projectId: string): Promise<NamingViolationsResponse> =>
    api
      .get<NamingViolationsResponse>(
        `/projects/${projectId}/reports/naming-violations`,
      )
      .then((r) => r.data),

  getApprovalDelays: (
    projectId: string,
    thresholdHours?: number,
  ): Promise<ApprovalDelaysResponse> =>
    api
      .get<ApprovalDelaysResponse>(
        `/projects/${projectId}/reports/approval-delays`,
        thresholdHours !== undefined
          ? { params: { threshold_hours: thresholdHours } }
          : undefined,
      )
      .then((r) => r.data),

  getRequirementsStatus: (
    projectId: string,
  ): Promise<RequirementsStatusResponse> =>
    api
      .get<RequirementsStatusResponse>(
        `/projects/${projectId}/reports/requirements-status`,
      )
      .then((r) => r.data),
};
