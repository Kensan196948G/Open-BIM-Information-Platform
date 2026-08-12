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

---

# 追記（2026-08-12 夜間: Phase 1 スライス実施）

## 1. RBAC エンドポイント権限強制（Issue #36）

- `app/services/rbac.py` を追加。システムロール（member / reviewer / org_admin）と
  権限コードを定義し、`has_permission` / `require_permission` を実装。
- シードマイグレーション（9a8b7c6d5e4f）: 17 権限・3 システムロール・41 紐付けを
  冪等に投入（PostgreSQL で upgrade→downgrade→upgrade 検証済み）。
- 適用エンドポイント:
  - コンテナ: create/update/submit/approve/return/revise/archive
  - ファイル: upload/delete
  - ワークフロー: start（act は担当者割当ベースの従来制御を維持）
  - プロジェクト: create/update（組織管理者以上）
  - 命名規則: manage（組織管理者以上）
  - 要求文書: read / manage
- 職務分掌: member は approve/return/archive 不可（403）。テスト
  `test_rbac_enforcement.py` で分離を実証。
- 既存テストはロールを明示（reviewer / org_admin）する形に更新。

## 2. アプリ内通知（Issue #34 垂直スライス）

- `notifications` テーブル＋API:
  - GET /api/v1/notifications（一覧・未読件数）
  - POST /api/v1/notifications/{id}/read
  - POST /api/v1/notifications/read-all
- 通知トリガー: ワークフロー開始（承認者へ依頼）、承認結果（発議者へ）、
  コンテナ状態変更（作成者へ）。
- UI: ヘッダーのベルアイコンに未読バッジ、/notifications ページ（既読/全既読）。
- テスト 3 件（発火・既読・ユーザースコープ）。

## 3. 検索と版管理（Issue #37 スライス）

- 検索: `GET /projects/{id}/containers?q=`（識別子/タイトル部分一致）、
  `GET /projects/{id}/requirements?q=`。ContainersPage に検索ボックス接続。
- 版管理: アップロード時に `ContainerRevision`（revision_code=P01,
  version_code=P01.01, P01.02…）を自動記録し、ファイルと紐付け。
  `GET /containers/{id}/revisions` で履歴取得。コンテナ詳細の「改訂履歴」タブを実データ化。
- テスト 3 件（検索 2・リビジョン 1）。

## 4. 検証（本番構成ステージング・QA）

- 本番 Compose（docker-compose.prod.yml + ポート分離オーバーレイ、.env.staging に
  `DEBUG=false` / `ALLOW_SELF_REGISTRATION=false` を追記）をローカルで起動。
  PostgreSQL / Redis / MinIO / ClamAV / migrate / backend / frontend 全 healthy。
- 発見・修正: migrate/backend サービスに `ALLOW_SELF_REGISTRATION` の引き渡しがなく
  起動ガードで失敗 → compose に必須 env として追加。
- スモーク: /health OK・ログイン・/me・プロジェクト一覧・RBAC（member approve → 403）確認。
- 負荷試験（scripts/smoke_load_test.py、25 ユーザー×8 反復）:
  - login p50 8.3s / p95 11.5s（bcrypt cost 12 + workers=1 + 共有ホストの CPU 競合。
    本番では Redis 共有レート制限と workers 増、または bcrypt ラウンド調整を要検討）
  - projects/tasks/notifications p50 約 93〜116ms / p95 約 160〜285ms、エラー 0
  - ログイン 25 並列時のレート制限（デフォルト 5/60s/IP）が意図通り動作することを確認
- バックアップ→復元演習: backup.sh で暗号化バンドル作成 → restore-drill.sh で
  projects=1 / containers=3 / audit_logs=55 復元・immutable トリガー確認・所要 13 秒。

## 残課題（Phase 1 次スライス）

- メール通知（Exchange Online/SMTP）と通知設定 UI
- 検索の全文検索化（pg_trgm 類似度・ファイル名検索）
- リビジョン確定（approve 時）と差分表示・変更理由の入力 UI
- パフォーマンス: Redis 共有レート制限 + workers 増、負荷試験の本番相当実施
