export type ContainerState = "WIP" | "Shared" | "Published" | "Archived";
export type ContainerType =
  | "document"
  | "drawing"
  | "model"
  | "ifc"
  | "bcf"
  | "other";
export type SecurityLevel =
  | "public"
  | "limited"
  | "confidential"
  | "restricted";
export type ProjectStatus = "active" | "suspended" | "completed" | "archived";

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_platform_admin: boolean;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  description: string | null;
  status: ProjectStatus;
  start_date: string | null;
  end_date: string | null;
  applied_standard: string;
}

export interface InformationContainer {
  id: string;
  project_id: string;
  identifier: string;
  title: string;
  container_type: ContainerType;
  current_state: ContainerState;
  current_revision: string;
  current_branch: string | null;
  security_level: SecurityLevel;
  naming_valid: boolean;
  naming_issues: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  occurred_at: string;
  event_type: string;
  actor_id: string | null;
  actor_ip: string | null;
  target_type: string;
  target_id: string | null;
  operation: string;
  result: string;
  reason: string | null;
}

export interface ContainerFile {
  id: string;
  container_id: string;
  original_filename: string;
  storage_key: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  uploaded_by: string;
  created_at: string;
}

export interface PendingApproval {
  approval_id: string;
  workflow_id: string;
  workflow_status: string;
  approval_stage: string;
  target_type: string;
  target_id: string;
  project_id: string;
  project_name: string;
  container_id: string | null;
  container_identifier: string | null;
  container_title: string | null;
  container_state: string | null;
  initiated_by: string;
  created_at: string | null;
  comment: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  size?: number;
}

export interface SegmentDefinition {
  key: string;
  label: string;
  required: boolean;
  max_length: number | null;
  min_length: number | null;
  allowed_values: string[];
  pattern: string | null;
  description: string;
}

export interface NamingRuleResponse {
  id: string;
  project_id: string;
  separator: string;
  segments: SegmentDefinition[];
  is_default: boolean;
}
