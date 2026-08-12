# 改善ログ 2026-08-12（外部評価ハードニング）

## 概要

2026-08-12 の統合評価（`docs/EVALUATION_REPORT.md`）で検出した重大・高優先の問題を
修正した記録。ブランチ: `feat/evaluation-hardening-2026-08`。

## セキュリティ

- **IDOR 修正**: `PATCH /api/v1/projects/{project_id}/containers/{container_id}` に
  `_get_project_or_404` を追加。他組織ユーザーによるコンテナ更新を 404 で拒否
  （実証テスト: クロス組織 PATCH が 200→404 になることを確認）。
- **自己登録制御**: `ALLOW_SELF_REGISTRATION` を追加。本番（ENVIRONMENT=production）では
  `false` を明示しないと起動しない。`POST /auth/register` は無効時に 403。
- **OIDC ドメイン制限**: `OIDC_ALLOWED_DOMAINS` を追加。JIT プロビジョニング時にメール
  ドメインを検証し、許可外は 403（監査ログに記録）。
- **Docker タグ固定**: postgres:15.10-alpine / redis:7.4.2-alpine /
  minio RELEASE.2025-04-22 / clamav:1.6.1 / nginx:1.27-alpine / node:20.19.4 /
  python:3.11.11。
- **worker 数是正**: 本番 Compose の uvicorn を `--workers 1` に変更（in-process
  レート制限との整合。複数 worker 化は Redis 共有ストア実装後）。

## 機能・データ品質

- ファイル一覧 `GET /projects/{p}/containers/{c}/files`。
- ファイル削除 `DELETE .../files/{file_id}`（WIP のみ・オブジェクト+DB+監査ログ）。
- 承認タスク `GET /api/v1/workflows/tasks/mine`（自分の未処理承認+コンテナ/プロジェクト文脈）。
- 監査ログ CSV `GET /api/v1/audit-logs/export.csv`（管理者限定・UTF-8 BOM）。
- ユーザー管理 API `GET/PATCH /api/v1/admin/users`（一覧/検索/有効化/組織割当/自己降格防止）。
- `/metrics`（Prometheus 形式、依存追加なし）。
- プロジェクト内の識別子重複を 409 で拒否。
- コンテナレスポンスに `created_at` / `updated_at` を追加（ダッシュボード用）。

## UI（誤表示・未接続の解消）

- ダッシュボード: 実 API（プロジェクト・コンテナ・承認タスク）から KPI/CDE 分布/承認待ち/
  最近更新/情報分類を表示。モック数値・無効ボタンを削除。
- 承認タスク: 実 API（tasks/mine + act）に接続。承認/差戻し/却下が DB に反映。
- アップロード: 実 API（コンテナ作成+ファイルアップロード）に接続。実ファイル選択・
  種別/情報分類の指定・エラー表示を追加。
- コンテナ詳細: ファイルタブ（一覧・ダウンロード・WIP 削除）。
- 監査ログ: 偽の「ハッシュチェーン検証済み」表示を削除し、実際の仕様
  （Append-Only トリガー）に合わせて修正。CSV エクスポートを実装。
- 設定: プロフィールを実ユーザー、組織タブを実 API ベースに変更。偽メンバー一覧を削除。
- プロジェクト詳細: 偽のコンテナ数・適合率・メンバー・活動履歴を実データ/説明に置換。

## E2E / CI

- `scripts/seed_e2e.py` を追加（org/プロジェクト/ユーザー/コンテナ/承認ワークフローを
  決定的に投入。再実行可能）。
- 承認 E2E を実データベース（seeded data）に書き換え、モック UI 依存を排除。
- CI の E2E ジョブに seed ステップを追加。
- Playwright を `fullyParallel: false` に変更（実データ共有時の決定性確保）。

## 検証結果（ローカル）

- バックエンド: 全テスト合格（件数は最終実行結果を参照）。
- ruff / mypy: 0 エラー。
- フロント: type-check / lint 0 エラー、ビルド成功。
- シード検証: 新規 PostgreSQL に alembic upgrade → seed → ログイン → tasks/mine → 成功。
- 制約: 本ホストの Node/undici Wasm 環境問題によりフロント単体テストと一部ビルドが
  不安定（CI では green）。Playwright は CI で検証予定。

## 残課題

- RBAC のエンドポイント権限強制（ロール⇔API）
- 通知・検索・版管理・データ移行（Phase 1-2）
- 本番環境・Secrets 提供（Issue #31）
