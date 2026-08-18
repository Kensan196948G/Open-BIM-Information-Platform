# 運用台帳

> 定期作業の予定・実績・証跡保存先を記録する。
> **予定の作業を「実施済み」と記録しないこと。** 実績は実施時に日時・担当・結果を追記する。

## 日次

| No | 点検項目 | 担当 | 証跡 | 次回予定 | 実績 |
|---|---|---|---|---|---|
| D1 | バックアップ成功確認（`scripts/backup.sh` exit code / 生成物） | IT担当 | `backups/` と実行ログ | 毎日 02:30 | 未実施 |
| D2 | `/health` 応答・主要画面スモーク | IT担当 | 監視プローブ記録 | 毎日始業時 | 未実施 |
| D3 | エラーログ・認証失敗の確認 | IT担当 | ログ確認記録 | 毎日始業時 | 未実施 |

## 週次

| No | 点検項目 | 担当 | 証跡 | 次回予定 | 実績 |
|---|---|---|---|---|---|
| W1 | ディスク・DB容量・MinIO容量確認 | IT担当 | 容量記録 | 毎週月曜 | 未実施 |
| W2 | 依存監査（npm audit / pip-audit / SBOM）結果確認 | 開発担当 | CI結果 | 毎週月曜 | 未実施 |
| W3 | 証明書有効期限・ドメイン確認 | IT担当 | 期限一覧 | 毎週月曜 | 未実施 |

## 月次

| No | 点検項目 | 担当 | 証跡 | 次回予定 | 実績 |
|---|---|---|---|---|---|
| M1 | アクセス権限棚卸（管理者・サービスアカウント・DBロール） | セキュリティ担当 | 棚卸記録 | 毎月第1営業日 | 未実施 |
| M2 | バックアップ復元試験（隔離環境） | IT担当 | `restore-drill.sh` 出力 | 毎月第1週 | 未実施 |
| M3 | Cloudflare/Neon 使用量・課金・予算アラート確認 | IT担当 | 利用レポート | 毎月第1営業日 | 未実施 |
| M4 | ライセンス・OSS告知・SBOM更新 | 開発担当 | SBOM生成物 | 毎月第1週 | 未実施 |

## 四半期

| No | 点検項目 | 担当 | 証跡 | 次回予定 | 実績 |
|---|---|---|---|---|---|
| Q1 | DR 演習（本番相当データでの復元・RPO/RTO実測） | IT担当 | 演習レポート | 次回: 本番稼働後3か月 | 未実施 |
| Q2 | SLO実績レビュー・アラート閾値見直し | IT/開発 | レビュー議事録 | 本番稼働後3か月 | 未実施 |
| Q3 | パスワード/APIキー/シークレットのローテーション | セキュリティ担当 | ローテーション記録 | 本番稼働後3か月 | 未実施 |

## インシデント記録

| 日時 | 重大度 | 概要 | 原因 | 対処 | 再発防止 | 担当 |
|---|---|---|---|---|---|---|
| 2026-08-18 | High | MVP・本番 URL（open-bim-mvp / open-bim.mirai-dx-platform.com）が HTTP 530 / Error 1033（Cloudflare Tunnel 到達不可） | 各サービス・Tunnel が手動プロセスで起動されており、ホスト再起動等で停止したため | バックエンド（:8030/:8040）・vite preview（:4190/:4191）・cloudflared（MVP/本番）を再起動し、ログイン・API・RBAC 403→200・監査ログまで実ブラウザ相当の curl 検証で復旧確認 | systemd（user）ユニット 6 本（`open-bim-*-{backend,frontend,tunnel}.service`）に移行・enabled（Linger=yes で再起動後も自動起動） | DevOps |

## 検証実績（2026-08-12 追記）

| No | 項目 | 結果 | 証跡 |
|---|---|---|---|
| D1 | バックアップ取得（本番構成ステージング） | ✅ 暗号化バンドル作成（16KB・PG dump 含む） | `/tmp/bim-backups/backup-20260812-222020.tar.gz.enc` |
| D1 | 復元演習（隔離環境） | ✅ projects=1 / containers=3 / audit_logs=55 復元、immutable トリガー確認、所要 13 秒 | `restore-drill.sh` 出力（本ログ） |
| D2 | 本番構成スモーク（ポート分離） | ✅ 全サービス healthy・/health OK・ログイン/一覧/RBAC 403 確認 | 改善ログ 2026-08-12 追記 |
| D2 | 負荷試験（25 ユーザー×8 反復） | ✅ API p50 93〜116ms / p95 160〜285ms・エラー 0。login p50 8.3s（要最適化） | `scripts/smoke_load_test.py` |
| D2 | RBAC 職務分掌確認 | ✅ member の approve → 403 | ステージング API 検証 |
| D2 | 負荷試験（workers=4・Redis共有レート制限） | ✅ login p50 3.45s / p95 4.45s（前回比 2.6 倍改善）、API p95 37〜73ms・エラー 0 | 改善ログ 追記2 |
| D2 | 共有レート制限の実証 | ✅ 4 worker・25 並列 → 200×5 / 429×20（Redis 共有） | ステージング API 検証 |
| D2 | MVP・本番 URL 復旧確認（2026-08-18） | ✅ 両 URL HTTP 200・ログイン（reviewer/engineer/platform-admin）・タスク一覧・通知・監査ログ・未認証 401・権限外 approve 403・正規 approve 200 を Tunnel 経由で確認 | 本ログ（インシデント記録参照） |
| D3 | 運用恒久化（2026-08-18） | ✅ systemd user ユニット 6 本へ移行（enabled・Linger=yes）。`systemctl --user status open-bim-*` で全 active を確認 | `~/.config/systemd/user/open-bim-*.service` |
| D1 | 空 DB への Migration + Seed 再実行（2026-08-18） | ✅ 空の PostgreSQL 15 コンテナ（bim_verify）へ `alembic upgrade head`（22 テーブル）→ `seed_mvp.py` を実行し、2 回目実行でも users=6 / orgs=2 / projects=3 / containers=11 で重複なし（冪等） | 本ログ（コンテナは検証後破棄） |
| D2 | 実ブラウザ a11y・レスポンシブ・キーボード検証（2026-08-18） | ✅ 本番 URL で Playwright（chromium）検証 11/11: title/h1/ラベル付き入力/ボタン名/キーボード Tab 巡回/ログイン→ダッシュボード遷移/ナビ 10 リンク/モバイル 375px・デスクトップ 1440px で横スクロールなし/コンソールエラー 0 | Playwright スクリプト実行ログ（本ログ） |
| D1 | バックアップ取得（2026-08-18 20:12） | ✅ bim_prod・bim_mvp を pg_dump → 暗号化バンドル作成（36KB・AES-256-CBC・世代保持 7 日） | `backups/backup-20260818-201244.tar.gz.enc` |
| D1 | 復元演習（2026-08-18） | ✅ 暗号化バンドルを復号し bim_mvp を分離 PostgreSQL 15 コンテナへ復元 → users=6 / containers=11 / projects=3 を確認 | 本ログ（コンテナは検証後破棄） |
| M3 | Neon 実環境での Migration + Seed 検証（2026-08-18） | ✅ Neon プロジェクト `open-bim-information-platform`（noisy-paper-35107522・us-west-2）を作成し、空の neondb へ `alembic upgrade head`（22 テーブル）→ `seed_mvp.py` 実行 → users=6 / orgs=2 / projects=3 / containers=11 / notifications=3 を確認。さらに一時バックエンドで同 DB にログイン・承認タスク取得が動作（DB 接続の実証） | Neon コンソール + 本ログ |

> 備考: SSH デプロイ Secrets（PROD_*）・監視通知先は引き続き人間の提供待ち（Issue #31）。
> 本番 DB の Neon 移行は、本検証を踏まえ Human Gate 承認後に実施可能。
