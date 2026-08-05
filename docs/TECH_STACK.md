# 🔧 技術スタック詳細

> Open BIM 情報基盤の技術構成・設計判断・依存関係を記述した**エンジニア・開発担当者向け**ドキュメントです。
> ISO 19650 は「準拠支援・設計目標」であり、第三者認証は未取得です。

---

## 📋 目次

- [🏗️ アーキテクチャ全体図](#️-アーキテクチャ全体図)
- [📦 使用技術一覧](#-使用技術一覧)
- [🔄 データフロー（CDE 状態遷移）](#-データフローcde-状態遷移)
- [🔐 認証・セキュリティ設計](#-認証セキュリティ設計)
- [🗄️ データベーススキーマ概要](#️-データベーススキーマ概要)
- [📐 ISO 19650 実装マッピング](#-iso-19650-実装マッピング)
- [⚙️ CI/CD パイプライン](#️-cicd-パイプライン)
- [🚀 開発環境セットアップ](#-開発環境セットアップ)
- [🔗 関連リンク](#-関連リンク)

---

## 🏗️ アーキテクチャ全体図

```mermaid
graph TB
    subgraph Client["🌐 クライアント層"]
        Browser["🖥️ Webブラウザ"]
    end

    subgraph FE["🖥️ フロントエンド層 (Port 5173)"]
        React["⚛️ React 18 + TypeScript"]
        Vite["⚡ Vite 5 (bundler / Nginx)"]
        TQ["🔄 TanStack Query v5\n(サーバー状態管理)"]
        Router["🧭 React Router v6"]
        Lucide["🎨 Lucide React (アイコン)"]
    end

    subgraph BE["⚙️ バックエンド層 (Port 8000)"]
        FastAPI["⚡ FastAPI (Python 3.11)"]
        subgraph Middleware["🔒 ミドルウェア"]
            Auth["🔑 JWT 認証\npython-jose"]
            RBAC["👥 RBAC\n権限チェック"]
            Naming["📐 NamingRuleEngine\nISO 19650 Annex A"]
        end
        SQLAlchemy["🗃️ SQLAlchemy 2.0 (ORM)"]
        Alembic["🔄 Alembic (migration)"]
        Pydantic["✅ Pydantic v2 (validation)"]
    end

    subgraph Data["🗄️ データ層"]
        PG["🐘 PostgreSQL 15\nPort 5432\n(メインDB)"]
        Redis["⚡ Redis 7\nPort 6379\n(セッション・キャッシュ)"]
        MinIO["📦 MinIO\nPort 9000\n(S3互換ストレージ)"]
    end

    subgraph Audit["📋 監査層"]
        AuditLogs["📋 audit_logs テーブル\n(Append-Only)"]
    end

    Browser -->|"HTTPS"| Vite
    React --> TQ
    React --> Router
    TQ -->|"REST API / JSON"| FastAPI
    FastAPI --> Auth
    FastAPI --> RBAC
    FastAPI --> Naming
    FastAPI --> SQLAlchemy
    SQLAlchemy --> PG
    FastAPI --> Redis
    FastAPI --> MinIO
    FastAPI --> AuditLogs
    AuditLogs --> PG
```

---

## 📦 使用技術一覧

### 🖥️ フロントエンド

| 技術 | バージョン | 用途 |
|---|---|---|
| ⚛️ React | 18 | UI フレームワーク |
| 📘 TypeScript | 5.x | 型安全な開発 |
| ⚡ Vite | 5.x | 高速ビルドツール |
| 🔄 TanStack Query | v5 | サーバー状態管理・キャッシュ |
| 🧭 React Router | v6 | クライアントサイドルーティング |
| 🎨 Lucide React | latest | アイコンライブラリ |
| 📡 Axios | 1.x | HTTP クライアント |

### ⚙️ バックエンド

| 技術 | バージョン | 用途 |
|---|---|---|
| 🐍 Python | 3.11 | 実行環境 |
| ⚡ FastAPI | 0.110+ | REST API フレームワーク |
| 🗃️ SQLAlchemy | 2.0 | ORM（Object-Relational Mapper） |
| 🔄 Alembic | latest | DB スキーママイグレーション |
| ✅ Pydantic | v2 | データバリデーション・シリアライゼーション |
| 🔐 python-jose | latest | JWT トークン処理 |
| 🔑 passlib / bcrypt | latest | パスワードハッシュ |
| 📦 aioboto3 | latest | MinIO/S3 非同期クライアント |
| 🔌 httpx | latest | 非同期 HTTP クライアント（テスト用） |

### 🗄️ データ・インフラ

| 技術 | バージョン | 用途 |
|---|---|---|
| 🐘 PostgreSQL | 15 | リレーショナル DB（メインデータストア） |
| ⚡ Redis | 7 | セッション・キャッシュ |
| 📦 MinIO | latest | S3 互換ファイルストレージ |
| 🐳 Docker Compose | v2 | コンテナオーケストレーション |
| 🔧 systemd | — | サービス自動起動管理 |
| 🌐 Nginx | latest | リバースプロキシ・静的ファイル配信 |

### 🧪 テスト・品質

| 技術 | バージョン | 用途 |
|---|---|---|
| 🧪 pytest | 8.x | バックエンドユニット・統合テスト |
| ⚡ pytest-asyncio | latest | 非同期テストサポート |
| ⏱️ pytest-timeout | latest | テストハング防止（30秒タイムアウト） |
| 🧩 moto | latest | AWS/MinIO モック |
| ⚡ Vitest | v4 | フロントエンドユニットテスト |
| 🎭 Playwright | latest | E2E（エンドツーエンド）テスト |
| 🔍 ESLint | latest | フロントエンド静的解析 |
| 📏 Ruff | latest | Python 静的解析・フォーマット |

---

## 🔄 データフロー（CDE 状態遷移）

ISO 19650 に基づく **CDE（Common Data Environment）** の情報コンテナ状態遷移:

```mermaid
stateDiagram-v2
    [*] --> WIP : 📝 コンテナ作成\nPOST /containers

    WIP --> Shared : 📤 チームへ提出\nPATCH /containers/{id}/transition\n(action: submit)

    Shared --> WIP : ↩️ 差し戻し\n(action: reject)
    Shared --> Published : ✅ 承認・発行\n(action: approve)

    Published --> WIP : 🔄 改訂開始\n(action: revise)
    Published --> Archived : 📁 保管\n(action: archive)

    Archived --> [*] : 🔒 完全保管\n(変更不可)

    note right of WIP
        current_state = "WIP"
        🟡 作業中
        個人・チームで編集可
    end note

    note right of Shared
        current_state = "Shared"
        🔵 共有・レビュー中
        承認者が確認
    end note

    note right of Published
        current_state = "Published"
        🟢 承認済み・公式
        現場・関係者に公開
    end note

    note right of Archived
        current_state = "Archived"
        ⬜ 保管済み
        改ざん防止・永久保存
    end note
```

### API エンドポイント構成

```mermaid
graph LR
    subgraph Auth["🔑 認証"]
        A1["POST /auth/register"]
        A2["POST /auth/login"]
        A3["GET /auth/me"]
    end

    subgraph Projects["📁 プロジェクト"]
        P1["GET /projects"]
        P2["POST /projects"]
        P3["GET /projects/{id}"]
        P4["PATCH /projects/{id}"]
    end

    subgraph Containers["📦 情報コンテナ"]
        C1["GET /projects/{id}/containers"]
        C2["POST /projects/{id}/containers"]
        C3["GET /projects/{id}/containers/{cid}"]
        C4["PATCH /projects/{id}/containers/{cid}"]
        C5["POST /projects/{id}/containers/{cid}/transition"]
    end

    subgraph Audit["📋 監査"]
        AU1["GET /audit-logs"]
    end

    subgraph Naming["📐 命名規則"]
        N1["GET /naming-rules"]
        N2["POST /naming-rules/validate"]
    end

    Auth --> Projects
    Projects --> Containers
    Containers --> C5
```

---

## 🔐 認証・セキュリティ設計

```mermaid
sequenceDiagram
    participant Browser as 🌐 ブラウザ
    participant API as ⚙️ FastAPI
    participant DB as 🗄️ PostgreSQL
    participant Redis as ⚡ Redis

    Browser->>API: POST /auth/login\n(email + password)
    API->>DB: ユーザー検索
    DB-->>API: ユーザー情報
    API->>API: bcrypt パスワード検証
    API->>Redis: セッション情報キャッシュ
    API-->>Browser: 🔑 JWT アクセストークン\n(有効期限: 30分)

    Browser->>API: GET /projects\nAuthorization: Bearer <token>
    API->>API: ① JWT 署名検証\n② RBAC 権限チェック\n③ 組織メンバーシップ確認
    API->>DB: SELECT（権限フィルタ適用）
    DB-->>API: データ
    API-->>Browser: ✅ JSON レスポンス

    Note over API,DB: すべての操作は audit_logs に自動記録
```

### 🛡️ セキュリティ対策一覧

| 🛡️ 対策 | 実装 | 備考 |
|---|---|---|
| 🔑 認証 | JWT (HS256、RS256 対応準備済み) | 30分有効期限 |
| 🔐 パスワード | bcrypt ハッシュ | コスト係数 12 |
| 👥 RBAC | ロールベースアクセス制御 | `UserOrganization.role_in_org` |
| 🔒 プラットフォーム管理者 | `User.is_platform_admin` フラグ | 全組織横断アクセス |
| 📋 監査証跡 | `audit_logs` テーブル（Append-Only・DBトリガー） | J-SOX 対応は設計目標・未認証 |
| 🌐 CORS | ホワイトリスト制御 | 許可オリジンのみ |
| 💉 SQL インジェクション | SQLAlchemy ORM（パラメータバインド） | — |
| 🔒 XSS | React の自動エスケープ | — |
| 📁 ファイル検証 | SHA-256 + MIME タイプ検証 | アップロード時 |
| 🔍 IDOR 防止 | 非メンバーへの 404 返却 | 403 ではなく 404 でリソース存在を隠蔽 |

---

## 🗄️ データベーススキーマ概要

```mermaid
erDiagram
    organizations {
        uuid id PK
        string name
        string slug
    }

    users {
        uuid id PK
        string email
        string username
        bool is_platform_admin
        bool is_active
    }

    user_organizations {
        uuid user_id FK
        uuid organization_id FK
        string role_in_org
    }

    projects {
        uuid id PK
        uuid organization_id FK
        string name
        string code
        string status
        string applied_standard
    }

    information_containers {
        uuid id PK
        uuid project_id FK
        string identifier
        string current_state
        string security_level
        string title
    }

    revisions {
        uuid id PK
        uuid container_id FK
        int revision_number
        string state
    }

    naming_rules {
        uuid id PK
        uuid project_id FK
        string segment_pattern
    }

    audit_logs {
        uuid id PK
        uuid actor_id FK
        string target_type
        uuid target_id
        string operation
        string result
        timestamp created_at
    }

    organizations ||--o{ user_organizations : "所属"
    users ||--o{ user_organizations : "参加"
    organizations ||--o{ projects : "所有"
    projects ||--o{ information_containers : "含む"
    projects ||--o{ naming_rules : "定義"
    information_containers ||--o{ revisions : "版管理"
    users ||--o{ audit_logs : "操作記録"
```

---

## 📐 ISO 19650 実装マッピング

| 📐 ISO 19650 要件 | 🔧 実装 | 📁 コード位置 |
|---|---|---|
| CDE 状態管理 | `containers.current_state` (WIP/Shared/Published/Archived) | `app/models/container.py` |
| 命名規則 (Annex A) | `NamingRuleEngine` — 7セグメント検証 | `app/services/naming_rule.py` |
| 情報セキュリティ区分 | `security_level` (public/limited/confidential/restricted) | `app/models/container.py` |
| 改訂管理 | `revisions` テーブル + 状態履歴 | `app/models/revision.py` |
| 役割と責任 | `rbac_roles` + `UserOrganization.role_in_org` | `app/models/user.py` |
| 監査証跡 | `audit_logs` テーブル (actor/target/operation/result) | `app/models/audit_log.py` |
| 情報管理責任者 | `is_platform_admin` フラグ | `app/models/user.py` |

---

## ⚙️ CI/CD パイプライン

```mermaid
flowchart TD
    subgraph Trigger["🚀 トリガー"]
        Push["git push\n(feature branch)"]
        PR["Pull Request\n(→ main)"]
    end

    subgraph CI["🔄 GitHub Actions CI"]
        direction TB
        L["🔍 Lint\nRuff (Python)\nESLint (TypeScript)"]
        T["🧪 Test\npytest (backend)\nVitest (frontend)"]
        B["🏗️ Build\nVite build\n(フロントエンド)"]
        S["🔒 Security Scan\ndependency audit"]
    end

    subgraph Gate["✅ マージゲート"]
        G1["✅ 全 CI ジョブ成功"]
        G2["✅ CodeRabbit レビュー"]
        G3["✅ コードレビュー承認"]
    end

    subgraph Deploy["🚀 デプロイ（手動）"]
        D["🏭 本番環境\ndocker compose up -d"]
    end

    Push --> CI
    PR --> CI
    L --> T
    T --> B
    B --> S
    S --> Gate
    G1 --> G2
    G2 --> G3
    G3 -->|"main merge後"| Deploy
```

### テスト構成

```mermaid
graph LR
    subgraph Backend["🐍 バックエンドテスト (pytest)"]
        BT1["🔑 auth テスト\n12テスト"]
        BT2["📋 audit-logs テスト\n11テスト"]
        BT3["🔄 workflows テスト\n5テスト"]
        BT4["📁 projects テスト\n15テスト"]
        BT5["📦 containers テスト\n~15テスト"]
        BT6["📐 naming_rules テスト\n~10テスト"]
    end

    subgraph Frontend["⚛️ フロントエンドテスト (Vitest)"]
        FT1["🧩 コンポーネントテスト"]
        FT2["🔄 hooks テスト"]
    end

    subgraph E2E["🎭 E2E テスト (Playwright)"]
        ET1["🌐 ブラウザ統合テスト"]
    end

    subgraph DB["🗃️ テスト用DB"]
        SQLite["SQLite in-memory\n(StaticPool)"]
    end

    Backend --> SQLite
```

---

## 🚀 開発環境セットアップ

### バックエンド

```bash
# 1. 仮想環境作成
cd backend
python -m venv venv && source venv/bin/activate

# 2. 依存パッケージインストール
pip install -r requirements.txt
pip install -r requirements-dev.txt  # テスト依存含む

# 3. 環境変数設定
cp .env.example .env

# 4. 開発サーバー起動
uvicorn app.main:app --reload --port 8000

# 5. テスト実行
pytest backend/tests/ -v --timeout=30
```

### フロントエンド

```bash
# 1. 依存パッケージインストール
cd frontend
npm install

# 2. 環境変数設定
cp .env.example .env.local

# 3. 開発サーバー起動（バックエンド連携）
npm run dev   # http://localhost:5173

# 4. モックモード（バックエンド不要）
VITE_MOCK_MODE=true npm run dev

# 5. テスト実行
npm test
```

### Docker Compose（フルスタック起動）

```bash
# 全サービス起動
docker compose up -d

# ログ確認
docker compose logs -f backend

# マイグレーション実行
docker compose exec backend alembic upgrade head
```

---

## 🔗 関連リンク

| ドキュメント | 対象 |
|---|---|
| [📖 README（非エンジニア向け）](../README.md) | 現場・経営・監査 |
| [💻 IT セットアップガイド](IT_SETUP.md) | IT 部門スタッフ |
| [🏗️ アーキテクチャ設計書](ARCHITECTURE.md) | BIM 管理者・設計担当 |
| [🌐 API ドキュメント](http://localhost:8000/docs) | 開発者（起動後） |
| [📦 GitHub リポジトリ](https://github.com/Kensan196948G/Open-BIM-Information-Platform) | 全員 |

---

*⚙️ 技術的な質問・バグ報告は [GitHub Issues](https://github.com/Kensan196948G/Open-BIM-Information-Platform/issues) へ*
