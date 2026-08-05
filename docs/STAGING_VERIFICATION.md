# ステージング検証記録

> 実施日: 2026-08-05
> 環境: 開発ホスト（192.168.0.185）上の本番構成（docker-compose.prod.yml）を専用ポートで分離
> 検証対象コミット: feat/phase0-hardening ブランチ（PR #30 時点）

## 構成

- `docker-compose.prod.yml` + `docker-compose.staging.yml`（ホストポート 8090/8443 のみ公開）
- PostgreSQL / Redis / MinIO / ClamAV / backend / frontend（nginx TLS）
- 自己署名証明書（検証専用）、独立ボリューム、独立ネットワーク `bim_platform_net`
- 本番ガード（production起動時の弱い資格情報拒否）を有効化した状態で起動確認

## スモークテスト結果

| 項目 | 結果 |
|---|---|
| `GET /health`（nginx経由） | ✅ 200 `{"status":"ok","database":"ok","redis":"ok"}` |
| セキュリティヘッダー | ✅ HSTS / X-Content-Type-Options / X-Frame-Options / Referrer-Policy / CSP |
| フロントエンド配信 | ✅ `<title>Open BIM 情報基盤</title>` |
| APIドキュメント `/api/docs` | ✅ 200 |
| ユーザー登録 → ログイン → `/me` → `/projects` | ✅ 一連のフロー成功 |
| 不正パスワードログイン | ✅ 401 |
| refreshトークンローテーション | ✅ 新トークン発行・旧トークン失効 |
| OIDC未設定時のSSO無効化 | ✅ `/auth/oidc/config` → `enabled:false` |

## マイグレーション検証

- 新規PostgreSQLで `alembic upgrade head` 成功（5リビジョン）
- `alembic downgrade base` → `upgrade head` 再実行成功（Enum型の後始末を修正済み）
- 監査ログ immutable トリガー `audit_logs_no_modify` の存在確認
- `docker-compose.prod.yml` に migrate ワンショットサービスを追加し、起動時に自動適用されることを確認

## バックアップ・復元演習

- `scripts/backup.sh` で PostgreSQL dump / MinIO mirror / 設定スナップショットを暗号化バンドル化
- `scripts/restore-drill.sh` で隔離環境（docker-compose.restore.yml）へ復元
- 検証結果:
  - projects=1 / information_containers=1 / container_files=1 / audit_logs=4 を復元
  - 監査ログ immutable トリガー再適用を確認
  - MinIOオブジェクト8件を復元し、先頭ファイルのSHA-256がDBの `checksum_sha256` と一致
  - 所要時間 15秒（RTO目標8時間に対し十分）

## 発見・修正された問題（この検証で検出）

1. production起動ガードが想定通り弱い資格情報・localhost CORSを拒否（仕様動作として確認）
2. 初回起動時にDBマイグレーションが未適用 → migrateワンショットサービスを追加して解消
3. マイグレーション再実行時にトリガー重複で失敗 → 冪等化
4. `downgrade base` 後にEnum型が残存し再upgrade失敗 → downgradeで型を削除
5. 復元演習のクリーンアップが同一ディレクトリのステージングを巻き添えに → 独立プロジェクト名 `bim-restore` に分離
6. Alpineの `wget localhost` がIPv6に接続しhealthcheckが失敗 → `127.0.0.1` に修正
7. backup.sh のMinIO mirrorがroot権限・設定ディレクトリ問題で空になる → 事前ディレクトリ作成と `--user`/`--config-dir` 指定で解消

## 判定

- ステージング品質ゲート: **GO**
- 本番デプロイ: **未実施**（本番環境・ドメイン・Secretsが未確定のため）
