# 🛠️ 運用手順書 — Open BIM 情報基盤

> ISO 19650 準拠支援 BIM 情報管理プラットフォームの運用・デプロイ・障害対応手順
> （第三者による適合性評価・認証は未取得）

---

## 📌 目次

1. [システム構成](#-システム構成)
2. [デプロイ手順](#-デプロイ手順)
3. [ロールバック手順](#-ロールバック手順)
4. [監視・ヘルスチェック](#-監視ヘルスチェック)
5. [バックアップ・リストア](#-バックアップリストア)
6. [障害対応](#-障害対応)
7. [セキュリティ運用](#-セキュリティ運用)

---

## 🗺️ システム構成

| サービス    | ポート      | 役割                  | ヘルスチェック           |
| ----------- | ----------- | --------------------- | ------------------------ |
| 🖥️ frontend | 5173 / 80   | React SPA             | `GET /`                  |
| 🗄️ backend  | 8000        | FastAPI               | `GET /health` / `GET /ready` |
| 🐘 postgres | 5432        | メタデータDB          | `pg_isready`             |
| 🔴 redis    | 6379        | キャッシュ/セッション | `redis-cli ping`         |
| 📦 minio    | 9000 / 9001 | ファイルストレージ    | `GET /minio/health/live` |

---

## 🚀 デプロイ手順

### 前提条件

- Docker & Docker Compose v2.x
- `.env` ファイル作成済み（本番値設定）
- DNS / TLS 証明書設定済み（リバースプロキシ側）

### ステップ

```bash
# 1. 最新コードを取得
git fetch origin
git checkout <release-tag>   # 例: v0.1.0

# 2. 環境変数を本番値で設定（重要）
cp .env.example .env
vi .env
#   - SECRET_KEY: openssl rand -hex 32 で生成した値
#   - POSTGRES_PASSWORD: 強固なパスワード
#   - MINIO_ROOT_PASSWORD: 強固なパスワード
#   - CORS_ORIGINS: 本番フロントエンドURL
#   - ENVIRONMENT: production

# 3. イメージビルド（本番は production Compose を使用）
docker compose -f docker-compose.prod.yml build

# 4. DB マイグレーション（バックエンド起動前）
docker compose -f docker-compose.prod.yml up -d postgres redis minio
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 5. 監査ログ immutable トリガーは alembic upgrade head で適用される
#    （初回のみ init.sql で関数定義も適用）
docker compose -f docker-compose.prod.yml exec postgres psql -U bim_user -d bim_platform -f /docker-entrypoint-initdb.d/init.sql

# 6. 全サービス起動
docker compose -f docker-compose.prod.yml up -d

# 7. ヘルスチェック確認
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ready
# → {"status":"ok","version":"0.1.0"}
```

### デプロイ後確認チェックリスト

- [ ] `GET /health` が200を返す（liveness）
- [ ] `GET /ready` が200を返し、DB/Redis/Storage/AVがready
- [ ] `GET /api/docs` で OpenAPI ドキュメントが表示される
- [ ] フロントエンドのログイン画面が表示される
- [ ] テストユーザーでログイン → ダッシュボード遷移
- [ ] 監査ログに起動イベントが記録される
- [ ] MinIO コンソール（:9001）にアクセスできる

---

## ⏪ ロールバック手順

### コードのロールバック

```bash
# 1. 直前の安定タグに戻す
git checkout <previous-stable-tag>

# 2. 再ビルド・再起動
docker compose build backend frontend
docker compose up -d backend frontend
```

### DB マイグレーションのロールバック

```bash
# 1つ前のリビジョンへ
docker compose run --rm backend alembic downgrade -1

# 特定リビジョンへ
docker compose run --rm backend alembic downgrade <revision_id>

# マイグレーション履歴確認
docker compose run --rm backend alembic history
docker compose run --rm backend alembic current
```

> ⚠️ **注意**: `audit_logs` テーブルは immutable トリガーで保護されており、
> DELETE/UPDATE は拒否される。ロールバック時もログは保持される（これは仕様）。

### ロールバック判断基準

| 症状                 | 対応                              |
| -------------------- | --------------------------------- |
| `GET /health` が 503 | process/DBを確認し、必要なら即時コードロールバック |
| `GET /ready` が 503 | responseのdependency項目を確認し、deployを停止 |
| マイグレーション失敗 | `alembic downgrade -1` で復旧     |
| データ不整合検出     | サービス停止 → DB リストア → 調査 |

---

## 📊 監視・ヘルスチェック

```bash
# 全サービス状態
docker compose ps

# バックエンドログ（構造化ログ structlog）
docker compose logs -f backend

# DB 接続数確認
docker compose exec postgres psql -U bim_user -d bim_platform \
  -c "SELECT count(*) FROM pg_stat_activity;"

# ヘルスチェックエンドポイント
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### 監視すべきメトリクス

| メトリクス           | 閾値          | アクション     |
| -------------------- | ------------- | -------------- |
| `/health` 応答時間   | > 1s          | 調査           |
| DB 接続数            | > 80% of pool | プール拡張検討 |
| MinIO ディスク使用率 | > 80%         | 容量追加       |
| 5xx エラー率         | > 1%          | 即時調査       |

---

## 💾 バックアップ・リストア

### PostgreSQL バックアップ

```bash
# 論理バックアップ（日次推奨）
docker compose exec postgres pg_dump -U bim_user bim_platform \
  | gzip > backup_$(date +%Y%m%d).sql.gz

# リストア
gunzip -c backup_YYYYMMDD.sql.gz \
  | docker compose exec -T postgres psql -U bim_user bim_platform
```

### MinIO バックアップ

```bash
# mc (MinIO Client) でミラー
mc mirror local/bim-containers /backup/minio/$(date +%Y%m%d)/
```

> 📋 **監査要件**: ISO 19650 準拠のため、監査ログ・改訂履歴は
> 保管期間（プロジェクト設定）満了まで削除禁止。バックアップも同期間保持。

---

## 🚨 障害対応

### 障害レベル定義

| レベル | 定義                       | 初動                           |
| ------ | -------------------------- | ------------------------------ |
| 🔴 P1  | 全サービス停止・データ損失 | 即時ロールバック + DB リストア |
| 🟠 P2  | 一部機能停止               | 該当サービス再起動 → 調査      |
| 🟡 P3  | 性能劣化・軽微なバグ       | 次リリースで修正               |

### よくある障害と対処

| 症状                     | 原因候補                           | 対処                                                     |
| ------------------------ | ---------------------------------- | -------------------------------------------------------- |
| backend が起動しない     | DB 未起動 / マイグレーション未実行 | `docker compose up -d postgres` → `alembic upgrade head` |
| ファイルアップロード 503 | MinIO 未起動                       | `docker compose restart minio`                           |
| ログイン 401 連発        | SECRET_KEY 不一致                  | `.env` の SECRET_KEY 確認                                |
| 監査ログ書込エラー       | トリガー誤設定                     | init.sql のトリガー定義確認                              |

---

## 🔐 セキュリティ運用

- **シークレット管理**: `.env` は git 管理外。本番は Vault / Secrets Manager 推奨
- **TLS**: リバースプロキシ（nginx 等）で TLS 終端。バックエンドは内部通信のみ
- **監査ログ監視**: 認証失敗・権限変更イベントを定期レビュー
- **依存更新**: 月次で `npm audit` / `pip-audit` 実行、Critical/High は即対応
- **バックアップ暗号化**: バックアップファイルは暗号化保存
- **マルウェア対策**: 本番ComposeのClamAVでアップロードをスキャン。EICAR検証は
  `./scripts/av-eicar-test.sh`（詳細は `docs/ADR/ADR-003-malware-scanning.md`）
- **SSO/MFA**: OIDC設定後はIdP側の条件付きアクセスでMFAを強制
  （詳細は `docs/ADR/ADR-001-sso-mfa.md`）
- **バックアップ/復元**: `scripts/backup.sh`（日次）と `scripts/restore-drill.sh`（四半期）
  （詳細は `docs/BACKUP_RESTORE.md`）

---

## 📞 エスカレーション

1. P1 障害 → 即時ロールバック実施 → インシデント記録作成
2. データ整合性疑い → サービス停止判断 → DB スナップショット取得
3. セキュリティインシデント → アクセス遮断 → 監査ログ保全

---

_最終更新: 2026-05-31 / Sprint 1_
