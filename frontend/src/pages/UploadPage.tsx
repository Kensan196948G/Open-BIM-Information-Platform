import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
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
import { namingSegments } from "@/lib/designData";

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

export default function UploadPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const projectCode = (projectId ?? "TKO").slice(0, 3).toUpperCase();
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
  const [file, setFile] = useState<{ name: string; size: string } | null>(null);
  const [done, setDone] = useState(false);

  const results = useMemo(
    () =>
      namingSegments.map((segment) => ({
        ...segment,
        value: segments[segment.key],
        ...validateSegment(segment.key, segments[segment.key], projectCode),
      })),
    [projectCode, segments],
  );
  const identifier = namingSegments.map((segment) => segments[segment.key] || "-").join("-");
  const fails = results.filter((r) => r.status === "fail").length;
  const warns = results.filter((r) => r.status === "warn").length;
  const overall = fails > 0 ? "fail" : warns > 0 ? "warn" : "pass";

  const setSegment = (key: string, value: string) => {
    setSegments((current) => ({ ...current, [key]: value.toUpperCase() }));
  };

  if (done) {
    return (
      <div className="mx-auto max-w-xl p-6 pt-16">
        <div className="app-card-pad py-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full tone-success">
            <CheckCircle className="h-7 w-7" />
          </div>
          <h1 className="t-h1">コンテナを登録しました</h1>
          <p className="t-sec mt-2">WIP 状態で作成され、監査ログに記録されました。</p>
          <div className="mono my-5 rounded-lg p-3 text-sm font-semibold" style={{ background: "var(--surface-2)" }}>
            {identifier}
          </div>
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

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="grid gap-4">
          <div className="app-card-pad">
            <div className="t-h2 mb-3">ファイル</div>
            {!file ? (
              <button
                className="w-full rounded-xl border border-dashed p-8 text-center"
                style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}
                onClick={() => setFile({ name: "A-基準階平面.pdf", size: "4.2 MB" })}
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
                  <div className="t-tiny mono">{file.size} · MIME 許可 · SHA-256 検証済み</div>
                </div>
                <span className="app-badge app-badge-sq tone-success"><Check className="h-3 w-3" />完了</span>
                <button className="app-btn app-btn-ghost app-btn-icon app-btn-sm" onClick={() => setFile(null)}>
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
                      className="app-field mono text-center font-semibold"
                      value={result.value}
                      disabled={result.key === "Project"}
                      maxLength={result.key === "Number" ? 4 : 3}
                      onChange={(e) => setSegment(result.key, e.target.value)}
                      style={{ borderColor: color }}
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
            <label className="block">
              <div className="mb-1 text-[12.5px] font-medium" style={{ color: "var(--text-2)" }}>タイトル</div>
              <input className="app-field" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例: 9F 基準階平面詳細図" />
            </label>
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
            disabled={overall === "fail" || !file || !title}
            onClick={() => setDone(true)}
            style={overall === "fail" || !file || !title ? { opacity: 0.5, cursor: "not-allowed" } : undefined}
          >
            <Plus className="h-4 w-4" />
            WIP として登録
          </button>
        </aside>
      </div>
    </div>
  );
}
