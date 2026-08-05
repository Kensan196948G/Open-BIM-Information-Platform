import { useState } from "react";
import { useParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle,
  Plus,
  RefreshCw,
  Save,
  Settings2,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/design/Primitives";
import type { NamingRuleResponse, SegmentDefinition } from "@/types";

const DEFAULT_SEGMENTS: SegmentDefinition[] = [
  {
    key: "project",
    label: "プロジェクト",
    required: true,
    max_length: 20,
    min_length: 2,
    allowed_values: [],
    pattern: "^[A-Z0-9]+$",
    description: "プロジェクトコード",
  },
  {
    key: "originator",
    label: "発信者",
    required: true,
    max_length: 10,
    min_length: 2,
    allowed_values: [],
    pattern: "^[A-Z0-9]+$",
    description: "組織コード",
  },
  {
    key: "volume",
    label: "区分/系統",
    required: false,
    max_length: 6,
    min_length: null,
    allowed_values: [],
    pattern: "^[A-Z0-9]+$",
    description: "ボリューム (例: ZZ)",
  },
  {
    key: "level",
    label: "レベル",
    required: false,
    max_length: 6,
    min_length: null,
    allowed_values: [],
    pattern: "^[A-Z0-9]+$",
    description: "フロア/レベルコード",
  },
  {
    key: "type",
    label: "種別",
    required: true,
    max_length: 4,
    min_length: 2,
    allowed_values: ["DR", "M3", "MO", "MS", "WD", "RP", "SK", "SP", "XX"],
    pattern: null,
    description: "情報種別コード",
  },
  {
    key: "role",
    label: "ロール",
    required: true,
    max_length: 4,
    min_length: 1,
    allowed_values: [],
    pattern: "^[A-Z]{1,4}$",
    description: "担当分野コード",
  },
  {
    key: "number",
    label: "連番",
    required: true,
    max_length: 6,
    min_length: 4,
    allowed_values: [],
    pattern: "^\\d+$",
    description: "4桁以上の数字",
  },
];

function buildPreview(segments: SegmentDefinition[], separator: string) {
  return segments
    .filter((s) => s.required || s.description)
    .map((s) => s.allowed_values[0] ?? s.key.toUpperCase().slice(0, 4))
    .join(separator);
}

function SegmentRow({
  seg,
  idx,
  onChange,
  onRemove,
}: {
  seg: SegmentDefinition;
  idx: number;
  onChange: (i: number, updated: SegmentDefinition) => void;
  onRemove: (i: number) => void;
}) {
  const update = (field: keyof SegmentDefinition, value: unknown) =>
    onChange(idx, { ...seg, [field]: value });

  return (
    <div
      className="rounded-xl border p-4"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white"
            style={{ background: "var(--primary)" }}
          >
            {idx + 1}
          </span>
          <span
            className="text-sm font-semibold"
            style={{ color: "var(--text)" }}
          >
            {seg.label || seg.key}
          </span>
          {!seg.required && (
            <span
              className="app-badge"
              style={{ background: "var(--surface-3)", color: "var(--text-3)" }}
            >
              任意
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => onRemove(idx)}
          className="flex h-7 w-7 items-center justify-center rounded-lg"
          style={{ color: "var(--danger)" }}
          title="セグメントを削除"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="t-label mb-1 block">キー</label>
          <input
            className="app-input w-full font-mono"
            value={seg.key}
            onChange={(e) => update("key", e.target.value)}
            placeholder="project"
          />
        </div>
        <div>
          <label className="t-label mb-1 block">ラベル</label>
          <input
            className="app-input w-full"
            value={seg.label}
            onChange={(e) => update("label", e.target.value)}
            placeholder="プロジェクト"
          />
        </div>
        <div>
          <label className="t-label mb-1 block">正規表現パターン</label>
          <input
            className="app-input w-full font-mono"
            value={seg.pattern ?? ""}
            onChange={(e) => update("pattern", e.target.value || null)}
            placeholder="^[A-Z0-9]+$"
          />
        </div>
        <div>
          <label className="t-label mb-1 block">許容値 (カンマ区切り)</label>
          <input
            className="app-input w-full font-mono"
            value={seg.allowed_values.join(",")}
            onChange={(e) =>
              update(
                "allowed_values",
                e.target.value
                  ? e.target.value.split(",").map((s) => s.trim())
                  : [],
              )
            }
            placeholder="DR,M3,SP"
          />
        </div>
        <div className="flex items-center gap-4">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={seg.required}
              onChange={(e) => update("required", e.target.checked)}
            />
            <span className="t-sec text-sm">必須</span>
          </label>
          <div className="flex items-center gap-2">
            <span className="t-label">最小</span>
            <input
              type="number"
              className="app-input w-16 font-mono"
              value={seg.min_length ?? ""}
              onChange={(e) =>
                update(
                  "min_length",
                  e.target.value ? Number(e.target.value) : null,
                )
              }
            />
            <span className="t-label">最大</span>
            <input
              type="number"
              className="app-input w-16 font-mono"
              value={seg.max_length ?? ""}
              onChange={(e) =>
                update(
                  "max_length",
                  e.target.value ? Number(e.target.value) : null,
                )
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NamingRulesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [editMode, setEditMode] = useState(false);
  const [separator, setSeparator] = useState("-");
  const [segments, setSegments] =
    useState<SegmentDefinition[]>(DEFAULT_SEGMENTS);

  const { data: rule, isLoading } = useQuery<NamingRuleResponse>({
    queryKey: ["naming-rules", projectId],
    queryFn: () =>
      api
        .get<NamingRuleResponse>(`/projects/${projectId}/naming-rules`)
        .then((r) => r.data),
    enabled: !!projectId && projectId !== "demo",
  });

  const upsertMutation = useMutation({
    mutationFn: (body: { separator: string; segments: SegmentDefinition[] }) =>
      api.put(`/projects/${projectId}/naming-rules`, body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["naming-rules", projectId] });
      setEditMode(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/projects/${projectId}/naming-rules`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["naming-rules", projectId] });
      setEditMode(false);
    },
  });

  const startEdit = () => {
    const src = rule ?? { separator: "-", segments: DEFAULT_SEGMENTS };
    setSeparator(src.separator);
    setSegments(src.segments as SegmentDefinition[]);
    setEditMode(true);
  };

  const addSegment = () =>
    setSegments((prev) => [
      ...prev,
      {
        key: `seg${prev.length + 1}`,
        label: "新規セグメント",
        required: false,
        max_length: null,
        min_length: null,
        allowed_values: [],
        pattern: null,
        description: "",
      },
    ]);

  const updateSegment = (i: number, updated: SegmentDefinition) =>
    setSegments((prev) => prev.map((s, idx) => (idx === i ? updated : s)));

  const removeSegment = (i: number) =>
    setSegments((prev) => prev.filter((_, idx) => idx !== i));

  const preview = buildPreview(
    editMode
      ? segments
      : ((rule?.segments as SegmentDefinition[]) ?? DEFAULT_SEGMENTS),
    editMode ? separator : (rule?.separator ?? "-"),
  );

  if (isLoading) {
    return (
      <div className="mx-auto max-w-[1000px] p-6">
        <div className="t-sec py-12 text-center">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1000px] p-5 sm:p-6">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <Settings2
              className="h-5 w-5"
              style={{ color: "var(--primary)" }}
            />
            <h1 className="t-display">命名規則設定</h1>
          </div>
          <p className="t-sec">
            ISO 19650-2 Annex A 準拠のセグメント構成を管理します。
          </p>
        </div>
        <div className="flex gap-2">
          {!editMode ? (
            <>
              <button className="app-btn" onClick={startEdit}>
                <Settings2 className="h-4 w-4" />
                編集
              </button>
              {rule && !rule.is_default && (
                <button
                  className="app-btn"
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending}
                  style={{ color: "var(--danger)" }}
                >
                  <RefreshCw className="h-4 w-4" />
                  デフォルトへリセット
                </button>
              )}
            </>
          ) : (
            <>
              <button className="app-btn" onClick={() => setEditMode(false)}>
                キャンセル
              </button>
              <button
                className="app-btn app-btn-primary"
                onClick={() => upsertMutation.mutate({ separator, segments })}
                disabled={upsertMutation.isPending}
              >
                <Save className="h-4 w-4" />
                {upsertMutation.isPending ? "保存中..." : "保存"}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Status badge */}
      {rule && (
        <div
          className="mb-5 flex items-center gap-2 rounded-xl border px-4 py-3"
          style={{
            borderColor: rule.is_default
              ? "var(--border)"
              : "var(--primary-border)",
            background: rule.is_default
              ? "var(--surface-2)"
              : "var(--primary-subtle)",
          }}
        >
          {rule.is_default ? (
            <AlertCircle
              className="h-4 w-4 shrink-0"
              style={{ color: "var(--text-3)" }}
            />
          ) : (
            <CheckCircle
              className="h-4 w-4 shrink-0"
              style={{ color: "var(--success)" }}
            />
          )}
          <span
            className="text-sm"
            style={{
              color: rule.is_default ? "var(--text-2)" : "var(--primary-text)",
            }}
          >
            {rule.is_default
              ? "ISO 19650 デフォルトルールを使用中"
              : `カスタムルール設定済み (${rule.segments.length} セグメント)`}
          </span>
        </div>
      )}

      {/* Identifier preview */}
      <div className="app-card-pad mb-5">
        <div className="t-label mb-2">識別子プレビュー</div>
        <div
          className="mono rounded-lg border px-3 py-2 text-sm"
          style={{
            background: "var(--surface-2)",
            borderColor: "var(--border)",
            color: "var(--text)",
          }}
        >
          {preview}
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {(editMode
            ? segments
            : ((rule?.segments as SegmentDefinition[]) ?? DEFAULT_SEGMENTS)
          ).map((s, i, arr) => (
            <span key={s.key}>
              <span
                className="app-badge"
                style={{
                  background: s.required
                    ? "var(--primary-subtle)"
                    : "var(--surface-3)",
                  color: s.required ? "var(--primary-text)" : "var(--text-3)",
                }}
              >
                {s.label}
              </span>
              {i < arr.length - 1 && (
                <span
                  className="mx-0.5 text-xs"
                  style={{ color: "var(--text-3)" }}
                >
                  {editMode ? separator : (rule?.separator ?? "-")}
                </span>
              )}
            </span>
          ))}
        </div>
      </div>

      {/* Separator setting (edit mode) */}
      {editMode && (
        <div className="app-card-pad mb-5">
          <div className="t-label mb-2">区切り文字</div>
          <div className="flex items-center gap-3">
            {["-", "_", ".", "/"].map((sep) => (
              <button
                key={sep}
                type="button"
                className="mono flex h-9 w-9 items-center justify-center rounded-lg border text-sm font-bold"
                style={{
                  borderColor:
                    separator === sep ? "var(--primary)" : "var(--border)",
                  background:
                    separator === sep
                      ? "var(--primary-subtle)"
                      : "var(--surface)",
                  color:
                    separator === sep ? "var(--primary-text)" : "var(--text)",
                }}
                onClick={() => setSeparator(sep)}
              >
                {sep}
              </button>
            ))}
            <span className="t-sec text-xs">
              現在: &ldquo;{editMode ? separator : (rule?.separator ?? "-")}
              &rdquo;
            </span>
          </div>
        </div>
      )}

      {/* Segments */}
      <div className="mb-4 flex items-center justify-between">
        <div className="t-h2">
          セグメント定義 (
          {(editMode ? segments : (rule?.segments ?? DEFAULT_SEGMENTS)).length}{" "}
          件)
        </div>
        {editMode && (
          <button className="app-btn" onClick={addSegment}>
            <Plus className="h-4 w-4" />
            追加
          </button>
        )}
      </div>

      {(editMode
        ? segments
        : ((rule?.segments as SegmentDefinition[]) ?? DEFAULT_SEGMENTS)
      ).length === 0 ? (
        <EmptyState
          icon={<Settings2 className="h-6 w-6" />}
          title="セグメントが未設定です"
          sub="「追加」ボタンでセグメントを作成してください"
        />
      ) : editMode ? (
        <div className="space-y-3">
          {segments.map((seg, idx) => (
            <SegmentRow
              key={idx}
              seg={seg}
              idx={idx}
              onChange={updateSegment}
              onRemove={removeSegment}
            />
          ))}
        </div>
      ) : (
        <div
          className="overflow-hidden rounded-xl border"
          style={{ borderColor: "var(--border)" }}
        >
          <table className="w-full text-sm">
            <thead style={{ background: "var(--surface-2)" }}>
              <tr>
                {[
                  "#",
                  "キー",
                  "ラベル",
                  "必須",
                  "パターン / 許容値",
                  "長さ",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2.5 text-left"
                    style={{
                      color: "var(--text-3)",
                      fontSize: "11px",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(
                (rule?.segments as SegmentDefinition[]) ?? DEFAULT_SEGMENTS
              ).map((s, i) => (
                <tr
                  key={s.key}
                  className="border-t"
                  style={{ borderColor: "var(--border-faint)" }}
                >
                  <td
                    className="px-4 py-2.5"
                    style={{ color: "var(--text-3)" }}
                  >
                    {i + 1}
                  </td>
                  <td
                    className="px-4 py-2.5 font-mono text-xs"
                    style={{ color: "var(--text)" }}
                  >
                    {s.key}
                  </td>
                  <td
                    className="px-4 py-2.5 font-medium"
                    style={{ color: "var(--text)" }}
                  >
                    {s.label}
                  </td>
                  <td className="px-4 py-2.5">
                    {s.required ? (
                      <CheckCircle
                        className="h-3.5 w-3.5"
                        style={{ color: "var(--success)" }}
                      />
                    ) : (
                      <span className="t-sec text-xs">任意</span>
                    )}
                  </td>
                  <td
                    className="px-4 py-2.5 font-mono text-xs"
                    style={{ color: "var(--text-2)" }}
                  >
                    {s.pattern ??
                      (s.allowed_values.length > 0
                        ? s.allowed_values.join(", ")
                        : "—")}
                  </td>
                  <td
                    className="px-4 py-2.5 font-mono text-xs"
                    style={{ color: "var(--text-3)" }}
                  >
                    {s.min_length != null && s.max_length != null
                      ? `${s.min_length}–${s.max_length}`
                      : s.max_length != null
                        ? `≤${s.max_length}`
                        : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Mutation error */}
      {upsertMutation.isError && (
        <div
          className="mt-4 rounded-xl border px-4 py-3 text-sm"
          style={{
            borderColor: "var(--danger)",
            background: "var(--danger-bg)",
            color: "var(--danger-fg)",
          }}
        >
          保存に失敗しました: {String(upsertMutation.error)}
        </div>
      )}
    </div>
  );
}
