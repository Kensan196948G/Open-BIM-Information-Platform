import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Shield } from "lucide-react";
import type { AuditLog, PaginatedResponse } from "@/types";

const RESULT_COLORS: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  failure: "bg-red-100 text-red-700",
  denied: "bg-amber-100 text-amber-700",
};

export default function AuditLogsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () =>
      api.get<PaginatedResponse<AuditLog>>("/audit-logs").then((r) => r.data),
  });

  return (
    <div className="p-8">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-6 h-6 text-blue-500" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">監査ログ</h1>
          <p className="text-gray-500 text-sm">
            ISO 19650 / J-SOX 準拠 操作履歴
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">
                日時
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">
                イベント種別
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">
                対象
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">
                操作
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">
                結果
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-400">
                  読み込み中...
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-400">
                  ログがありません
                </td>
              </tr>
            ) : (
              data?.items.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs font-mono text-gray-500 whitespace-nowrap">
                    {log.occurred_at.slice(0, 19).replace("T", " ")}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-700">
                    {log.event_type}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {log.target_type}
                    {log.target_id && (
                      <span className="ml-1 font-mono text-gray-400">
                        #{log.target_id.slice(0, 8)}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-700">
                    {log.operation}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-medium ${
                        RESULT_COLORS[log.result] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {log.result}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
