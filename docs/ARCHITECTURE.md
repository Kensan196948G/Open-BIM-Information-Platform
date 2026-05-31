# 🏛️ アーキテクチャ設計書 — Open BIM 情報基盤

> ISO 19650 準拠 BIM 情報管理プラットフォームの設計思想と構造

---

## 📌 設計原則

1. **二層準拠モデル**: ISO 19650 完全準拠を「システム実装」と「組織運用」に分離。システムは統制を支援し、契約・教育・例外承認は運用で担保
2. **単一の真実**: メタデータDB（PostgreSQL）が情報コンテナ状態の唯一の真実。ファイル実体（MinIO）とメタデータを分離
3. **監査の不可変性**: 監査ログは Append-Only。DBトリガーで UPDATE/DELETE を物理的に拒否
4. **状態機械中心**: CDE 4状態（WIP/Shared/Published/Archived）を全機能の基軸とする

---

## 🗺️ システム全体図

```
                    ┌─────────────────────────────────────┐
                    │         利用者ブラウザ                 │
                    └──────────────────┬──────────────────┘
                                       │ HTTPS
                    ┌──────────────────▼──────────────────┐
                    │   Reverse Proxy (nginx / TLS終端)     │
                    └────────┬───────────────────┬─────────┘
                             │                   │
                  ┌──────────▼─────────┐  ┌──────▼──────────┐
                  │  Frontend (React)  │  │ Backend (FastAPI)│
                  │  ・SPA / Vite      │  │ ・REST API       │
                  │  ・React Query     │  │ ・JWT 認証       │
                  │  ・Zustand         │  │ ・RBAC 認可      │
                  └────────────────────┘  └───┬───┬───┬──────┘
                                              │   │   │
                       ┌──────────────────────┘   │   └───────────────┐
                       │                           │                   │
              ┌────────▼────────┐    ┌─────────────▼──────┐  ┌─────────▼────────┐
              │  PostgreSQL 15  │    │     Redis 7        │  │   MinIO (S3)     │
              │  ・メタデータ    │    │  ・キャッシュ       │  │  ・ファイル実体   │
              │  ・監査ログ      │    │  ・セッション       │  │  ・SHA-256検証   │
              │  ・immutable監査 │    └────────────────────┘  └──────────────────┘
              └─────────────────┘
```

---

## 🧱 レイヤー構造（バックエンド）

```
backend/app/
├── api/v1/         # プレゼンテーション層: REST エンドポイント
│   ├── auth.py         # 認証 (JWT)
│   ├── projects.py     # プロジェクト管理 (テナント分離)
│   ├── containers.py   # CDE 状態遷移
│   ├── naming.py       # 命名規則検証
│   ├── uploads.py      # ファイルアップロード
│   ├── workflows.py    # 承認ワークフロー
│   └── audit_logs.py   # 監査ログ参照
├── services/       # ビジネスロジック層
│   ├── naming_validator.py  # ISO 19650 命名検証エンジン
│   └── storage.py           # MinIO 抽象化
├── models/         # ドメイン層: SQLAlchemy ORM
├── schemas/        # DTO 層: Pydantic スキーマ
├── core/           # 横断的関心事: 設定・認証・依存性注入
└── db/             # インフラ層: DB セッション
```

---

## 🔁 CDE 状態機械

```
        ┌───────────────────────────────────────────────┐
        │                                               │
   ┌────▼────┐  submit   ┌──────────┐  approve  ┌───────────┐  archive  ┌──────────┐
   │   WIP   │──────────▶│  Shared  │──────────▶│ Published │──────────▶│ Archived │
   └─────────┘           └────┬─────┘           └───────────┘           └──────────┘
        ▲                     │                                              ▲
        │      return         │                          archive            │
        └─────────────────────┘──────────────────────────────────────────────┘
```

| 状態      | 編集      | 公開範囲   | 次状態                              |
| --------- | --------- | ---------- | ----------------------------------- |
| WIP       | ✅ 作成者 | 非公開     | Shared                              |
| Shared    | ❌        | レビュアー | Published / WIP（差戻し）/ Archived |
| Published | ❌        | 全員       | Archived                            |
| Archived  | ❌        | 参照のみ   | （終端）                            |

**実装**: `VALID_TRANSITIONS` 辞書 `(from_state, action) → to_state` でサーバー側が権威。
クライアント指定の `target_state` は照合のみ（divergence 検出）。

---

## 🔐 認証・認可モデル

### 認証フロー

```
Login → bcrypt 検証 → JWT (access + refresh) 発行
       → 以降 Bearer Token → get_current_user → User 解決
```

### 認可（多層防御）

1. **認証層**: JWT 検証 (`get_current_user`)
2. **テナント層**: 組織メンバーシップ検証 (`UserOrganization`)
3. **リソース層**: プロジェクト所属確認（IDOR 防止）
4. **操作層**: 承認者本人 or platform_admin チェック

> 全リソースアクセスで「認証 ≠ 認可」を徹底。`current_user.id` 保持だけでは不十分で、
> 毎回 `organization_id` の所属を検証する。

---

## ⚙️ 並列処理・整合性

### 承認ワークフローのロック戦略

```
act_on_approval:
  1. WorkflowInstance を FOR UPDATE ロック  ← 親をロックして全承認者を直列化
  2. Approval を FOR UPDATE ロック          ← 同一承認の二重actを防止
  3. 集計（all_approved/any_rejected）      ← 親ロック下で一貫したビュー
  4. Container を FOR UPDATE ロック          ← /transition endpoint と直列化
  5. 状態書込 → commit
```

**ロック順序**: WorkflowInstance → Approval → Container（デッドロック回避のため固定順序）

**分離レベル**: PostgreSQL デフォルト READ COMMITTED。親行ロックにより
マルチ承認者の write-skew を防止。

---

## 🗄️ データモデル概要

```
organizations ──< projects ──< information_containers ──< container_revisions
     │                │                  │
     └─< users        └─< project_members │──< container_files
         │                                 └──< container_state_histories
         └─< user_organizations

requirements_documents ──< requirement_items
workflow_instances ──< workflow_tasks
                   ──< approvals
audit_logs (immutable, append-only)
roles ──< role_permissions >── permissions
```

---

## 📐 ISO 19650 準拠ポイント

| 要件                           | 実装                                                                |
| ------------------------------ | ------------------------------------------------------------------- |
| 情報コンテナ状態管理           | `ContainerState` Enum + 状態遷移 API                                |
| 命名規則検証                   | セグメント定義 + look-ahead バリデーター                            |
| 改訂管理 (P01, C01)            | `ContainerRevision` (revision_code + version_code)                  |
| 監査証跡                       | `audit_logs` + immutable トリガー                                   |
| 要求文書 (OIR/AIR/PIR/EIR/BEP) | `RequirementsDocument` + `RequirementItem` (what/when/how/for_whom) |
| 承認権限                       | `Approval` + 段階別 approval_stage                                  |
| セキュリティ分類               | `SecurityLevel` Enum (public/limited/confidential/restricted)       |

---

_最終更新: 2026-05-31 / Sprint 1_
