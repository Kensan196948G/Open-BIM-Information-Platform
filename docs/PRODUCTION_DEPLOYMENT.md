# 本番デプロイ Runbook

> **2026-08-15 更新: 本番 URL を Cloudflare Tunnel で公開済み**（`https://open-bim.mirai-dx-platform.com`）。
> 現状の構成: ローカルホスト + Cloudflare Tunnel（production モード・架空デモデータのみ）。
> SSH ホストへの deploy.yml 経由デプロイは Secrets 提供後に実施可能。

## 1. 前提条件チェックリスト

- [ ] 本番ドメイン（例: `open-bim.mirai-dx-platform.com`）とDNS（A/Tunnelレコード）
- [ ] TLS証明書（Let's Encrypt等。nginxは `certs/fullchain.pem` / `certs/privkey.pem` を参照）
- [ ] 本番ホスト（VM/オンプレ）とSSH接続・Docker Compose v2.24+・`!override`対応
- [ ] 本番DB（Neonプロジェクトまたは自前PostgreSQL 15+）
- [ ] 本番用 `.env`（`.env.production.example` を雛形に強力な値で作成）
- [ ] GitHub Actions Secrets: `PROD_HOST` / `PROD_USER` / `PROD_SSH_KEY` / `PROD_DIR`
- [ ] バックアップ保存先（別障害ドメイン）と `BACKUP_ENCRYPTION_KEY`
- [ ] 監視通知先（Webhook/メール）と一次対応担当者

## 2. 環境作成（Neon利用時）

```bash
# プロジェクト作成（プロジェクト名は一意に特定できるものに）
neonctl projects create --name open-bim-information-platform --org-id <org-id>
# ブランチ・DB・ロール・接続文字列を取得し、本番 .env の DATABASE_URL に設定
neonctl connection-string --project-id <project-id> --branch main --role bim_user
```

> **2026-08-18 実証済み**: Neon プロジェクト `open-bim-information-platform`
> （project id `noisy-paper-35107522`・us-west-2）を作成し、空の `neondb` に対して
> `CREATE EXTENSION uuid-ossp / pg_trgm` ＋ `prevent_audit_log_modification()` 関数の適用 →
> `alembic upgrade head`（22 テーブル）→ `scripts/seed_mvp.py`（users=6 / orgs=2 / projects=3 /
> containers=11）まで確認済み。アプリの一時起動でもログイン・承認タスク取得が動作。
> 接続文字列は `postgresql+asyncpg://...?...&sslmode=require` 形式で利用する。

自前PostgreSQLの場合は `docker-compose.prod.yml` の postgres サービスを使用する。

### バックアップ（Tunnel/ホスト PostgreSQL 構成時）

`scripts/backup.sh` は docker 構成（bim_postgres コンテナ）向けのため、ホスト PostgreSQL で
運用している間は以下の手順で日次バックアップする（`BACKUP_ENCRYPTION_KEY` は `.env.production` を source）：

```bash
set -a; source .env.production; set +a
TS=$(date +%Y%m%d-%H%M%S); TMP=$(mktemp -d)
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -d bim_prod | gzip > "$TMP/bim_prod.sql.gz"
PGPASSWORD=bim_password pg_dump -h 127.0.0.1 -U bim_user -d bim_mvp | gzip > "$TMP/bim_mvp.sql.gz"
tar -czf - -C "$TMP" . | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_ENCRYPTION_KEY > "backups/backup-$TS.tar.gz.enc"
rm -rf "$TMP"   # 世代管理: 7 日より古い backup-*.tar.gz.enc を削除
```

復元は `openssl enc -d ... | tar -xzO ./bim_<env>.sql.gz | gunzip | psql ...` で実施
（2026-08-18 に分離コンテナへの復元演習済み: users=6 / containers=11 / projects=3）。

## 3. GitHub Secrets 設定

> 2026-08-12 時点: `production` 環境は作成済み（デプロイ承認ゲートの土台）。
> Secrets は未設定（`gh secret list` 空）。以下のコマンドで設定する。

```bash
gh secret set PROD_HOST
gh secret set PROD_USER
gh secret set PROD_SSH_KEY < key.pem
gh secret set PROD_DIR
```

`production` 環境に「必要なレビュアー」を追加すると、本番デプロイに人間承認が必要になる
（推奨: 技術責任者・セキュリティ担当 各1名）。

```bash
# 例: 承認者（ユーザー名）を指定
gh api -X PUT repos/Kensan196948G/Open-BIM-Information-Platform/environments/production \
  -f reviewers='[{"type":"User","id":<user-id>}]' 2>/dev/null || echo "レビュアー設定はWeb UIでも可"
```

### Cloudflare Pages（検証/公開基盤）作成手順（承認後）

```bash
wrangler pages project create open-bim
# デプロイ（プレビューURLは open-bim.pages.dev で即利用可）
wrangler pages deploy frontend/dist --project-name open-bim
# 本番ドメイン（例: open-bim.mirai-dx-platform.com）は Cloudflare ゾーンのDNS追加後に
# Pages > Custom domains で設定
```

### Neon PostgreSQL（DB正本）作成手順（承認後）

```bash
neonctl projects create --name open-bim-information-platform \
  --org-id org-little-violet-74140600
neonctl connection-string --project-id <project-id> --branch main --role bim_user
```

接続文字列は `DATABASE_URL` として本番 `.env` と GitHub Secrets に設定する。

## 4. デプロイ

### 手動（ホスト上）

```bash
cp .env.production.example .env   # 強力な値に編集
./scripts/deploy.sh local origin/main
```

### GitHub Actions（準備済みワークフロー）

- Actions → Deploy Production → workflow_dispatch で実行
- `environment: production` が設定されており、Secrets未設定時は安全に失敗する

### デプロイ後スモーク

```bash
curl -f https://<domain>/health  # liveness
curl -f https://<domain>/ready   # DB/Redis/Storage/AV release readiness
curl -ksI https://<domain>/ | grep -i content-security-policy
```

### 公開環境の常駐化（systemd user ユニット、2026-08-18 導入）

本番・MVP の各サービスは systemd（user）ユニットで常駐化している（`Linger=yes` で再起動後も自動起動）。

```bash
systemctl --user status open-bim-{mvp,prod}-{backend,frontend,tunnel}.service
journalctl --user -u open-bim-prod-backend.service -f   # 本番ログ
systemctl --user restart open-bim-prod-backend.service  # 更新反映
```

- ユニット定義: `~/.config/systemd/user/open-bim-*.service`
- 環境変数: 本番 = `.env.production` / MVP = `~/.config/open-bim/mvp.env`（0600）
- 構成: vite preview（MVP :4190 / 本番 :4191）→ /api プロキシ → uvicorn（MVP :8030 / 本番 :8040）→ Cloudflare Tunnel
- 手動プロセスで起動しないこと（再起動時に停止し HTTP 530 になるため）

## 5. ロールバック

```bash
./scripts/deploy.sh rollback <previous-stable-tag>
```

DBマイグレーションのロールバックは `alembic downgrade -1`（`docs/INCIDENT_RUNBOOK.md` 参照）。

## 6. 監視・運用開始

```bash
# cron / systemd timer で日次実行
MONITOR_READY_URL=https://<domain>/ready ./scripts/monitor.sh
```

- 障害時の一次確認: `curl -f https://open-bim.mirai-dx-platform.com/ready` →
  失敗時は `systemctl --user status open-bim-*` と `journalctl --user -u open-bim-*` で確認

- `docs/OPS_LEDGER.md` の日次/週次/月次/四半期項目を担当者へ割当
- `docs/SLI_SLO.md` の通知試験・SLO計測を開始
- 初回バックアップ取得と復元演習（本番データ）を実施し記録
