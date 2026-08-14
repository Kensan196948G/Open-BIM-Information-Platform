# MVP / Prototype デモ環境ガイド

> 本ドキュメントは **関係者レビュー用 MVP / Prototype** の起動・操作手順です。
> すべてのデータは**架空のデモデータ**です（実在の人物・企業・案件とは無関係）。
> 本番展開は `docs/PRODUCTION_DEPLOYMENT.md` 参照（2026-08-15 に Cloudflare Tunnel で公開済み）。

---

## 📌 概要

| 項目 | 内容 |
|---|---|
| 目的 | 主要ユースケース（登録・検索・一覧・詳細・承認・通知・監査・RBAC）を一通り操作・評価できる MVP |
| 構成 | FastAPI (backend) + React 19/TS/Vite (frontend) + PostgreSQL 15 + MinIO + Redis |
| データ | 架空デモデータ（`scripts/seed_mvp.py` で再生成可能） |
| ログイン | デモユーザー（下記）・パスワードは全て `DemoPass123!` |
| **公開 URL（レビュー用）** | **https://open-bim-mvp.mirai-dx-platform.com**（Cloudflare Tunnel） |
| 本番 URL | **https://open-bim.mirai-dx-platform.com**（2026-08-15 公開・production モード・架空データのみ） |

---

## 🚀 起動手順（ローカル開発環境）

### 前提

- Docker Compose またはローカルの PostgreSQL 15 / Redis / MinIO
- Python 3.11+（backend）、Node.js 20+（frontend）

### 1. DB マイグレーション

```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://bim_user:bim_password@localhost:5432/bim_mvp"
python -m alembic upgrade head
```

### 2. デモデータ投入（架空データ）

```bash
# 組織2・プロジェクト3・ユーザー8・コンテナ11・承認/通知/要求文書を投入
python ../scripts/seed_mvp.py
```

> 再実行しても安全（冪等）。既存デモユーザーは再利用され、パスワードは毎回 `DemoPass123!` にリセットされます。

### 3. バックエンド起動

```bash
export DATABASE_URL="postgresql+asyncpg://bim_user:bim_password@localhost:5432/bim_mvp" \
  ENVIRONMENT=development \
  SECRET_KEY="開発用の十分に長い秘密鍵（32文字以上）" \
  RATE_LIMIT_BACKEND=memory \
  CORS_ORIGINS="http://localhost:5173"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. フロントエンド起動

```bash
cd frontend
VITE_API_BASE_URL="http://localhost:8000" npm run dev
```

→ ブラウザで **http://localhost:5173** を開く

---

## 🔑 デモユーザー

| メールアドレス | ロール | 所属 | 確認できること |
|---|---|---|---|
| `platform-admin@example.jp` | プラットフォーム管理者 | — | 監査ログ・ユーザー管理 API・全テナント |
| `admin@mirai.example.jp` | 組織管理者 | 未来建設株式会社 | プロジェクト作成・命名規則・承認 |
| `reviewer@mirai.example.jp` | レビューア | 未来建設株式会社 | 承認タスク・承認/差戻し |
| `engineer@mirai.example.jp` | メンバー | 未来建設株式会社 | コンテナ作成・アップロード・共有申請 |
| `chief@ozora.example.jp` | 組織管理者 | おおぞら設計株式会社 | 設計プロジェクト（宮ヶ丘）管理 |
| `designer@ozora.example.jp` | メンバー | おおぞら設計株式会社 | 設計コンテナ作成 |

パスワード（全ユーザー共通）: **`DemoPass123!`**

---

## 🧭 確認できる主要フロー

| # | フロー | 画面 | 手順 |
|---|---|---|---|
| 1 | ログイン | `/login` | デモユーザーでログイン |
| 2 | ダッシュボード | `/` | プロジェクト別 KPI・CDE 分布・承認待ち（実データ） |
| 3 | プロジェクト一覧 | `/projects` | 未来橋架替工事 / 臨海部護岸整備工事（未来建設）、宮ヶ丘複合開発計画（おおぞら設計） |
| 4 | コンテナ一覧・検索 | プロジェクト詳細 | 識別子・タイトル検索、CDE 状態（WIP/Shared/Published/Archived） |
| 5 | コンテナ詳細・改訂履歴 | コンテナ詳細 | 版（P01.01 / P01.02）・改訂履歴・ファイル一覧 |
| 6 | アップロード | `/upload` | コンテナ作成 + ファイルアップロード（実 API） |
| 7 | 承認タスク | `/approvals` | レビューアで「承認」「差戻し」を実行 |
| 8 | 通知 | ヘッダーのベル / `/notifications` | 承認依頼の未読バッジ・既読管理 |
| 9 | 監査ログ | `/audit-logs` | 主要操作の記録（プラットフォーム管理者のみ）・CSV エクスポート |
| 10 | 要求文書 | `/requirements` | EIR / BEP と要求項目の進捗（met/partial/not_met） |
| 11 | RBAC | `/settings/roles` | ロール・権限の管理（実 API） |
| 12 | 設定 | `/settings` | プロフィール・パスワード変更・通知設定・セキュリティ概要 |

### RBAC 権限の実演

- `engineer@mirai.example.jp`（メンバー）が **Shared → Published の承認** を試みると **403** が返ります。
- `reviewer@mirai.example.jp`（レビューア）で承認すると **200** が返り、コンテナが Published になります。

---

## 📊 デモデータの内訳

| 種別 | 件数 | 備考 |
|---|---|---|
| 組織 | 2 | 未来建設株式会社 / おおぞら設計株式会社（すべて架空） |
| プロジェクト | 3 | 未来橋架替工事 / 臨海部護岸整備工事 / 宮ヶ丘複合開発計画 |
| ユーザー | 7 | 各ロール + プラットフォーム管理者 |
| コンテナ | 11 | WIP/Shared/Published/Archived を網羅（図面・モデル・文書） |
| 承認ワークフロー | 各プロジェクトに承認待ち1件 + 完了1件 |
| 通知 | 承認依頼（未読）をレビューアへ |
| 要求文書 | EIR（承認済み）・BEP（レビュー中）+ 要求項目 |

すべて `scripts/seed_mvp.py` で再生成可能。秘密情報・実在データは含みません。

---

## 🧪 品質ゲート（変更時の確認）

```bash
# backend
cd backend && python -m pytest -q            # 全テスト
python -m ruff check app tests               # lint
python -m ruff format --check app tests      # format
python -m mypy app                           # 型

# frontend
cd frontend && npm run type-check && npm run lint && npm run build && npm run test
```

---

## ⚠️ 注意事項

- 本環境は**評価・デモ専用**です。本番データを投入しないでください。
- `ENVIRONMENT=production` にしない限り production 起動ガードは無効です。
- 監査ログは Append-Only（更新・削除不可）です。誤って削除しようとすると DB トリガーで拒否されます。
