# 🏗️ Open BIM 情報基盤

> **ISO 19650 準拠 BIM 情報管理プラットフォーム**
> Common Data Environment (CDE) 状態管理・命名規則検証・承認ワークフロー・監査証跡を統合した Web システム

[![CI](https://github.com/Kensan196948G/Open-BIM-Information-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Kensan196948G/Open-BIM-Information-Platform/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-v0.1.0_Release_Ready-success)](https://github.com/Kensan196948G/Open-BIM-Information-Platform/releases)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![ISO 19650](https://img.shields.io/badge/ISO-19650-green)
![Tests](https://img.shields.io/badge/tests-35_backend_%2B_8_frontend_%2B_9_E2E-brightgreen)
![Security](https://img.shields.io/badge/security-Critical%2FHigh_0-success)

---

## 📌 概要

| 項目              | 内容                                               |
| ----------------- | -------------------------------------------------- |
| 🌐 提供形態       | Web ベース統合システム                             |
| 📐 準拠規格       | ISO 19650-1/2/5                                    |
| 🗄️ バックエンド   | FastAPI (Python 3.11) + PostgreSQL 15              |
| 🖥️ フロントエンド | React 18 + TypeScript + Vite (ライト/ダークモード) |
| 🔐 認証           | JWT + OIDC 対応準備済み                            |
| 📦 ファイル管理   | MinIO (S3 互換) + SHA-256 検証                     |
| 🐳 インフラ       | Docker Compose                                     |
| 🔧 テスト         | pytest / vitest v4 / Playwright E2E                |

---

## 🗺️ アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React 18 + TypeScript + Vite)                         │
│  ダッシュボード / プロジェクト / 情報コンテナ(CDE) / 承認タスク  │
│  要求文書(EIR/BEP) / アップロード / 監査ログ / 設定              │
│  ↑ ライト/ダークモード・デザイントークン・ISO 19650 命名バリデータ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API (/api/v1/*)
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI (Python 3.11)                                           │
│  auth / projects / containers / workflows / naming-rules         │
│  uploads / audit-logs / naming/validate                          │
│  ↑ JWT auth・RBAC・SELECT FOR UPDATE 排他制御・監査トリガー       │
└──────┬──────────┬──────────┬──────────┬──────────────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
PostgreSQL 15  Redis     MinIO      Alembic
(メタDB+      (キャッシュ) (ファイル   (スキーマ
 監査ログ)               ストレージ)  マイグレーション)
```

### 📐 CDE 状態機械

```
                 submit          approve
  ┌─── WIP ─────────────▶ Shared ──────────▶ Published ─┐
  │     ▲                   │                            │ archive
  │     └───── return ──────┘                            │
  │                                                      ▼
  └───────────────────────────────────────────────── Archived
```

---

## 🎬 主要機能

### 📂 CDE 情報コンテナ管理

| 機能                   | 内容                                            |
| ---------------------- | ----------------------------------------------- |
| 状態遷移               | WIP → Shared → Published → Archived (差戻し可)  |
| 命名規則検証           | ISO 19650-2 Annex A 準拠・7セグメント対応       |
| プロジェクト別命名規則 | カスタムセグメント・区切り文字・許容値 CRUD     |
| セキュリティ分類       | public / limited / confidential / restricted    |
| リビジョン管理         | P01 → C01 ライフサイクル                        |
| ファイル管理           | MinIO + SHA-256 + MIME allowlist + チャンク検証 |

### 🔐 セキュリティ・認証

| 機能       | 内容                                                |
| ---------- | --------------------------------------------------- |
| JWT 認証   | RS256 署名・Bearer token                            |
| RBAC       | ISO 19650 契約ロールベース権限管理                  |
| 監査ログ   | 改ざん防止 (Append-Only + PostgreSQL トリガー)      |
| 脆弱性対策 | IDOR・DoS・XSS・PathTraversal・RaceCondition・ReDoS |

### ✅ 承認ワークフロー

| 機能         | 内容                                     |
| ------------ | ---------------------------------------- |
| 多段階承認   | check / review / approve / authorise     |
| 排他制御     | SELECT FOR UPDATE による Write-Skew 防止 |
| 状態自動遷移 | 承認完了で Container 状態を自動更新      |

### 📋 要求文書管理 (ISO 19650)

OIR → AIR → PIR → **EIR** → **BEP** → **MIDP** → **TIDP** の情報要求階層に対応

---

## 🖥️ UI スクリーン一覧

| 画面              | パス                           | 機能                                       |
| ----------------- | ------------------------------ | ------------------------------------------ |
| 📊 ダッシュボード | `/dashboard`                   | KPI・CDE 状態サマリー・承認タスク一覧      |
| 📁 プロジェクト   | `/projects`                    | プロジェクト CRUD・メンバー管理            |
| 📦 情報コンテナ   | `/projects/:id/containers`     | CDE 管理・状態フィルタ・命名バリデーション |
| 📦 コンテナ詳細   | `/projects/:id/containers/:id` | タブ式詳細・状態遷移ボタン                 |
| ✅ 承認タスク     | `/approvals`                   | 双ペイン承認キュー・優先度・コメント       |
| 📄 要求文書       | `/requirements`                | EIR/BEP/MIDP 文書ビューア                  |
| ⬆️ アップロード   | `/projects/:id/upload`         | リアルタイム命名規則バリデーター           |
| 🛡️ 監査ログ       | `/audit-logs`                  | 全操作履歴・フィルタ・ハッシュ値           |
| ⚙️ 設定           | `/settings`                    | 命名規則マスタ・ロール権限 (実装中)        |

---

## 🛠️ セットアップ

### 前提条件

- Docker & Docker Compose v2.x
- Git

### クイックスタート

```bash
# 1. リポジトリクローン
git clone https://github.com/Kensan196948G/Open-BIM-Information-Platform.git
cd Open-BIM-Information-Platform

# 2. 環境変数設定
cp .env.example .env
# .env を編集 (SECRET_KEY 等を設定)

# 3. 起動
docker compose up -d

# 4. DB マイグレーション (全 2 マイグレーション)
docker compose exec backend alembic upgrade head

# 5. アクセス
# フロントエンド:    http://localhost:5173
# API ドキュメント:  http://localhost:8000/api/docs
# MinIO コンソール:  http://localhost:9001
```

### ローカル開発

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## 🧪 テスト

```bash
# Backend (35 テスト)
cd backend && pytest -v

# Frontend (vitest v4、8 テスト)
cd frontend && npm test

# E2E (Playwright + ライブバックエンド、9 テスト)
cd frontend && npx playwright test

# 型チェック
cd frontend && npm run type-check
cd backend && mypy app
```

---

## 📊 品質ゲート (CI — 全 7 ジョブ)

| ジョブ            | ツール                    | 基準           |
| ----------------- | ------------------------- | -------------- |
| 🔍 Backend Lint   | Ruff                      | エラー 0       |
| 🧪 Backend Tests  | pytest + PostgreSQL       | 全 35 件通過   |
| 🔍 Frontend Lint  | ESLint (--max-warnings 0) | 警告 0         |
| 🧪 Frontend Tests | vitest v4 + coverage      | 全 8 件通過    |
| 🏗️ Frontend Build | vite build                | 成功           |
| 🔐 Security Scan  | gitleaks                  | シークレット 0 |
| 🎭 E2E            | Playwright + live backend | 全 9 件通過    |

---

## 🔌 主要 API エンドポイント

| エンドポイント                                     | メソッド           | 説明                                      |
| -------------------------------------------------- | ------------------ | ----------------------------------------- |
| `/api/v1/auth/register`                            | POST               | ユーザー登録                              |
| `/api/v1/auth/login`                               | POST               | JWT トークン取得                          |
| `/api/v1/projects`                                 | GET/POST           | プロジェクト一覧・作成                    |
| `/api/v1/projects/{id}/containers`                 | GET/POST           | 情報コンテナ (命名自動検証)               |
| `/api/v1/projects/{id}/containers/{id}/transition` | POST               | 状態遷移                                  |
| **`/api/v1/projects/{id}/naming-rules`**           | **GET/PUT/DELETE** | **プロジェクト別命名規則 CRUD**           |
| `/api/v1/naming/validate`                          | POST               | 命名規則検証 (プロジェクト固有ルール対応) |
| `/api/v1/workflows`                                | POST               | 承認ワークフロー開始                      |
| `/api/v1/workflows/{id}/approvals/{id}/act`        | POST               | 承認アクション                            |
| `/api/v1/uploads`                                  | POST               | ファイルアップロード (MinIO)              |
| `/api/v1/audit-logs`                               | GET                | 監査ログ一覧                              |

完全な API 仕様: http://localhost:8000/api/docs (Swagger UI)

---

## 📁 プロジェクト構造

```
Open-BIM-Information-Platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── containers.py      # CDE 状態管理 (命名自動検証)
│   │   │   ├── naming_rules.py    # ★ プロジェクト別命名規則 CRUD
│   │   │   ├── naming.py          # 命名規則検証 (プロジェクト固有)
│   │   │   ├── workflows.py       # 承認ワークフロー
│   │   │   └── ...
│   │   ├── models/
│   │   │   ├── naming_rule.py     # ★ ProjectNamingRule
│   │   │   └── ...
│   │   ├── schemas/
│   │   │   ├── naming_rule.py     # ★ ReDoS 防止バリデーション
│   │   │   └── ...
│   │   └── services/
│   │       └── naming_validator.py  # ISO 19650 検証エンジン
│   ├── alembic/versions/          # 2 マイグレーション
│   └── tests/                     # 35 テスト
├── frontend/
│   └── src/
│       ├── pages/                 # 9 画面
│       │   ├── ApprovalsPage.tsx  # ★
│       │   ├── ContainerDetailPage.tsx  # ★
│       │   ├── RequirementsPage.tsx     # ★
│       │   └── UploadPage.tsx           # ★
│       ├── components/design/
│       │   └── Primitives.tsx     # ★ StatePill/NamingBadge/Avatar
│       └── lib/
│           ├── designData.ts      # ★ ISO 19650 デモデータ
│           └── fmt.ts             # ★ 日付フォーマット
├── docs/
│   ├── ARCHITECTURE.md
│   ├── OPERATIONS.md
│   └── RELEASE_CHECKLIST.md
├── .github/workflows/ci.yml       # 全 7 ジョブ CI
└── docker-compose.yml
```

---

## 🚀 ロードマップ

### ✅ Sprint 1 (完了)

- [x] 基盤整備 (Docker Compose + FastAPI + React + CI)
- [x] DB モデル設計 (20 テーブル・Alembic)
- [x] 認証 (JWT + bcrypt)
- [x] CDE 状態遷移 API
- [x] 命名規則検証エンジン (ISO 19650-2 Annex A)
- [x] ファイルアップロード API (MinIO)
- [x] 承認ワークフロー API
- [x] 監査ログ API
- [x] E2E テスト基盤 (Playwright)
- [x] セキュリティ強化 (13 件修正)

### ✅ Sprint 2 (完了)

- [x] 命名規則プロジェクト別カスタム設定 API (#3)
- [x] フロントエンド BIM デザインシステム (4 新画面)
- [x] ISO 19650 命名バリデーター UI (リアルタイム)
- [x] セキュリティ修正 3 件 (ReDoS/IDOR/入力検証)
- [x] vitest v4 アップグレード (critical 脆弱性 2 件解消)

### 🔜 Sprint 3 (計画中)

- [ ] OIDC/SAML 認証連携 (Keycloak / Azure AD)
- [ ] MinIO 実サービス統合テスト
- [ ] 通知システム (アプリ内 + メール)
- [ ] レポート出力 (CSV / PDF)
- [ ] 命名規則設定 UI (フロントエンド)
- [ ] GitHub Actions Node.js 24 移行 (期限: 2026-06-16)

---

## 📊 品質メトリクス推移

| 指標                  | Sprint 1 | Sprint 2  | 変化 |
| --------------------- | -------- | --------- | ---- |
| ✅ CI ジョブ          | 7/7      | 7/7       | →    |
| 🧪 テスト合計         | 45 件    | **52 件** | ▲ +7 |
| 🖥️ UI 画面数          | 5        | **9**     | ▲ +4 |
| 🔌 API エンドポイント | ~20      | **~24**   | ▲ +4 |
| 🔐 npm 脆弱性 (high+) | 0        | 0         | →    |
| 🛡️ セキュリティ修正   | 13 件    | **16 件** | ▲ +3 |

---

## 📚 ドキュメント

| ドキュメント                                                    | 内容                                            |
| --------------------------------------------------------------- | ----------------------------------------------- |
| [🏛️ ARCHITECTURE.md](docs/ARCHITECTURE.md)                      | 設計思想・レイヤー構造・CDE状態機械・認可モデル |
| [🛠️ OPERATIONS.md](docs/OPERATIONS.md)                          | デプロイ・ロールバック・監視・バックアップ      |
| [🚀 RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)            | Gate-3 リリース判定・人間サインオフ欄           |
| [📋 要件定義書](Open%20BIM%20情報基盤%20要件定義書.md)          | ISO 19650 業務要件・機能要件                    |
| [📐 詳細仕様書](open-bim-information-platform-detailed-spec.md) | 画面・API・データモデル・状態遷移仕様           |

> 🏁 **リリース状態**: v0.1.0 は **Release Ready（人間サインオフ待ち）**
> CI 全 7 ジョブ green・STABLE 達成 (N=5)・Critical/High 脆弱性 0
> 本番デプロイは [RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) のサインオフ後に人間が手動実行

---

_ISO 19650 準拠 BIM 情報管理 © 2026 — [GitHub](https://github.com/Kensan196948G/Open-BIM-Information-Platform)_
