# ⚙️ 技術スタック詳細

> Open BIM 情報基盤の技術構成・設計判断・依存関係を記述した **開発者・エンジニア向け** ドキュメントです。
> 非エンジニア向けの概要は → [README.md](../README.md) | IT部門向けセットアップは → [IT_SETUP.md](IT_SETUP.md)

---

## 📋 目次

- [アーキテクチャ全体図](#-アーキテクチャ全体図)
- [使用技術一覧](#-使用技術一覧)
- [フロントエンド構成](#-フロントエンド構成)
- [バックエンド構成](#-バックエンド構成)
- [データベーススキーマ](#-データベーススキーマ)
- [API エンドポイント一覧](#-api-エンドポイント一覧)
- [認証・セキュリティ設計](#-認証セキュリティ設計)
- [ISO 19650 実装マッピング](#-iso-19650-実装マッピング)
- [モックモード設計](#-モックモード設計)
- [CI/CD パイプライン](#-cicd-パイプライン)
- [開発環境セットアップ](#-開発環境セットアップ)

---

## 🏗️ アーキテクチャ全体図

### 本番モード（フルスタック）

```mermaid
graph TB
    subgraph Client["🌐 クライアント"]
        Browser["ブラウザ\nChrome / Edge / Firefox"]
    end

    subgraph FE["🖥️ フロントエンド（:5173）"]
        React["⚛️ React 18 + TypeScript"]
        Vite["⚡ Vite 5"]
        TQ["🔄 TanStack Query v5"]
        Router["🧭 React Router v6"]
        MockFlag{{"VITE_MOCK_MODE?"}}
    end

    subgraph BE["⚙️ バックエンド（:8000）"]
        FastAPI["🐍 FastAPI 0.110+"]
        Auth["🔐 JWT 認証 / RBAC"]
        NamingEngine["📛 NamingRuleEngine\nISO 19650 Annex A"]
        AuditMiddleware["📋 監査ミドルウェア"]
    end

    subgraph Data["🗄️ データ層"]
        PG[("🐘 PostgreSQL 15\n:5432")]
        Redis[("⚡ Redis 7\n:6379")]
        MinIO[("📦 MinIO\n:9000")]
    end

    Browser -->|"HTTP"| React
    React --> TQ
    React --> Router
    MockFlag -->|"false（本番）"| TQ
    MockFlag -->|"true（モック）"| MockData["📋 designData.ts\n静的モックデータ"]
    TQ -->|"REST API / JSON"| FastAPI
    FastAPI --> Auth
    FastAPI --> NamingEngine
    FastAPI --> AuditMiddleware
    FastAPI -->|"SQLAlchemy ORM"| PG
    FastAPI -->|"aioredis"| Redis
    FastAPI -->|"aioboto3 / S3 API"| MinIO

    style Client fill:#E3F2FD,stroke:#1976D2
    style FE fill:#F3E5F5,stroke:#7B1FA2
    style BE fill:#E8F5E9,stroke:#388E3C
    style Data fill:#FFF8E1,stroke:#F57F17
```

### デモモード（フロントエンドのみ）

```mermaid
graph LR
    Browser["🌐 ブラウザ"] -->|":3000"| Nginx["🖥️ Nginx\n（Vite ビルド済み）"]
    Nginx --> FE["⚛️ React SPA\nVITE_MOCK_MODE=true"]
    FE --> DS["📋 designData.ts\n• 10プロジェクト\n• 113情報コンテナ\n• 30承認フロー\n• 55監査ログ\n• 命名規則定義"]
    DS -.->|"バックエンド不要"| X(["❌ PostgreSQL\n❌ Redis\n❌ MinIO"])

    style DS fill:#E8EAF6,stroke:#3F51B5
    style X fill:#FFEBEE,stroke:#C62828
```

---

## 📦 使用技術一覧

### フロントエンド

| 技術              | バージョン | 用途                                      |
| ----------------- | ---------- | ----------------------------------------- |
| ⚛️ React          | 18         | UI コンポーネントフレームワーク           |
| 📘 TypeScript     | 5.x        | 型安全開発・コンパイル時エラー検出        |
| ⚡ Vite           | 5.x        | 高速ビルドツール（HMR 対応）              |
| 🔄 TanStack Query | v5         | サーバー状態管理・キャッシュ・再フェッチ  |
| 🧭 React Router   | v6         | クライアントサイドルーティング            |
| 🎨 Lucide React   | latest     | アイコンライブラリ（SVG）                 |
| 📡 Axios          | 1.x        | HTTP クライアント（インターセプター対応） |
| 🎭 Vitest         | v4         | ユニット・コンポーネントテスト            |
| 🎭 Playwright     | latest     | E2E テスト                                |

### バックエンド

| 技術              | バージョン | 用途                                       |
| ----------------- | ---------- | ------------------------------------------ |
| 🐍 Python         | 3.11       | 実行環境                                   |
| ⚡ FastAPI        | 0.110+     | 非同期 REST API フレームワーク             |
| 🗃️ SQLAlchemy     | 2.0        | ORM（非同期対応 async session）            |
| 🔄 Alembic        | latest     | DB スキーママイグレーション                |
| ✅ Pydantic       | v2         | リクエスト/レスポンスバリデーション        |
| 🔐 python-jose    | latest     | JWT トークン生成・検証                     |
| 🔑 passlib        | latest     | パスワードハッシュ（bcrypt）               |
| 📦 aioboto3       | latest     | MinIO / S3 非同期クライアント              |
| 🔴 aioredis       | latest     | Redis 非同期クライアント                   |
| 🧪 pytest         | 7.x+       | テストフレームワーク                       |
| 🧪 pytest-asyncio | latest     | 非同期テスト対応                           |
| ⏱️ pytest-timeout | latest     | テストタイムアウト制御                     |
| 🧪 moto           | latest     | AWS/S3 モックライブラリ                    |
| 📏 Ruff           | latest     | 静的解析・フォーマット（Black/isort 代替） |

### データ・インフラ

| 技術              | バージョン | 用途                               |
| ----------------- | ---------- | ---------------------------------- |
| 🐘 PostgreSQL     | 15         | メインリレーショナル DB            |
| ⚡ Redis          | 7          | セッション・キャッシュ・レート制限 |
| 📦 MinIO          | latest     | S3 互換ファイルストレージ          |
| 🐳 Docker         | 24.0+      | コンテナランタイム                 |
| 🐳 Docker Compose | v2.20+     | マルチコンテナオーケストレーション |
| 🔧 Nginx          | latest     | 静的ファイル配信（デモモード）     |
| ⚙️ systemd        | -          | OS 起動時サービス自動起動          |

---

## 🖥️ フロントエンド構成

### コンポーネントツリー

```mermaid
graph TD
    App["⚛️ App.tsx\n（ルートコンポーネント）"]

    App --> AuthProvider["🔐 AuthProvider\n（認証コンテキスト）"]
    App --> QueryProvider["🔄 QueryClientProvider\n（TanStack Query）"]
    App --> Router["🧭 Router"]

    Router --> Layout["📐 Layout.tsx\n（共通レイアウト）"]
    Layout --> Sidebar["📌 Sidebar.tsx\n（ナビゲーション）"]
    Layout --> Pages

    Pages --> Dashboard["📊 Dashboard\n（KPI・進捗）"]
    Pages --> Projects["📁 Projects\n（プロジェクト一覧）"]
    Pages --> Containers["📄 Containers\n（情報コンテナ）"]
    Pages --> Workflows["✅ Workflows\n（承認フロー）"]
    Pages --> AuditLogs["📋 AuditLogs\n（監査ログ）"]
    Pages --> NamingRules["📛 NamingRules\n（命名規則設定）"]
    Pages --> Settings["⚙️ Settings"]

    style App fill:#F3E5F5,stroke:#7B1FA2
    style Pages fill:#E8F5E9,stroke:#388E3C
```

### モックモード データフロー

```mermaid
flowchart LR
    ENV{{"VITE_MOCK_MODE\n=true?"}}

    ENV -->|"Yes（開発・デモ）"| MockService["📋 mockApiService.ts\n（静的レスポンス）"]
    ENV -->|"No（本番）"| RealAPI["📡 api.ts\nAxios → FastAPI"]

    MockService --> DesignData["📄 designData.ts\n113コンテナ / 30承認 / 55ログ"]
    RealAPI --> FastAPI["⚙️ FastAPI :8000"]

    style MockService fill:#E8EAF6,stroke:#3F51B5
    style RealAPI fill:#E8F5E9,stroke:#388E3C
```

### 主要ファイル構成

```
frontend/src/
├── components/          # 再利用可能UIコンポーネント
│   ├── ui/              # ボタン・モーダル・テーブル等
│   └── domain/          # BIM固有コンポーネント
├── pages/               # ルートごとのページコンポーネント
├── lib/
│   ├── designData.ts    # モックデータ定義（全エンティティ）
│   ├── api.ts           # Axios インスタンス + インターセプター
│   └── mockApiService.ts # モックAPI実装
├── hooks/               # カスタムフック（useProjects 等）
├── types/               # TypeScript 型定義
└── contexts/            # React Context（Auth 等）
```

---

## ⚙️ バックエンド構成

### レイヤーアーキテクチャ

```mermaid
graph TB
    subgraph API["🌐 API Layer（FastAPI）"]
        Router_["📡 APIRouter\n/api/v1/..."]
        Middleware["🔍 Middleware\n（Auth / CORS / Audit）"]
    end

    subgraph Domain["🏛️ ドメイン層"]
        ContainerSvc["📄 ContainerService"]
        WorkflowSvc["✅ WorkflowService"]
        NamingEngine_["📛 NamingRuleEngine\n（ISO 19650 Annex A）"]
        AuditSvc["📋 AuditService"]
    end

    subgraph Infra["🗄️ インフラ層"]
        Repo["🗃️ Repository\n（SQLAlchemy）"]
        FileStore["📦 FileStorage\n（MinIO）"]
        Cache["⚡ CacheService\n（Redis）"]
    end

    Router_ --> Middleware
    Middleware --> ContainerSvc
    Middleware --> WorkflowSvc
    Middleware --> NamingEngine_
    ContainerSvc --> AuditSvc
    WorkflowSvc --> AuditSvc
    ContainerSvc --> Repo
    WorkflowSvc --> Repo
    ContainerSvc --> FileStore
    Repo --> PG[("🐘 PostgreSQL")]
    Cache --> Redis_[("⚡ Redis")]

    style API fill:#E8F5E9,stroke:#388E3C
    style Domain fill:#E3F2FD,stroke:#1976D2
    style Infra fill:#FFF8E1,stroke:#F57F17
```

### 主要ファイル構成

```
backend/app/
├── main.py              # FastAPI アプリ初期化 / ミドルウェア登録
├── api/v1/              # APIルーター
│   ├── auth.py          # 認証 (login / refresh / logout)
│   ├── projects.py      # プロジェクト CRUD
│   ├── containers.py    # 情報コンテナ CRUD + 状態遷移
│   ├── workflows.py     # 承認フロー管理
│   ├── audit_logs.py    # 監査ログ取得
│   └── naming_rules.py  # 命名規則 CRUD + 検証
├── models/              # SQLAlchemy ORM モデル
├── schemas/             # Pydantic スキーマ（Request/Response）
├── services/            # ビジネスロジック
│   └── naming_rule_engine.py  # ISO 19650 Annex A 検証
├── core/
│   ├── security.py      # JWT / bcrypt
│   └── config.py        # 環境変数設定
└── db/
    └── session.py       # AsyncSession ファクトリ
```

---

## 🗄️ データベーススキーマ

### ER ダイアグラム

```mermaid
erDiagram
    organizations {
        uuid id PK
        string name
        string slug
    }
    users {
        uuid id PK
        string email UK
        string hashed_password
        string role
        bool is_active
        uuid org_id FK
    }
    projects {
        uuid id PK
        string identifier UK
        string name
        string status
        uuid org_id FK
        uuid lead_id FK
    }
    naming_rules {
        uuid id PK
        uuid project_id FK
        jsonb segments
        bool is_active
    }
    information_containers {
        uuid id PK
        string identifier
        string title
        string current_state
        string security_level
        uuid project_id FK
        uuid created_by FK
    }
    revisions {
        uuid id PK
        string revision_code
        string state_from
        string state_to
        timestamp created_at
        uuid container_id FK
        uuid author_id FK
    }
    files {
        uuid id PK
        string filename
        string mime_type
        string sha256_hash
        string storage_path
        uuid container_id FK
    }
    workflow_requests {
        uuid id PK
        string stage
        string status
        string priority
        timestamp due_date
        uuid container_id FK
        uuid requested_by FK
    }
    audit_logs {
        uuid id PK
        timestamp occurred_at
        string event_type
        string operation
        string result
        inet actor_ip
        uuid actor_id FK
        string target_type
        string target_id
    }
    project_members {
        uuid project_id FK
        uuid user_id FK
        string role
    }

    organizations ||--o{ users : "所属"
    organizations ||--o{ projects : "所有"
    projects ||--o{ naming_rules : "持つ"
    projects ||--o{ information_containers : "含む"
    projects ||--o{ project_members : "参加"
    users ||--o{ project_members : "所属"
    information_containers ||--o{ revisions : "版管理"
    information_containers ||--o{ files : "添付"
    information_containers ||--o{ workflow_requests : "承認申請"
    users ||--o{ audit_logs : "操作者"
    users ||--o{ workflow_requests : "申請者"
```

---

## 📡 API エンドポイント一覧

### 主要エンドポイントマップ

```mermaid
graph LR
    subgraph Auth["🔐 /auth"]
        Login["POST /login"]
        Refresh["POST /refresh"]
        Logout["POST /logout"]
        Me["GET /me"]
    end

    subgraph Proj["📁 /projects"]
        PList["GET /"]
        PCreate["POST /"]
        PGet["GET /{id}"]
        PUpdate["PUT /{id}"]
    end

    subgraph Cont["📄 /containers"]
        CList["GET /"]
        CCreate["POST /"]
        CGet["GET /{id}"]
        CTransit["POST /{id}/transition"]
        CValidate["POST /{id}/validate-name"]
        CUpload["POST /{id}/files"]
    end

    subgraph WF["✅ /workflows"]
        WList["GET /"]
        WCreate["POST /"]
        WApprove["POST /{id}/approve"]
        WReject["POST /{id}/reject"]
    end

    subgraph Audit["📋 /audit-logs"]
        AList["GET /"]
        AExport["GET /export"]
    end

    subgraph NR["📛 /naming-rules"]
        NList["GET /"]
        NCreate["POST /"]
        NCheck["POST /validate"]
    end

    style Auth fill:#FCE4EC,stroke:#C62828
    style Proj fill:#E8F5E9,stroke:#388E3C
    style Cont fill:#E3F2FD,stroke:#1976D2
    style WF fill:#FFF8E1,stroke:#F57F17
    style Audit fill:#F3E5F5,stroke:#7B1FA2
    style NR fill:#E0F2F1,stroke:#00796B
```

### エンドポイント詳細

| エンドポイント                          | メソッド | 認証    | 説明                                  |
| --------------------------------------- | -------- | ------- | ------------------------------------- |
| `/api/v1/auth/login`                    | POST     | ❌ 不要 | メール/パスワードでログイン、JWT 返却 |
| `/api/v1/auth/me`                       | GET      | ✅ JWT  | ログイン中ユーザー情報                |
| `/api/v1/projects`                      | GET      | ✅ JWT  | プロジェクト一覧（権限フィルタ）      |
| `/api/v1/projects/{id}`                 | GET      | ✅ JWT  | プロジェクト詳細                      |
| `/api/v1/containers`                    | GET      | ✅ JWT  | 情報コンテナ一覧                      |
| `/api/v1/containers/{id}/transition`    | POST     | ✅ JWT  | CDE状態遷移（WIP→Shared等）           |
| `/api/v1/containers/{id}/validate-name` | POST     | ✅ JWT  | ISO 19650 命名規則検証                |
| `/api/v1/workflows`                     | GET      | ✅ JWT  | 承認フロー一覧                        |
| `/api/v1/workflows/{id}/approve`        | POST     | ✅ JWT  | 承認（承認者ロール必須）              |
| `/api/v1/workflows/{id}/reject`         | POST     | ✅ JWT  | 差し戻し（コメント必須）              |
| `/api/v1/audit-logs`                    | GET      | ✅ JWT  | 監査ログ一覧（管理者のみ）            |
| `/api/v1/naming-rules/validate`         | POST     | ✅ JWT  | 命名規則バリデーション単体実行        |

---

## 🔐 認証・セキュリティ設計

### 認証フロー（JWT）

```mermaid
sequenceDiagram
    participant B as 🌐 ブラウザ
    participant F as ⚛️ Frontend
    participant A as ⚙️ FastAPI
    participant DB as 🐘 PostgreSQL
    participant R as ⚡ Redis

    B->>F: ログイン画面入力
    F->>A: POST /auth/login\n{email, password}
    A->>DB: SELECT users WHERE email=?
    DB-->>A: ユーザーレコード
    A->>A: bcrypt.verify(password, hash)
    A-->>F: {access_token, refresh_token}
    F->>R: セッション保存（オプション）

    Note over F,A: 以降のリクエスト
    F->>A: GET /api/v1/projects\nAuthorization: Bearer <token>
    A->>A: JWT 署名検証\n有効期限チェック
    A->>DB: SELECT（RBACフィルタ適用）
    DB-->>A: データ
    A-->>F: JSON レスポンス
```

### セキュリティ対策一覧

| カテゴリ                | 対策                   | 実装詳細                                            |
| ----------------------- | ---------------------- | --------------------------------------------------- |
| 🔐 認証                 | JWT Bearer トークン    | python-jose / HS256（RS256 対応準備済み）           |
| 🔑 パスワード           | bcrypt ハッシュ        | passlib[bcrypt] / work factor 12                    |
| 🛡️ 認可                 | RBAC                   | ロール: admin / manager / reviewer / member         |
| 📋 監査                 | 全操作記録             | audit_logs テーブル（actor / target / IP / result） |
| 🌐 CORS                 | ホワイトリスト         | 許可オリジンを環境変数で管理                        |
| 💉 SQL インジェクション | ORM パラメータバインド | SQLAlchemy 2.0 async                                |
| 🛡️ XSS                  | 自動エスケープ         | React の JSX エスケープ                             |
| 📁 ファイル検証         | SHA-256 + MIME         | アップロード時に整合性検証                          |
| 🔒 機密区分             | 4段階 security_level   | public / limited / confidential / restricted        |

---

## 📐 ISO 19650 実装マッピング

### CDE 状態遷移

```mermaid
stateDiagram-v2
    [*] --> WIP : コンテナ作成

    WIP --> Shared : チームへ提出\n（transition API）
    Shared --> WIP : 差し戻し\n（reject）
    Shared --> Published : 承認完了\n（approve）
    Published --> WIP : 改訂開始
    Published --> Archived : プロジェクト完了

    note right of WIP
        current_state = "WIP"
        編集可・提出前
    end note
    note right of Shared
        current_state = "Shared"
        レビュー中
    end note
    note right of Published
        current_state = "Published"
        正式公開版
    end note
    note right of Archived
        current_state = "Archived"
        読み取り専用
    end note
```

### ISO 19650 要件マッピング表

| ISO 19650 要件       | 実装クラス/テーブル              | 説明                                                   |
| -------------------- | -------------------------------- | ------------------------------------------------------ |
| CDE 状態管理         | `containers.current_state`       | WIP/Shared/Published/Archived の4状態                  |
| 命名規則 Annex A     | `NamingRuleEngine`               | 7セグメント検証（PROJECT-ORG-VOL-LEVEL-TYPE-ROLE-NUM） |
| 情報セキュリティ区分 | `containers.security_level`      | 4段階（public/limited/confidential/restricted）        |
| 改訂管理             | `revisions` テーブル             | 全状態変化を履歴として保存                             |
| 役割と責任           | `rbac_roles` + `project_members` | プロジェクト単位のロール付与                           |
| 監査証跡             | `audit_logs` テーブル            | actor/target/operation/result/IP を記録                |
| EIR / BEP 管理       | `projects.metadata` (JSONB)      | 情報要求・BIM実行計画のメタデータ管理                  |

### 命名規則 7セグメント構造（ISO 19650 Annex A）

```
{PROJECT} - {ORIGINATOR} - {VOLUME} - {LEVEL} - {TYPE} - {ROLE} - {NUMBER}
    TKO   -     CVL      -   ZZ    -   ZZ    -   DR   -    A   -  0001
```

| セグメント | 例            | 説明                             |
| ---------- | ------------- | -------------------------------- |
| PROJECT    | TKO, HKR, HND | プロジェクト識別子               |
| ORIGINATOR | CVL, STR, MEP | 担当組織・専門分野               |
| VOLUME     | ZZ, TN1, BRG  | ボリューム/エリア区分            |
| LEVEL      | ZZ, B1, RF    | フロア/レベル                    |
| TYPE       | DR, MD, SP    | 情報タイプ（図面/モデル/仕様書） |
| ROLE       | A, C, E       | 作成者ロール                     |
| NUMBER     | 0001〜9999    | 連番                             |

---

## 🎭 モックモード設計

### 環境変数切り替え

```mermaid
flowchart TD
    Start["npm run dev / docker compose up"] --> Check{{"VITE_MOCK_MODE\n環境変数?"}}
    Check -->|"true"| Mock["📋 mockApiService.ts\n静的JSONレスポンス"]
    Check -->|"false / 未設定"| Real["📡 api.ts\nAxios → http://localhost:8000"]

    Mock --> DesignData["📄 designData.ts\n• demoProjects (10件)\n• demoContainers (113件)\n• demoApprovals (30件)\n• demoAuditLogs (55件)\n• demoNamingRule"]

    Real --> Backend["⚙️ FastAPI バックエンド\n（要起動: docker compose up）"]

    style Mock fill:#E8EAF6,stroke:#3F51B5
    style Real fill:#E8F5E9,stroke:#388E3C
```

### モックデータ内訳

| データ種別      | 件数                        | ファイル                        |
| --------------- | --------------------------- | ------------------------------- |
| 📁 プロジェクト | 10件                        | `designData.ts: demoProjects`   |
| 📄 情報コンテナ | 113件                       | `designData.ts: demoContainers` |
| ✅ 承認フロー   | 30件                        | `designData.ts: demoApprovals`  |
| 📋 監査ログ     | 55件                        | `designData.ts: demoAuditLogs`  |
| 📛 命名規則     | 1定義（10プロジェクト対応） | `designData.ts: demoNamingRule` |

---

## 🔄 CI/CD パイプライン

### GitHub Actions ワークフロー

```mermaid
flowchart TD
    Push["📤 git push\n（feature/* または PR）"] --> Trigger["⚡ GitHub Actions 起動"]

    Trigger --> Parallel["並列実行"]

    Parallel --> LintFE["🔍 Frontend Lint\nESLint + TypeScript check"]
    Parallel --> LintBE["🔍 Backend Lint\nRuff"]
    Parallel --> TestBE["🧪 Backend Tests\npytest + moto\n（タイムアウト30s）"]
    Parallel --> TestFE["🧪 Frontend Tests\nVitest"]
    Parallel --> Security["🔒 Security Scan\nDependency audit"]

    LintFE --> Build["🏗️ Frontend Build\nvite build"]
    LintBE --> Build
    TestBE --> Build
    TestFE --> Build
    Security --> Build

    Build --> E2E["🎭 E2E Tests\nPlaywright"]
    E2E --> Gate{{"✅ 全ジョブ\n通過?"}}

    Gate -->|"Yes"| Ready["🟢 PR Merge 可能"]
    Gate -->|"No"| Block["🔴 Merge ブロック\n（要修正）"]

    style Push fill:#E3F2FD,stroke:#1976D2
    style Gate fill:#FFF8E1,stroke:#F57F17
    style Ready fill:#E8F5E9,stroke:#388E3C
    style Block fill:#FFEBEE,stroke:#C62828
```

### CI ジョブ詳細

| ジョブ            | ツール                         | 対象                       | 所要時間目安 |
| ----------------- | ------------------------------ | -------------------------- | ------------ |
| 🔍 Frontend Lint  | ESLint + tsc --noEmit          | `frontend/src/**`          | ~30秒        |
| 🔍 Backend Lint   | Ruff                           | `backend/app/**`           | ~10秒        |
| 🧪 Backend Tests  | pytest + moto + pytest-timeout | `backend/tests/**`         | ~60秒        |
| 🧪 Frontend Tests | Vitest                         | `frontend/src/**/*.test.*` | ~30秒        |
| 🔒 Security Scan  | npm audit + pip-audit          | 依存パッケージ             | ~20秒        |
| 🏗️ Build          | vite build                     | `frontend/`                | ~45秒        |
| 🎭 E2E Tests      | Playwright                     | `e2e/**`                   | ~120秒       |

---

## 🚀 開発環境セットアップ

### バックエンド起動

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# PostgreSQL + Redis が必要（Docker Compose 推奨）
docker compose up postgres redis -d

# マイグレーション実行
alembic upgrade head

# 開発サーバー起動
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs  (Swagger UI)
```

### フロントエンド起動

```bash
cd frontend
npm install

# 本番モード（バックエンド接続）
cp .env.example .env.local
# .env.local: VITE_API_BASE_URL=http://localhost:8000
npm run dev   # → http://localhost:5173

# モックモード（バックエンド不要）
VITE_MOCK_MODE=true npm run dev
```

### 全スタック起動（推奨）

```bash
# フルスタック
./scripts/start.sh

# デモモード（バックエンド不要・即起動）
./scripts/start.sh demo
```

### テスト実行

```bash
# バックエンドテスト
cd backend
pytest -v --timeout=30

# フロントエンドテスト
cd frontend
npm run test

# E2E テスト
cd e2e
npx playwright test
```

---

## 🔗 関連ドキュメント

| 対象者                     | ドキュメント                                                                 |
| -------------------------- | ---------------------------------------------------------------------------- |
| 👔 非エンジニア・経営者    | [📋 README.md（概要）](../README.md)                                         |
| 💻 IT 部門・システム管理者 | [📘 IT_SETUP.md（セットアップ）](IT_SETUP.md)                                |
| 📐 BIM 管理者・技術者      | [📐 BIM_GUIDE.md（ISO 19650 ガイド）](BIM_GUIDE.md)                          |
| 🌐 API リファレンス        | [Swagger UI](http://localhost:8000/docs)（起動後）                           |
| 📦 GitHub                  | [リポジトリ](https://github.com/Kensan196948G/Open-BIM-Information-Platform) |

---

_← [README.md（概要）](../README.md) | [📘 IT_SETUP.md（IT セットアップ）](IT_SETUP.md) →_
