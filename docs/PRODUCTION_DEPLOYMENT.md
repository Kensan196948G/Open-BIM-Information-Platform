# 本番デプロイ Runbook

> 本番環境の提供を受けた後の実施手順。**本番環境は2026-08-05時点で未確定**のため、
> この手順は準備済みであり、実行は環境確定後に行う。

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

自前PostgreSQLの場合は `docker-compose.prod.yml` の postgres サービスを使用する。

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
curl -f https://<domain>/health
curl -ksI https://<domain>/ | grep -i content-security-policy
```

## 5. ロールバック

```bash
./scripts/deploy.sh rollback <previous-stable-tag>
```

DBマイグレーションのロールバックは `alembic downgrade -1`（`docs/INCIDENT_RUNBOOK.md` 参照）。

## 6. 監視・運用開始

```bash
# cron / systemd timer で日次実行
MONITOR_HEALTH_URL=https://<domain>/health ./scripts/monitor.sh
```

- `docs/OPS_LEDGER.md` の日次/週次/月次/四半期項目を担当者へ割当
- `docs/SLI_SLO.md` の通知試験・SLO計測を開始
- 初回バックアップ取得と復元演習（本番データ）を実施し記録
