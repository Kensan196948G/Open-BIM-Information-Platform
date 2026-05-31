import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { FileText, Plus, ArrowRight } from "lucide-react";
import type {
  InformationContainer,
  PaginatedResponse,
  ContainerState,
} from "@/types";

const STATE_COLORS: Record<ContainerState, string> = {
  WIP: "bg-gray-100 text-gray-700",
  Shared: "bg-blue-100 text-blue-700",
  Published: "bg-green-100 text-green-700",
  Archived: "bg-amber-100 text-amber-700",
};

const TRANSITION_ACTIONS: Partial<
  Record<ContainerState, { action: string; label: string; next: string }>
> = {
  WIP: { action: "submit", label: "Shared へ提出", next: "Shared" },
  Shared: { action: "approve", label: "Published へ承認", next: "Published" },
  Published: { action: "archive", label: "Archive へ保管", next: "Archived" },
};

export default function ContainersPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [showForm, setShowForm] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [title, setTitle] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["containers", projectId],
    queryFn: () =>
      api
        .get<
          PaginatedResponse<InformationContainer>
        >(`/projects/${projectId}/containers`)
        .then((r) => r.data),
    enabled: !!projectId,
  });

  const createMutation = useMutation({
    mutationFn: (body: { identifier: string; title: string }) =>
      api.post(`/projects/${projectId}/containers`, body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["containers", projectId] });
      setShowForm(false);
      setIdentifier("");
      setTitle("");
    },
  });

  const transitionMutation = useMutation({
    mutationFn: ({
      containerId,
      action,
    }: {
      containerId: string;
      action: string;
    }) =>
      api
        .post(`/projects/${projectId}/containers/${containerId}/transition`, {
          action,
          target_state:
            TRANSITION_ACTIONS[
              data?.items.find((c) => c.id === containerId)
                ?.current_state as ContainerState
            ]?.next,
        })
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["containers", projectId] });
    },
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">情報コンテナ</h1>
          <p className="text-gray-500 text-sm mt-1">
            📊 全{data?.total ?? 0}件 · CDE管理
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          コンテナ登録
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate({ identifier, title });
          }}
          className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6 space-y-3"
        >
          <h2 className="font-semibold text-blue-900">新規情報コンテナ</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              placeholder="識別子 (例: PRJ-XXX-A-01-DOC-001)"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
            />
            <input
              required
              placeholder="タイトル"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? "登録中..." : "登録"}
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
          {data?.items.map((container) => {
            const transition = TRANSITION_ACTIONS[container.current_state];
            return (
              <div
                key={container.id}
                className="bg-white border border-gray-100 rounded-xl p-4 flex items-center gap-4"
              >
                <FileText className="w-7 h-7 text-violet-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-sm font-semibold text-gray-900">
                    {container.identifier}
                  </p>
                  <p className="text-sm text-gray-500 truncate">
                    {container.title}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Rev: {container.current_revision}
                  </p>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded font-semibold ${STATE_COLORS[container.current_state]}`}
                >
                  {container.current_state}
                </span>
                {transition && (
                  <button
                    onClick={() =>
                      transitionMutation.mutate({
                        containerId: container.id,
                        action: transition.action,
                      })
                    }
                    disabled={transitionMutation.isPending}
                    className="flex items-center gap-1 text-xs border border-blue-300 text-blue-600 px-3 py-1.5 rounded-lg hover:bg-blue-50 disabled:opacity-50 whitespace-nowrap"
                  >
                    <ArrowRight className="w-3 h-3" />
                    {transition.label}
                  </button>
                )}
              </div>
            );
          })}
          {data?.items.length === 0 && (
            <div className="text-center py-16 text-gray-400">
              <FileText className="w-12 h-12 mx-auto mb-3 text-gray-200" />
              <p>コンテナがありません。登録してください。</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
