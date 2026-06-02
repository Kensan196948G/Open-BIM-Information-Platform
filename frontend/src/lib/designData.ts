import type {
  ContainerState,
  ContainerType,
  InformationContainer,
  Project,
  SecurityLevel,
} from "@/types";

export interface DesignUser {
  id: string;
  name: string;
  initials: string;
  role: string;
  org: string;
  color: string;
}

export interface DemoContainer {
  id: string;
  projectId: string;
  identifier: string;
  title: string;
  type: ContainerType;
  state: ContainerState;
  revision: string;
  security: SecurityLevel;
  naming: "pass" | "warn" | "fail";
  owner: string;
  org: string;
  updated: string;
  size: string;
  ext: string;
  discipline: string;
  issue?: string;
}

export const designUsers: DesignUser[] = [
  { id: "u1", name: "佐藤 健一", initials: "佐", role: "BIMマネージャー", org: "大成設計", color: "#2c63e6" },
  { id: "u2", name: "鈴木 由美", initials: "鈴", role: "情報管理者", org: "大成設計", color: "#14a85f" },
  { id: "u3", name: "高橋 誠", initials: "高", role: "意匠設計", org: "大成設計", color: "#d99a26" },
  { id: "u4", name: "田中 浩二", initials: "田", role: "構造設計", org: "東和構造", color: "#9b59b6" },
  { id: "u5", name: "伊藤 さくら", initials: "伊", role: "設備設計", org: "日本設備工業", color: "#e0483b" },
  { id: "u6", name: "山本 大輔", initials: "山", role: "承認者 / 主任", org: "発注者PMO", color: "#0d9488" },
];

export const userById = Object.fromEntries(designUsers.map((u) => [u.id, u]));

export const demoProject: Project = {
  id: "demo",
  organization_id: "demo-org",
  name: "東京中央ターミナル再開発",
  code: "TKO",
  description: "地上48階・地下4階の複合ターミナル。鉄道・商業・オフィス・ホテルを統合。",
  status: "active",
  start_date: "2025-04-01",
  end_date: "2028-03-31",
  applied_standard: "ISO 19650-2:2018",
};

export const demoContainers: DemoContainer[] = [
  { id: "c1", projectId: "demo", identifier: "TKO-ARC-XX-07-DR-A-0421", title: "基準階平面詳細図 (7F オフィス)", type: "drawing", state: "Published", revision: "C02", security: "limited", naming: "pass", owner: "u3", org: "大成設計", updated: "2026-05-28T11:24:00", size: "4.2 MB", ext: "PDF", discipline: "意匠" },
  { id: "c2", projectId: "demo", identifier: "TKO-STR-XX-ZZ-M3-S-0008", title: "全体構造解析モデル v8", type: "model", state: "Shared", revision: "P04.02", security: "confidential", naming: "pass", owner: "u4", org: "東和構造", updated: "2026-05-29T16:48:00", size: "218 MB", ext: "RVT", discipline: "構造" },
  { id: "c3", projectId: "demo", identifier: "TKO-MEP-B2-B2-DR-M-0117", title: "地下2階 機械設備配管図", type: "drawing", state: "WIP", revision: "P02.05", security: "limited", naming: "warn", owner: "u5", org: "日本設備工業", updated: "2026-05-30T09:12:00", size: "7.8 MB", ext: "PDF", discipline: "設備", issue: "レベルコードがマスタ未登録 (B2)" },
  { id: "c4", projectId: "demo", identifier: "tko-arc-xx-12-dr-a-09", title: "12F 平面図 ドラフト", type: "drawing", state: "WIP", revision: "P01.01", security: "limited", naming: "fail", owner: "u3", org: "大成設計", updated: "2026-05-30T18:03:00", size: "3.1 MB", ext: "DWG", discipline: "意匠", issue: "小文字使用・連番桁数不足 (4桁必須)" },
  { id: "c5", projectId: "demo", identifier: "TKO-ARC-XX-ZZ-IFC-A-0003", title: "意匠統合 IFC モデル (連携用)", type: "ifc", state: "Published", revision: "C01", security: "limited", naming: "pass", owner: "u1", org: "大成設計", updated: "2026-05-25T14:30:00", size: "512 MB", ext: "IFC", discipline: "意匠" },
  { id: "c6", projectId: "demo", identifier: "TKO-STR-XX-03-BCF-S-0044", title: "3F 梁貫通スリーブ干渉 指摘", type: "bcf", state: "Shared", revision: "P01.03", security: "limited", naming: "pass", owner: "u4", org: "東和構造", updated: "2026-05-29T10:05:00", size: "82 KB", ext: "BCF", discipline: "構造" },
  { id: "c7", projectId: "demo", identifier: "TKO-ARC-XX-XX-SP-A-0012", title: "内装仕上げ仕様書", type: "document", state: "Published", revision: "C03", security: "public", naming: "pass", owner: "u2", org: "大成設計", updated: "2026-05-20T13:18:00", size: "1.1 MB", ext: "PDF", discipline: "意匠" },
  { id: "c8", projectId: "demo", identifier: "TKO-MEP-XX-ZZ-M3-M-0021", title: "機械設備 統合モデル", type: "model", state: "WIP", revision: "P03.01", security: "confidential", naming: "pass", owner: "u5", org: "日本設備工業", updated: "2026-05-30T15:42:00", size: "176 MB", ext: "RVT", discipline: "設備" },
];

export const demoInformationContainers: InformationContainer[] =
  demoContainers.map((container) => ({
    id: container.id,
    project_id: container.projectId,
    identifier: container.identifier,
    title: container.title,
    container_type: container.type,
    current_state: container.state,
    current_revision: container.revision,
    current_branch: null,
    security_level: container.security,
    naming_valid: container.naming === "pass",
    naming_issues: container.issue ?? null,
    created_by: container.owner,
  }));

export const approvals = [
  { id: "a1", containerId: "c2", identifier: "TKO-STR-XX-ZZ-M3-S-0008", title: "全体構造解析モデル v8", stage: "review / authorise", from: "WIP", to: "Shared", requestedBy: "u4", due: "2026-06-02", priority: "high", security: "confidential" },
  { id: "a2", containerId: "c6", identifier: "TKO-STR-XX-03-BCF-S-0044", title: "3F 梁貫通スリーブ干渉 指摘", stage: "check / review / approve", from: "Shared", to: "Published", requestedBy: "u4", due: "2026-05-31", priority: "high", security: "limited" },
  { id: "a3", containerId: "c1", identifier: "TKO-ARC-XX-07-DR-A-0421", title: "基準階平面詳細図 (7F オフィス)", stage: "approve", from: "Shared", to: "Published", requestedBy: "u3", due: "2026-06-01", priority: "medium", security: "limited" },
] as const;

export const reqDocs = [
  { id: "d1", type: "EIR", title: "発注者情報要求事項 (EIR) — 東京中央ターミナル", revision: "C02", status: "approved", owner: "u6", items: 24, desc: "設計・施工各段階で要求する情報、フォーマット、提出時点を定義。" },
  { id: "d2", type: "BEP", title: "BIM実行計画書 (BEP) — 設計段階", revision: "P03.01", status: "review", owner: "u1", items: 38, desc: "情報生成の方針、責任分担、ソフト構成、座標系、品質保証を規定。" },
  { id: "d3", type: "MIDP", title: "マスター情報配信計画", revision: "P02.00", status: "review", owner: "u2", items: 52, desc: "全TIDPを統合した成果物提出スケジュール。" },
] as const;

export const requirementItems = [
  { no: "EIR-01", what: "各階平面図 (LOD300)", when: "Stage 4 完了時", how: "PDF + IFC2x3 / 命名規則準拠", who: "発注者・施工者", status: "met" },
  { no: "EIR-02", what: "統合構造解析モデル", when: "実施設計中間", how: "RVT + IFC4 / 座標系JGD2011", who: "構造監理", status: "met" },
  { no: "EIR-03", what: "設備統合モデル (機械/電気)", when: "実施設計完了", how: "RVT + COBie", who: "FM・施工者", status: "partial" },
  { no: "EIR-04", what: "竣工モデル (As-built)", when: "引渡時", how: "IFC4 + COBie / FM連携", who: "資産管理者", status: "open" },
] as const;

export const namingSegments = [
  { key: "Project", label: "プロジェクト", ex: "TKO" },
  { key: "Originator", label: "発信者", ex: "ARC" },
  { key: "Volume", label: "区分/系統", ex: "XX" },
  { key: "Level", label: "レベル", ex: "07" },
  { key: "Type", label: "種別", ex: "DR" },
  { key: "Role", label: "ロール", ex: "A" },
  { key: "Number", label: "連番", ex: "0001" },
] as const;

export const auditSamples = [
  { id: "e1", at: "2026-05-30T18:03:12", actor: "u3", event: "container.naming.fail", target: "TKO-ARC...-09", type: "コンテナ", op: "命名規則検証", result: "warning", ip: "10.4.21.88", reason: "連番桁数不足・小文字使用" },
  { id: "e2", at: "2026-05-30T16:48:40", actor: "u4", event: "container.transition", target: "TKO-STR-XX-ZZ-M3-S-0008", type: "コンテナ", op: "WIP→Shared 提出", result: "success", ip: "10.4.21.40", reason: "—" },
  { id: "e3", at: "2026-05-30T14:20:55", actor: "u6", event: "approval.act", target: "TKO-ARC-XX-01-DR-A-0205", type: "承認", op: "レビュー承認", result: "success", ip: "10.4.20.7", reason: "—" },
  { id: "e4", at: "2026-05-30T11:58:31", actor: "u2", event: "security.share", target: "TKO-ARC-XX-ZZ-IFC-A-0003", type: "外部共有", op: "外部共有申請", result: "denied", ip: "10.4.21.51", reason: "機密区分の承認者不足" },
] as const;

export const stateOrder: ContainerState[] = ["WIP", "Shared", "Published", "Archived"];
