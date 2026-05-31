import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { FolderOpen, Plus, ChevronRight } from "lucide-react";
import type { PaginatedResponse, Project } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  active: "稼働中",
  suspended: "停止中",
  completed: "完了",
  archived: "アーカイブ",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  suspended: "bg-amber-100 text-amber-700",
  completed: "bg-blue-100 text-blue-700",
  archived: "bg-gray-100 text-gray-600",
};

export default function ProjectsPage() {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () =>
      api.get<PaginatedResponse<Project>>("/projects").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (body: { name: string; code: string }) =>
      api.post<Project>("/projects", body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setName("");
      setCode("");
    },
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">プロジェクト</h1>
          <p className="text-gray-500 text-sm mt-1">
            📊 全{data?.total ?? 0}件
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          新規作成
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate({ name, code });
          }}
          className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6 space-y-3"
        >
          <h2 className="font-semibold text-blue-900">新規プロジェクト</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              placeholder="プロジェクト名"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <input
              required
              placeholder="プロジェクトコード (例: PROJ-001)"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? "作成中..." : "作成"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
            >
              キャンセル
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">読み込み中...</div>
      ) : (
        <div className="space-y-2">
          {data?.items.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}/containers`}
              className="flex items-center gap-4 bg-white border border-gray-100 rounded-xl p-4 hover:border-blue-200 hover:shadow-sm transition-all"
            >
              <FolderOpen className="w-8 h-8 text-blue-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 truncate">
                  {project.name}
                </p>
                <p className="text-xs text-gray-400">
                  {project.code} · {project.applied_standard}
                </p>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded font-medium ${STATUS_COLORS[project.status]}`}
              >
                {STATUS_LABELS[project.status]}
              </span>
              <ChevronRight className="w-4 h-4 text-gray-300 shrink-0" />
            </Link>
          ))}
          {data?.items.length === 0 && (
            <div className="text-center py-16 text-gray-400">
              <FolderOpen className="w-12 h-12 mx-auto mb-3 text-gray-200" />
              <p>プロジェクトがありません。新規作成してください。</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
