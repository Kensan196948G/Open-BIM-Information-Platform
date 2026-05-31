import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { FolderOpen, FileText, CheckCircle, AlertTriangle } from "lucide-react";
import type { PaginatedResponse, Project } from "@/types";

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
  });

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">ダッシュボード</h1>
      <p className="text-gray-500 text-sm mb-8">ISO 19650 BIM 情報管理状況</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={FolderOpen}
          label="プロジェクト数"
          value={projects?.total ?? "-"}
          color="bg-blue-500"
        />
        <StatCard
          icon={FileText}
          label="情報コンテナ"
          value="-"
          color="bg-violet-500"
        />
        <StatCard
          icon={CheckCircle}
          label="承認済み"
          value="-"
          color="bg-green-500"
        />
        <StatCard
          icon={AlertTriangle}
          label="レビュー待ち"
          value="-"
          color="bg-amber-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="font-semibold text-gray-900 mb-4">
            📋 アクティブプロジェクト
          </h2>
          {projects?.items.length === 0 ? (
            <p className="text-gray-400 text-sm">プロジェクトがありません</p>
          ) : (
            <ul className="space-y-2">
              {projects?.items.slice(0, 5).map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between py-2 border-b border-gray-50"
                >
                  <span className="text-sm font-medium">{p.name}</span>
                  <span className="text-xs text-gray-400">{p.code}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="font-semibold text-gray-900 mb-4">
            🔁 CDE 状態サマリー
          </h2>
          <div className="space-y-3">
            {[
              { state: "WIP", color: "bg-gray-200 text-gray-700", count: "-" },
              {
                state: "Shared",
                color: "bg-blue-100 text-blue-700",
                count: "-",
              },
              {
                state: "Published",
                color: "bg-green-100 text-green-700",
                count: "-",
              },
              {
                state: "Archived",
                color: "bg-amber-100 text-amber-700",
                count: "-",
              },
            ].map(({ state, color, count }) => (
              <div key={state} className="flex items-center justify-between">
                <span
                  className={`text-xs font-semibold px-2 py-1 rounded ${color}`}
                >
                  {state}
                </span>
                <span className="text-sm text-gray-600 font-medium">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
