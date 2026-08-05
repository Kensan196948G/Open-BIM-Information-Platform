#!/usr/bin/env bash
#
# backup.sh — Open BIM Information Platform 日次バックアップ
#
# 前提:
#   - docker compose (本番構成: docker-compose.prod.yml)
#   - .env に POSTGRES_USER / POSTGRES_DB / POSTGRES_PASSWORD / MINIO_ROOT_USER / MINIO_ROOT_PASSWORD
#   - BACKUP_DIR (デフォルト ./backups)
#   - BACKUP_ENCRYPTION_KEY (AES-256-CBC のパスフレーズ、32文字以上推奨)
#   - openssl / tar / gzip
#
# 使い方:
#   BACKUP_ENCRYPTION_KEY='...' ./scripts/backup.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
NETWORK_NAME="${NETWORK_NAME:-bim_platform_net}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
TMP_DIR="$(mktemp -d)"

if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
  echo "❌ BACKUP_ENCRYPTION_KEY が設定されていません" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "❌ .env が見つかりません" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "🔐 バックアップ開始: $TIMESTAMP"

# PostgreSQL 論理バックアップ
echo "  🐘 PostgreSQL dump..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-bim_user}" "${POSTGRES_DB:-bim_platform}" \
  | gzip > "$TMP_DIR/postgres.sql.gz"

# MinIO バケット mirror
echo "  📦 MinIO mirror..."
docker run --rm \
  --network "$NETWORK_NAME" \
  -e "MC_HOST_local=http://${MINIO_ROOT_USER:-minioadmin}:${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD required}@minio:9000" \
  -v "$TMP_DIR/minio:/backup" \
  minio/mc mirror --overwrite local/bim-containers "/backup/$TIMESTAMP"

# 設定ファイルのスナップショット
echo "  ⚙️  config snapshot..."
cp .env "$TMP_DIR/env.snapshot"
cp "$COMPOSE_FILE" "$TMP_DIR/compose.yml"
cp frontend/nginx.conf "$TMP_DIR/nginx.conf" 2>/dev/null || true

# バンドル → 暗号化
echo "  🔒 encrypting bundle..."
tar -czf - -C "$TMP_DIR" . \
  | openssl enc -aes-256-cbc -pbkdf2 -salt \
      -pass env:BACKUP_ENCRYPTION_KEY \
      > "$BACKUP_DIR/backup-$TIMESTAMP.tar.gz.enc"

# 世代管理（日次）
find "$BACKUP_DIR" -name 'backup-*.tar.gz.enc' -mtime +"$RETENTION_DAYS" -delete

SIZE=$(du -h "$BACKUP_DIR/backup-$TIMESTAMP.tar.gz.enc" | cut -f1)
echo "✅ バックアップ完了: $BACKUP_DIR/backup-$TIMESTAMP.tar.gz.enc ($SIZE)"
echo "   世代保持: 直近 ${RETENTION_DAYS} 日"

# 監視連携ポイント: このスクリプトの exit code と最終行を監視基盤/通知へ送る
