import { api } from "@/lib/api";

export async function downloadAuditLogCsv(): Promise<void> {
  const res = await api.get<Blob>("/audit-logs/export.csv", {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "audit-logs.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
