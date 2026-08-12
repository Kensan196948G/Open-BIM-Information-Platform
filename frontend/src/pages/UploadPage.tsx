import { useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle,
  FileCheck,
  Plus,
  Upload,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { namingSegments } from "@/lib/designData";
import type { ContainerType, SecurityLevel } from "@/types";

const allowed = {
  Originator: ["ARC", "STR", "MEP", "CIV", "LAN", "FAC"],
  Type: ["DR", "M3", "SP", "RP", "SH", "BC", "CR", "MS"],
  Role: ["A", "S", "M", "E", "C", "L", "F"],
} as const;

function validateSegment(key: string, value: string, projectCode: string) {
  if (!value) return { status: "fail", message: "未入力" };
  if (key === "Project") return value === projectCode ? { status: "pass", message: "一致" } : { status: "fail", message: `${projectCode} と不一致` };
  if (key === "Originator") return /^[A-Z]{3}$/.test(value) ? { status: "pass", message: "発信者" } : { status: "fail", message: "英大文字3桁" };
  if (key === "Volume") return /^[A-Z0-9]{2}$/.test(value) ? { status: "pass", message: "2桁" } : { status: "fail", message: "2桁必須" };
  if (key === "Level") return /^(B[0-9]|[0-9]{2}|XX|ZZ)$/.test(value) ? { status: "pass", message: "レベル" } : { status: "warn", message: "マスタ未登録" };
  if (key === "Type") return allowed.Type.includes(value as never) ? { status: "pass", message: "種別" } : { status: "warn", message: "未定義" };
  if (key === "Role") return allowed.Role.includes(value as never) ? { status: "pass", message: "ロール" } : { status: "fail", message: "未定義" };
  if (key === "Number") return /^[0-9]{4}$/.test(value) ? { status: "pass", message: "4桁" } : { status: "fail", message: "数字4桁" };
  return { status: "pass", message: "" };
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const projectCode = (projectId ?? "TKO").slice(0, 3).toUpperCase();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [segments, setSegments] = useState<Record<string, string>>({
    Project: projectCode,
    Originator: "ARC",
    Volume: "XX",
    Level: "09",
    Type: "DR",
    Role: "A",
    Number: "0001",
  });
  const [title, setTitle] = useState("");
  const [containerType, setContainerType] = useState<ContainerType>("document");
  const [securityLevel, setSecurityLevel] = useState<SecurityLevel>("limited");
  const [file, setFile] = useState<File | null>(null);
  const [done, setDone] = useState(false);
  const [createdContainerId, setCreatedContainerId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const results = useMemo(
    () =>
      namingSegments.map((segment) => ({
        ...segment,
        value: segments[segment.key],
        ...validateSegment(segment.key, segments[segment.key], projectCode),
      })),
    [projectCode, segments],
  );
  const identifier = namingSegments
    .map((segment) => segments[segment.key] || "-")
    .join("-");
  const fails = results.filter((r) => r.status === "fail").length;
  const warns = results.filter((r) => r.status === "warn").length;
  const overall = fails > 0 ? "fail" : warns > 0 ? "warn" : "pass";

  const setSegment = (key: string, value: string) => {
    setSegments((current) => ({ ...current, [key]: value.toUpperCase() }));
  };

  const isDemo = projectId === "demo";

  const handleSubmit = async () => {
    if (isDemo) {
      setDone(true);
      return;
    }
    if (!projectId || overall === "fail" || !title || !file) return;
    setError("");
    setSubmitting(true);
    try {
      const containerRes = await api.post<{ id: string }>(
        `/projects/${projectId}/containers`,
        {
          identifier,
          title,
          container_type: containerType,
          security_level: securityLevel,
        },
      );
      const containerId = containerRes.data.id;
      const form = new FormData();
      form.append("file", file);
      await api.post(
        `/projects/${projectId}/containers/${containerId}/upload`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      setCreatedContainerId(containerId);
      setDone(true);
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "登録に失敗しました。入力内容を確認してください。";
      setError(String(detail));
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="mx-auto max-w-xl p-6 pt-16">
        <div className="app-card-pad py-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full tone-success">
            <CheckCircle className="h-7 w-7" />
          </div>
          <h1 className="t-h1">コンテナを登録しました</h1>
          <p className="t-sec mt-2">
            WIP 状態で作成され、監査ログに記録されました
            {file && "。ファイルのSHA-256も保存されています。"}
          </p>
          <div className="mono my-5 rounded-lg p-3 text-sm font-semibold" style={{ background: "var(--surface-2)" }}>
            {identifier}
          </div>
          {!isDemo && createdContainerId && projectId && (
            <Link
              className="app-btn app-btn-ghost app-btn-sm mr-2"
              to={`/projects/${projectId}/containers/${createdContainerId}`}
            >
              コンテナ詳細へ
            </Link>
          )}
          <button className="app-btn app-btn-primary" onClick={() => setDone(false)}>
            続けて登録
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1180px] p-5 sm:p-6">
      <div className="mb-5">
        <h1 className="t-display">アップロード / コンテナ登録</h1>
        <p className="t-sec mt-1">ISO 19650-2 命名規則をリアルタイム検証</p>
      </div>

      {error && (
        <div className="mb-4 flex gap-2 rounded-lg p-3 tone-danger">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <div className="text-[12.5px]">{error}</div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="grid gap-4">
          <div className="app-card-pad">
            <div className="t-h2 mb-3">ファイル</div>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              aria-label="ファイル選択"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {!file ? (
              <button
                className="w-full rounded-xl border border-dashed p-8 text-center"
                style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl app-card">
                  <Upload className="h-5 w-5" style={{ color: "var(--primary)" }} />
                </div>
                <div className="text-sm font-semibold">ファイルをドロップ、またはクリックして選択</div>
                <div className="t-tiny mt-1">PDF · RVT · IFC · BCF · DWG · XLSX / SHA-256 検証</div>
              </button>
            ) : (
              <div className="flex items-center gap-3 rounded-xl border p-3" style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}>
                <FileCheck className="h-8 w-8" style={{ color: "var(--primary)" }} />
                <div className="flex-1">
                  <div className="text-sm font-semibold">{file.name}</div>
                  <div className="t-tiny mono">{formatBytes(file.size)}</div>
                </div>
                <button className="app-btn app-btn-ghost app-btn-icon app-btn-sm" onClick={() => setFile(null)} aria-label="ファイルを外す">
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>

          <div className="app-card-pad">
            <div className="mb-1 flex items-center justify-between">
              <div className="t-h2">識別子（命名規則ビルダー）</div>
              <span className="t-tiny mono">Project-Originator-Volume-Level-Type-Role-Number</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-7">
              {results.map((result) => {
                const color = result.status === "pass" ? "var(--success)" : result.status === "warn" ? "var(--warning)" : "var(--danger)";
                return (
                  <label key={result.key}>
                    <div className="mb-1 truncate text-center text-[10px] font-semibold" style={{ color: "var(--text-3)" }}>{result.label}</div>
                    <input
                      className="mono w-full rounded-lg border bg-transparent px-2 py-1.5 text-center font-semibold"
                      value={result.value}
                      disabled={result.key === "Project"}
                      maxLength={result.key === "Number" ? 4 : 3}
                      onChange={(e) => setSegment(result.key, e.target.value)}
                      style={{ borderColor: color, color: "var(--text)" }}
                      aria-label={`${result.label}セグメント`}
                    />
                    <div className="mt-1 flex items-center justify-center gap-1 text-[9px]" style={{ color }}>
                      {result.status === "pass" ? <Check className="h-2.5 w-2.5" /> : result.status === "warn" ? <AlertTriangle className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />}
                      {result.message}
                    </div>
                  </label>
                );
              })}
            </div>
            <div className="mt-4 flex flex-col justify-between gap-3 rounded-xl p-4 sm:flex-row sm:items-center" style={{ background: "var(--surface-2)" }}>
              <div>
                <div className="t-label mb-1">生成される識別子</div>
                <div className="mono text-sm font-semibold">{identifier}</div>
              </div>
              <span className={`app-badge app-badge-sq tone-${overall === "pass" ? "success" : overall === "warn" ? "warning" : "danger"} h-7`}>
                {overall === "pass" ? <CheckCircle className="h-3.5 w-3.5" /> : overall === "warn" ? <AlertTriangle className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                {overall === "pass" ? "適合" : overall === "warn" ? "警告" : "不適合"}
              </span>
            </div>
          </div>

          <div className="app-card-pad">
            <div className="t-h2 mb-3">メタデータ</div>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block sm:col-span-1">
                <div className="mb-1 text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>タイトル</div>
                <input
                  className="w-full rounded-lg border bg-transparent px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)", color: "var(--text)" }}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="例: 9F 基準階平面詳細図"
                />
              </label>
              <label className="block">
                <div className="mb-1 text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>種別</div>
                <select
                  className="w-full rounded-lg border bg-transparent px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)", color: "var(--text)" }}
                  value={containerType}
                  onChange={(e) => setContainerType(e.target.value as ContainerType)}
                >
                  <option value="document">文書</option>
                  <option value="drawing">図面</option>
                  <option value="model">モデル</option>
                  <option value="ifc">IFC</option>
                  <option value="bcf">BCF</option>
                  <option value="other">その他</option>
                </select>
              </label>
              <label className="block">
                <div className="mb-1 text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>情報分類</div>
                <select
                  className="w-full rounded-lg border bg-transparent px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)", color: "var(--text)" }}
                  value={securityLevel}
                  onChange={(e) => setSecurityLevel(e.target.value as SecurityLevel)}
                >
                  <option value="public">公開</option>
                  <option value="limited">限定</option>
                  <option value="confidential">機密</option>
                  <option value="restricted">制限付き</option>
                </select>
              </label>
            </div>
          </div>
        </div>

        <aside className="grid content-start gap-4">
          <div className="app-card-pad">
            <div className="t-label mb-3">検証サマリー</div>
            <div className={`mb-4 flex gap-3 rounded-xl p-4 tone-${overall === "pass" ? "success" : overall === "warn" ? "warning" : "danger"}`}>
              {overall === "pass" ? <CheckCircle className="h-7 w-7" /> : overall === "warn" ? <AlertTriangle className="h-7 w-7" /> : <AlertCircle className="h-7 w-7" />}
              <div>
                <div className="text-base font-bold">{overall === "pass" ? "適合" : overall === "warn" ? "警告" : "不適合"}</div>
                <div className="text-xs">
                  {overall === "pass" ? "提出可能です。" : overall === "warn" ? `${warns} 件の警告があります。` : `${fails} 件の不適合があります。`}
                </div>
              </div>
            </div>
            <div className="space-y-2">
              {results.map((result) => (
                <div key={result.key} className="flex items-center gap-2 text-xs">
                  <span className="w-20" style={{ color: "var(--text-2)" }}>{result.label}</span>
                  <span className="mono font-semibold">{result.value}</span>
                  <span className="ml-auto" style={{ color: "var(--text-3)" }}>{result.message}</span>
                </div>
              ))}
            </div>
          </div>

          <button
            className="app-btn app-btn-primary h-11"
            disabled={overall === "fail" || !file || !title || submitting}
            onClick={handleSubmit}
            style={overall === "fail" || !file || !title || submitting ? { opacity: 0.5, cursor: "not-allowed" } : undefined}
          >
            <Plus className="h-4 w-4" />
            {submitting ? "登録中..." : "WIP として登録"}
          </button>
        </aside>
      </div>
    </div>
  );
}
