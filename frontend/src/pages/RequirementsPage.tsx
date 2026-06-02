import { useState } from "react";
import { CheckCircle, Download, Link as LinkIcon, Plus } from "lucide-react";
import { reqDocs, requirementItems, userById } from "@/lib/designData";
import { Avatar } from "@/components/design/Primitives";

const statusMeta = {
  approved: { tone: "success", label: "承認済" },
  review: { tone: "warning", label: "レビュー中" },
  draft: { tone: "neutral", label: "ドラフト" },
} as const;

export default function RequirementsPage() {
  const [activeId, setActiveId] = useState<string>(reqDocs[0].id);
  const active = reqDocs.find((doc) => doc.id === activeId) ?? reqDocs[0];

  return (
    <div className="mx-auto max-w-[1320px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="t-display">要求文書 (EIR / BEP)</h1>
          <p className="t-sec mt-1">ISO 19650 情報要求・配信計画</p>
        </div>
        <button className="app-btn app-btn-primary">
          <Plus className="h-4 w-4" />
          文書を作成
        </button>
      </div>

      <div className="app-card-pad mb-4">
        <div className="t-label mb-3">情報要求の階層 (ISO 19650)</div>
        <div className="flex gap-2 overflow-x-auto">
          {["OIR", "AIR", "PIR", "EIR", "BEP", "MIDP", "TIDP"].map((type) => {
            const doc = reqDocs.find((item) => item.type === type);
            const selected = doc?.id === activeId;
            return (
              <button
                key={type}
                disabled={!doc}
                className="min-w-[92px] rounded-xl border px-4 py-2 text-center"
                style={{
                  borderColor: selected ? "var(--primary)" : "var(--border)",
                  background: selected ? "var(--primary-subtle)" : doc ? "var(--surface)" : "var(--surface-2)",
                  opacity: doc ? 1 : 0.5,
                }}
                onClick={() => doc && setActiveId(doc.id)}
              >
                <div className="mono text-sm font-bold" style={{ color: selected ? "var(--primary-text)" : "var(--text)" }}>{type}</div>
                <div className="text-[9.5px]" style={{ color: "var(--text-3)" }}>要求文書</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <div className="app-card overflow-hidden">
          <div className="border-b px-4 py-3" style={{ borderColor: "var(--border)" }}>
            <span className="t-h2">文書 ({reqDocs.length})</span>
          </div>
          {reqDocs.map((doc) => {
            const selected = doc.id === active.id;
            const meta = statusMeta[doc.status];
            return (
              <button
                key={doc.id}
                className="block w-full border-b p-4 text-left"
                style={{
                  borderColor: "var(--border-faint)",
                  borderLeft: selected ? "3px solid var(--primary)" : "3px solid transparent",
                  background: selected ? "var(--primary-subtle)" : "transparent",
                }}
                onClick={() => setActiveId(doc.id)}
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="mono rounded-md px-2 py-0.5 text-xs font-bold" style={{ background: "var(--surface-3)" }}>{doc.type}</span>
                  <span className={`app-badge app-badge-sq tone-${meta.tone}`}>{meta.label}</span>
                  <span className="mono t-tiny ml-auto">{doc.revision}</span>
                </div>
                <div className="text-[12.5px] font-medium">{doc.title}</div>
                <div className="mt-2 flex items-center gap-2">
                  <Avatar user={doc.owner} size={20} />
                  <span className="t-tiny">{userById[doc.owner].org}</span>
                  <span className="t-tiny mono ml-auto">{doc.items} 要件</span>
                </div>
              </button>
            );
          })}
        </div>

        <div className="app-card-pad">
          <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="mono rounded-md px-2 py-1 text-xs font-bold" style={{ background: "var(--surface-3)" }}>{active.type}</span>
                <span className="mono text-[12.5px]" style={{ color: "var(--text-2)" }}>{active.revision}</span>
                <span className={`app-badge app-badge-sq tone-${statusMeta[active.status].tone}`}>{statusMeta[active.status].label}</span>
              </div>
              <h2 className="t-h1">{active.title}</h2>
              <p className="t-sec mt-1 max-w-2xl">{active.desc}</p>
            </div>
            <button className="app-btn app-btn-sm">
              <Download className="h-3.5 w-3.5" />
              PDF
            </button>
          </div>

          <div className="mb-5 grid gap-3 sm:grid-cols-4">
            <div className="rounded-xl p-3" style={{ background: "var(--surface-2)" }}>
              <div className="t-label mb-2">責任者</div>
              <div className="flex items-center gap-2">
                <Avatar user={active.owner} size={22} />
                <span className="text-[12.5px] font-medium">{userById[active.owner].name}</span>
              </div>
            </div>
            <div className="rounded-xl p-3" style={{ background: "var(--surface-2)" }}>
              <div className="t-label mb-2">要件数</div>
              <div className="text-sm font-semibold">{active.items} 件</div>
            </div>
            <div className="rounded-xl p-3 sm:col-span-2" style={{ background: "var(--surface-2)" }}>
              <div className="t-label mb-2">関連文書</div>
              <span className="app-badge app-badge-sq tone-info"><LinkIcon className="h-3 w-3" />EIR / BEP / MIDP</span>
            </div>
          </div>

          <div className="mb-3 flex items-center justify-between">
            <div className="t-h2">要求事項明細</div>
            <span className="t-tiny">何を / いつ / どのように / 誰のために</span>
          </div>
          <div className="overflow-hidden rounded-xl border" style={{ borderColor: "var(--border)" }}>
            <div className="overflow-x-auto">
              <table className="app-table min-w-[860px]">
                <thead>
                  <tr>
                    <th>No.</th>
                    <th>何を</th>
                    <th>いつ</th>
                    <th>どのように</th>
                    <th>誰のために</th>
                    <th>状態</th>
                  </tr>
                </thead>
                <tbody>
                  {requirementItems.map((item) => (
                    <tr key={item.no}>
                      <td><span className="mono text-xs font-semibold">{item.no}</span></td>
                      <td className="font-medium">{item.what}</td>
                      <td>{item.when}</td>
                      <td>{item.how}</td>
                      <td>{item.who}</td>
                      <td>
                        <span className={`app-badge app-badge-sq tone-${item.status === "met" ? "success" : item.status === "partial" ? "warning" : "danger"}`}>
                          <CheckCircle className="h-3 w-3" />
                          {item.status === "met" ? "充足" : item.status === "partial" ? "一部充足" : "未充足"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
