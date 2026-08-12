import { api } from "@/lib/api";
import type { PendingApproval } from "@/types";

export async function listMyPendingApprovals(): Promise<PendingApproval[]> {
  const res = await api.get<PendingApproval[]>("/workflows/tasks/mine");
  return res.data;
}

export async function actOnApproval(
  workflowId: string,
  approvalId: string,
  result: "approved" | "rejected" | "returned" | "conditionally_approved",
  comment?: string,
): Promise<void> {
  await api.post(`/workflows/${workflowId}/approvals/${approvalId}/act`, {
    result,
    comment: comment || null,
  });
}
