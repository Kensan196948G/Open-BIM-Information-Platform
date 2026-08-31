import { useState } from "react";
import { Link, useParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Download,
  FileText,
  Lock,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  deleteFile,
  downloadFile,
  downloadFileToWritable,
  DownloadHttpError,
  listContainerRevisions,
  listFiles,
} from "@/api/containers";
import {
  EmptyState,
  NamingBadge,
  SecurityPill,
  StatePill,
} from "@/components/design/Primitives";
import { fmtDate } from "@/lib/fmt";
import { demoInformationContainers, namingSegments, stateOrder } from "@/lib/designData";
import type {
  ContainerState,
  InformationContainer,
  PaginatedResponse,
} from "@/types";

const MAX_BLOB_DOWNLOAD_BYTES = 100 * 1024 * 1024;

interface SaveFilePickerWindow extends Window {
  showSaveFilePicker?: (options: { suggestedName: string }) => Promise<FileSystemFileHandle>;
}

const transitions: Partial<
  Record<ContainerState, Array<{ action: string; to: ContainerState; label: string; danger?: boolean }>>
> = {
  WIP: [{ action: "submit", to: "Shared", label: "Shared へ提出" }],
  Shared: [
    { action: "approve", to: "Published", label: "Published へ承認" },
    { action: "return", to: "WIP", label: "WIP へ差戻し", danger: true },
  ],
  Published: [{ action: "archive", to: "Archived", label: "Archive へ保管" }],
};

function namingStatus(container: InformationContainer): "pass" | "warn" | "fail" {
  if (container.naming_valid) return "pass";
  return container.naming_issues?.includes("不足") ? "fail" : "warn";
}

export default function ContainerDetailPage() {
  const { projectId, containerId } = useParams<{ projectId: string; containerId: string }>();
  const [tab, setTab] = useState<"overview" | "files" | "revisions" | "history">("overview");
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["containers", projectId],
    queryFn: () =>
      api
        .get<PaginatedResponse<InformationContainer>>(`/projects/${projectId}/containers`)
        .then((r) => r.data),
    enabled: !!projectId && projectId !== "demo",
  });

  const transitionMutation = useMutation({
    mutationFn: ({
      action,
      targetState,
    }: {
      action: string;
      targetState: ContainerState;
    }) =>
      api.post(`/projects/${projectId}/containers/${containerId}/transition`, {
        action,
        target_state: targetState,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["containers", projectId] }),
  });
  const { data: files = [] } = useQuery({
    queryKey: ["files", projectId, containerId],
    queryFn: () => listFiles(projectId!, containerId!),
    enabled: !!projectId && !!containerId && projectId !== "demo",
  });
  const deleteFileMutation = useMutation({
    mutationFn: (fileId: string) => deleteFile(projectId!, containerId!, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["files", projectId, containerId] });
      queryClient.invalidateQueries({ queryKey: ["containers", projectId] });
    },
  });
  const downloadMutation = useMutation({
    mutationFn: async ({
      file,
      handle,
    }: {
      file: (typeof files)[number];
      handle?: FileSystemFileHandle;
    }) => {
      if (handle) {
        const writable = await handle.createWritable();
        await downloadFileToWritable(projectId!, containerId!, file.id, writable);
        return { blob: null, filename: file.original_filename };
      }
      return {
        blob: await downloadFile(projectId!, containerId!, file.id),
        filename: file.original_filename,
      };
    },
    onMutate: () => setDownloadError(null),
    onSuccess: ({ blob, filename }) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    },
    onError: (error) => {
      if (error instanceof DownloadHttpError && error.status === 429) {
        setDownloadError("同時ダウンロードの上限に達しました。30秒後に再試行してください。");
        return;
      }
      if (error instanceof DownloadHttpError && error.status === 507) {
        setDownloadError("一時保存領域を使用できません。管理者へ連絡してください。");
        return;
      }
      setDownloadError("ファイルを取得できませんでした。ストレージの状態を確認してください。");
    },
  });

  const startDownload = async (file: (typeof files)[number]) => {
    setDownloadError(null);
    const picker = (window as SaveFilePickerWindow).showSaveFilePicker;
    if (picker) {
      try {
        const handle = await picker({ suggestedName: file.original_filename });
        downloadMutation.mutate({ file, handle });
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setDownloadError("保存先を開けませんでした。");
        }
      }
      return;
    }
    if (file.file_size_bytes > MAX_BLOB_DOWNLOAD_BYTES) {
      setDownloadError(
        "このブラウザーでは100 MBを超えるファイルを安全に保存できません。Chromium系ブラウザーを使用してください。",
      );
      return;
    }
    downloadMutation.mutate({ file });
  };
  const { data: revisions = [] } = useQuery({
    queryKey: ["revisions", projectId, containerId],
    queryFn: () => listContainerRevisions(projectId!, containerId!),
    enabled: !!projectId && !!containerId && projectId !== "demo",
  });

  const sourceItems =
    projectId === "demo" ? demoInformationContainers : (data?.items ?? []);
  const loading = projectId === "demo" ? false : isLoading;
  const container = sourceItems.find((c) => c.id === containerId);

  if (loading) {
    return <div className="p-6 t-sec">読み込み中...</div>;
  }

  if (!container) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <EmptyState icon={<FileText className="h-6 w-6" />} title="コンテナが見つかりません" />
      </div>
    );
  }

  const available = transitions[container.current_state] ?? [];
  const segments = container.identifier.split("-");
  const status = namingStatus(container);

  return (
    <div className="mx-auto max-w-[1180px] p-5 sm:p-6">
      <Link className="app-btn app-btn-ghost app-btn-sm mb-4" to={`/projects/${projectId}/containers`}>
        <ArrowLeft className="h-3.5 w-3.5" />
        情報コンテナ一覧
      </Link>

      <div className="mb-5 flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: "var(--surface-3)", color: "var(--text-2)" }}>
              <FileText className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="mono truncate text-base font-semibold">{container.identifier}</div>
              <div className="t-sec truncate">{container.title}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="grid gap-4">
          <div className="app-card-pad">
            <div className="mb-4 flex items-center justify-between">
              <div className="t-h2">命名規則の検証</div>
              <NamingBadge status={status} />
            </div>
            <div className="flex flex-wrap gap-2">
              {segments.map((segment, index) => (
                <div key={`${segment}-${index}`} className="overflow-hidden rounded-lg border" style={{ borderColor: status === "pass" ? "var(--border)" : "var(--warning)" }}>
                  <div className="mono px-3 py-1.5 text-center text-sm font-semibold" style={{ background: status === "pass" ? "var(--surface-2)" : "var(--warning-bg)", color: status === "pass" ? "var(--text)" : "var(--warning-fg)" }}>
                    {segment}
                  </div>
                  <div className="border-t px-3 py-1 text-center text-[9.5px]" style={{ borderColor: "var(--border-faint)", color: "var(--text-3)" }}>
                    {namingSegments[index]?.label ?? "-"}
                  </div>
                </div>
              ))}
            </div>
            <div className={`mt-4 flex gap-2 rounded-lg p-3 tone-${status === "pass" ? "success" : status === "warn" ? "warning" : "danger"}`}>
              {status === "pass" ? <Check className="h-4 w-4" /> : <RotateCcw className="h-4 w-4" />}
              <div className="text-[12.5px]">
                {container.naming_valid
                  ? "ISO 19650-2 命名規則に適合しています。"
                  : container.naming_issues}
              </div>
            </div>
          </div>

          <div className="app-card overflow-hidden">
            <div className="flex border-b px-2" style={{ borderColor: "var(--border)" }}>
              {[
                ["overview", "概要・メタデータ"],
                ["files", `ファイル (${files.length})`],
                ["revisions", "改訂履歴"],
                ["history", "状態履歴"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  className="relative px-3 py-3 text-[13px]"
                  onClick={() => setTab(key as typeof tab)}
                  style={{ color: tab === key ? "var(--text)" : "var(--text-2)", fontWeight: tab === key ? 600 : 450 }}
                >
                  {label}
                  {tab === key && <span className="absolute inset-x-2 bottom-[-1px] h-0.5 rounded bg-[var(--primary)]" />}
                </button>
              ))}
            </div>
            <div className="p-4">
              {tab === "overview" && (
                <div className="grid gap-4 sm:grid-cols-3">
                  {[
                    ["種別", container.container_type],
                    ["改訂", container.current_revision],
                    ["ブランチ", container.current_branch ?? "-"],
                    ["作成者", container.created_by.slice(0, 8)],
                    ["状態", container.current_state],
                  ].map(([key, value]) => (
                    <div key={key}>
                      <div className="t-label mb-1">{key}</div>
                      <div className="mono text-[13px] font-medium">{value}</div>
                    </div>
                  ))}
                  <div>
                    <div className="t-label mb-1">情報分類</div>
                    <SecurityPill level={container.security_level} />
                  </div>
                </div>
              )}
              {tab === "files" && (
                <div>
                  {downloadError && (
                    <div className="mb-3 text-sm" role="alert" style={{ color: "var(--danger, #dc2626)" }}>
                      {downloadError}
                    </div>
                  )}
                  {files.length === 0 ? (
                    <div className="py-8 text-center t-sec">
                      ファイルがありません。WIP 状態でアップロードできます。
                    </div>
                  ) : (
                    <div className="divide-y" style={{ borderColor: "var(--border-faint)" }}>
                      {files.map((file) => (
                        <div key={file.id} className="flex items-center gap-3 py-3">
                          <FileText className="h-5 w-5 shrink-0" style={{ color: "var(--text-3)" }} />
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-[13px] font-semibold" style={{ color: "var(--text)" }}>
                              {file.original_filename}
                            </div>
                            <div className="t-tiny mono">
                              {(file.file_size_bytes / 1024).toFixed(1)} KB · {fmtDate(file.created_at, true)}
                            </div>
                          </div>
                          <span className="mono hidden truncate text-[10px] sm:inline" style={{ color: "var(--text-3)" }}>
                            {file.checksum_sha256.slice(0, 12)}…
                          </span>
                          <button
                            className="app-btn app-btn-ghost app-btn-sm"
                            disabled={downloadMutation.isPending}
                            onClick={() => void startDownload(file)}
                            aria-label={`${file.original_filename} をダウンロード`}
                          >
                            <Download className="h-3.5 w-3.5" />
                          </button>
                          {container.current_state === "WIP" && (
                            <button
                              className="app-btn app-btn-ghost app-btn-sm"
                              disabled={deleteFileMutation.isPending}
                              onClick={() => {
                                if (window.confirm(`「${file.original_filename}」を削除しますか？`)) {
                                  deleteFileMutation.mutate(file.id);
                                }
                              }}
                              aria-label={`${file.original_filename} を削除`}
                            >
                              <Trash2 className="h-3.5 w-3.5" style={{ color: "var(--danger, #dc2626)" }} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {tab === "revisions" && (
                <div>
                  {revisions.length === 0 ? (
                    <div className="py-8 text-center t-sec">
                      改訂履歴はありません。ファイルをアップロードすると記録されます。
                    </div>
                  ) : (
                    <div className="divide-y" style={{ borderColor: "var(--border-faint)" }}>
                      {revisions.map((revision, index) => (
                        <div key={revision.id} className="flex items-center gap-3 py-3">
                          <span className="mono w-20 shrink-0 rounded-lg px-2 py-1 text-center text-xs font-semibold"
                            style={{
                              background: index === 0 ? "var(--primary-subtle)" : "var(--surface-2)",
                              color: index === 0 ? "var(--primary-text)" : "var(--text-2)",
                            }}
                          >
                            {revision.version_code}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-[13px] font-semibold" style={{ color: "var(--text)" }}>
                              {revision.file?.original_filename ?? "（ファイルなし）"}
                            </div>
                            <div className="t-tiny">
                              {revision.change_reason ?? "変更理由なし"} ·{" "}
                              {revision.created_at ? fmtDate(revision.created_at, true) : "-"}
                            </div>
                          </div>
                          {index === 0 && (
                            <span className="app-badge app-badge-sq tone-success">現行版</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {tab === "history" && (
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <span className="mt-1 h-3 w-3 rounded-full bg-[var(--primary)]" />
                    <div>
                      <div className="text-sm font-semibold">現在の状態: {container.current_state}</div>
                      <div className="t-tiny">すべての状態遷移は監査ログに記録されます。</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <aside className="grid content-start gap-4">
          <div className="app-card-pad">
            <div className="t-label mb-3">現在の状態</div>
            <StatePill state={container.current_state} jp />
            <div className="mt-5 flex items-center">
              {stateOrder.map((state, index) => {
                const active = state === container.current_state;
                const passed = stateOrder.indexOf(container.current_state) > index;
                return (
                  <div key={state} className="contents">
                    <div className="flex flex-1 flex-col items-center">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{
                          background: active
                            ? `var(--${state.toLowerCase()}-dot)`
                            : passed
                              ? "var(--text-3)"
                              : "var(--surface-3)",
                        }}
                      />
                      <span className="mt-1 text-[9px]" style={{ color: active ? "var(--text)" : "var(--text-3)" }}>{state}</span>
                    </div>
                    {index < stateOrder.length - 1 && <span className="mb-4 h-px w-4 bg-[var(--border-strong)]" />}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="app-card-pad">
            <div className="t-label mb-3">実行可能なアクション</div>
            {available.length === 0 ? (
              <div className="flex gap-2 rounded-lg p-3" style={{ background: "var(--surface-2)" }}>
                <Lock className="h-4 w-4" style={{ color: "var(--text-3)" }} />
                <div className="t-sec">この状態では遷移できません。</div>
              </div>
            ) : (
              <div className="grid gap-2">
                {available.map((action) => (
                  <button
                    key={action.action}
                    className={`app-btn ${action.danger ? "" : "app-btn-primary"}`}
                    disabled={transitionMutation.isPending}
                    onClick={() => transitionMutation.mutate({ action: action.action, targetState: action.to })}
                  >
                    {action.danger ? <RotateCcw className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="app-card-pad">
            <div className="t-label mb-3">セキュリティ統制</div>
            {[
              ["閲覧", true],
              ["ダウンロード", container.security_level !== "restricted"],
              ["外部共有", container.security_level === "public" || container.security_level === "limited"],
              ["保管", container.current_state === "Published"],
            ].map(([label, ok]) => (
              <div key={String(label)} className="mb-2 flex items-center justify-between">
                <span className="t-sec">{label}</span>
                <span className={`app-badge app-badge-sq tone-${ok ? "success" : "danger"}`}>
                  {ok ? <Check className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
                  {ok ? "許可" : "不可"}
                </span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
