# 🏗️ Open BIM 情報基盤

> **ISO 19650 準拠 BIM 情報管理プラットフォーム**
> Common Data Environment (CDE) 状態管理・監査証跡・要求文書管理を統合した Web システム

[![CI](https://github.com/kensan1969/Open-BIM-Information-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/kensan1969/Open-BIM-Information-Platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![ISO 19650](https://img.shields.io/badge/ISO-19650-green)

---

## 📌 概要

| 項目              | 内容                                  |
| ----------------- | ------------------------------------- |
| 🌐 提供形態       | Web ベース統合システム                |
| 📐 準拠規格       | ISO 19650-1/2/5                       |
| 🗄️ バックエンド   | FastAPI (Python 3.11) + PostgreSQL 15 |
| 🖥️ フロントエンド | React 18 + TypeScript + Vite          |
| 🔐 認証           | JWT + OIDC 対応準備済み               |
| 📦 ファイル管理   | MinIO (S3 互換)                       |
| 🐳 インフラ       | Docker Compose                        |

---

## 🗺️ アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│  Browser (React 18 + TypeScript + Vite)         │
│  ・ダッシュボード  ・プロジェクト管理            │
│  ・情報コンテナ CDE  ・監査ログ                  │
└────────────────────┬────────────────────────────┘
                     │ HTTP / REST
┌────────────────────▼────────────────────────────┐
│  FastAPI (Python 3.11)                           │
│  /api/v1/auth  /api/v1/projects                 │
│  /api/v1/containers  /api/v1/audit-logs         │
└──┬──────────┬──────────┬──────────┬─────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
PostgreSQL  Redis     MinIO     Alembic
(メタDB)  (キャッシュ) (ファイル) (マイグレーション)
```

---

## 🎬 主要機能

### 📂 CDE 状態管理

```
WIP ──submit──▶ Shared ──approve──▶ Published ──archive──▶ Archived
      ◀──return──          (差戻し可)
```

| 状態         | 説明         | 編集 | 公開     |
| ------------ | ------------ | ---- | -------- |
| 🔵 WIP       | 作業中       | ✅   | ❌       |
| 🟦 Shared    | レビュー中   | ❌   | 限定     |
| 🟢 Published | 承認済み公開 | ❌   | ✅       |
| 🟡 Archived  | 保管済み     | ❌   | 参照のみ |

### 🔒 セキュリティ統制

- 情報分類: `public / limited / confidential / restricted`
- 監査ログ: 改ざん防止 (Append-Only) + PostgreSQL トリガー
- RBAC: ISO 19650 契約ロールベース権限管理

### 📋 要求文書管理

- OIR / AIR / PIR / EIR / BEP / MIDP / TIDP 対応
- 要求事項明細: **何を / いつ / どのように / 誰のために**

---

## 🛠️ セットアップ

### 前提条件

- Docker & Docker Compose v2.x
- Git

### クイックスタート

```bash
# 1. リポジトリクローン
git clone https://github.com/kensan1969/Open-BIM-Information-Platform.git
cd Open-BIM-Information-Platform

# 2. 環境変数設定
cp .env.example .env
# .env を編集して SECRET_KEY 等を設定

# 3. 起動
docker compose up -d

# 4. DB マイグレーション
docker compose exec backend alembic upgrade head

# 5. アクセス
# フロントエンド: http://localhost:5173
# API ドキュメント: http://localhost:8000/api/docs
# MinIO コンソール: http://localhost:9001
```

### ローカル開発（Docker なし）

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
# Backend
cd backend
pytest -v

# Frontend
cd frontend
npm test

# 型チェック
npm run type-check
```

---

## 📊 品質ゲート (CI)

| チェック   | ツール          | 基準           |
| ---------- | --------------- | -------------- |
| Lint       | Ruff            | エラー 0       |
| 型チェック | mypy / tsc      | エラー 0       |
| テスト     | pytest / vitest | 全通過         |
| ビルド     | vite build      | 成功           |
| Security   | gitleaks        | シークレット 0 |

---

## 📁 プロジェクト構造

```
Open-BIM-Information-Platform/
├── backend/              # FastAPI アプリ
│   ├── app/
│   │   ├── api/v1/      # REST エンドポイント
│   │   ├── models/      # SQLAlchemy モデル
│   │   ├── schemas/     # Pydantic スキーマ
│   │   ├── core/        # 設定・認証・依存性
│   │   └── db/          # DB 接続
│   ├── alembic/         # マイグレーション
│   └── tests/           # pytest テスト
├── frontend/             # React アプリ
│   └── src/
│       ├── pages/       # 画面コンポーネント
│       ├── components/  # 共通コンポーネント
│       ├── hooks/       # カスタムフック
│       ├── lib/         # API クライアント
│       └── types/       # TypeScript 型定義
├── infra/               # インフラ設定
├── .github/workflows/   # CI/CD
└── docker-compose.yml
```

---

## 🚀 ロードマップ

- [x] 基盤整備 (Docker Compose + FastAPI + React)
- [x] DB モデル設計 (ISO 19650 対応)
- [x] 認証 (JWT)
- [x] CDE 状態遷移 API
- [x] CI/CD (GitHub Actions)
- [ ] ファイルアップロード (MinIO)
- [ ] 命名規則検証エンジン
- [ ] 承認ワークフロー
- [ ] OIDC/SAML 連携
- [ ] E2E テスト (Playwright)

---

_ISO 19650 準拠 BIM 情報管理 © 2026_
