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
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ $ENV_FILE が見つかりません" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR_OVERRIDE:-${BACKUP_DIR:-$PROJECT_DIR/backups}}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
NETWORK_NAME="${NETWORK_NAME:-bim_platform_net}"
POSTGRES_BACKUP_MODE="${POSTGRES_BACKUP_MODE:-compose}"
MINIO_BACKUP_MODE="${MINIO_BACKUP_MODE:-compose}"
PG_DUMP_BIN="${PG_DUMP_BIN:-pg_dump}"
PSQL_BIN="${PSQL_BIN:-psql}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
  echo "❌ BACKUP_ENCRYPTION_KEY が設定されていません" >&2
  exit 1
fi

if [[ "$MINIO_BACKUP_MODE" != "skip" && "${BACKUP_MAINTENANCE_CONFIRMED:-false}" != "true" ]]; then
  echo "❌ full backupには書込み停止の確認（BACKUP_MAINTENANCE_CONFIRMED=true）が必要です" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
mkdir -p "$BACKUP_DIR"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "🔐 バックアップ開始: $TIMESTAMP"

# PostgreSQL 論理バックアップ
echo "  🐘 PostgreSQL dump ($POSTGRES_BACKUP_MODE)..."
case "$POSTGRES_BACKUP_MODE" in
  compose)
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_dump --no-owner --no-acl \
        -U "${POSTGRES_USER:-bim_user}" "${POSTGRES_DB:-bim_platform}" \
      | gzip > "$TMP_DIR/postgres.sql.gz"
    ;;
  host)
    PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}" \
      "$PG_DUMP_BIN" --no-owner --no-acl \
        --host "${POSTGRES_HOST:-127.0.0.1}" \
        --port "${POSTGRES_PORT:-5432}" \
        --username "${POSTGRES_USER:-bim_user}" \
        --dbname "${POSTGRES_DB:-bim_platform}" \
      | gzip > "$TMP_DIR/postgres.sql.gz"
    ;;
  *)
    echo "❌ POSTGRES_BACKUP_MODE は compose または host を指定してください" >&2
    exit 1
    ;;
esac

# MinIO バケット mirror
echo "  📦 MinIO mirror ($MINIO_BACKUP_MODE)..."
mkdir -p "$TMP_DIR/minio"
MINIO_SCHEME="http"
if [[ "${MINIO_SECURE:-false}" == "true" ]]; then MINIO_SCHEME="https"; fi
BACKUP_KIND="full"
case "$MINIO_BACKUP_MODE" in
  compose)
    MINIO_BACKUP_ENDPOINT="${MINIO_SCHEME}://minio:9000"
    MINIO_NETWORK_ARGS=(--network "$NETWORK_NAME")
    MINIO_BACKUP_USER="${MINIO_ROOT_USER:-${MINIO_ACCESS_KEY:-minioadmin}}"
    MINIO_BACKUP_PASSWORD="${MINIO_ROOT_PASSWORD:-${MINIO_SECRET_KEY:?MINIO password required}}"
    ;;
  host)
    MINIO_BACKUP_ENDPOINT="${MINIO_SCHEME}://${MINIO_ENDPOINT:-127.0.0.1:9000}"
    MINIO_NETWORK_ARGS=(--network host)
    MINIO_BACKUP_USER="${MINIO_ACCESS_KEY:-${MINIO_ROOT_USER:-minioadmin}}"
    MINIO_BACKUP_PASSWORD="${MINIO_SECRET_KEY:-${MINIO_ROOT_PASSWORD:?MINIO password required}}"
    ;;
  skip)
    if [[ "${ALLOW_DB_ONLY_BACKUP:-false}" != "true" ]]; then
      echo "❌ DB-only backup には ALLOW_DB_ONLY_BACKUP=true が必要です" >&2
      exit 1
    fi
    BACKUP_KIND="db-only"
    printf 'MinIO was not included. This is not a complete application backup.\n' \
      > "$TMP_DIR/minio.NOT_INCLUDED"
    ;;
  *)
    echo "❌ MINIO_BACKUP_MODE は compose、host、skip を指定してください" >&2
    exit 1
    ;;
esac

if [[ "$MINIO_BACKUP_MODE" != "skip" ]]; then
  docker run --rm \
    "${MINIO_NETWORK_ARGS[@]}" \
    --user "$(id -u):$(id -g)" \
    -e "MINIO_BACKUP_ENDPOINT=$MINIO_BACKUP_ENDPOINT" \
    -e "MINIO_BACKUP_USER=$MINIO_BACKUP_USER" \
    -e "MINIO_BACKUP_PASSWORD=$MINIO_BACKUP_PASSWORD" \
    -e "BACKUP_TIMESTAMP=$TIMESTAMP" \
    -v "$TMP_DIR/minio:/backup" \
    --entrypoint /bin/sh \
    minio/mc -c \
      'mc --config-dir /tmp/.mc alias set local "$MINIO_BACKUP_ENDPOINT" "$MINIO_BACKUP_USER" "$MINIO_BACKUP_PASSWORD" >/dev/null && mc --config-dir /tmp/.mc mirror --overwrite local/bim-containers "/backup/$BACKUP_TIMESTAMP"'

  echo "  🔎 PostgreSQL / MinIO file integrity..."
  case "$POSTGRES_BACKUP_MODE" in
    compose)
      docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-bim_user}" \
          -d "${POSTGRES_DB:-bim_platform}" -tAc \
          "SELECT DISTINCT storage_key FROM container_files ORDER BY storage_key" \
        > "$TMP_DIR/storage-keys.txt"
      ;;
    host)
      PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}" \
        "$PSQL_BIN" -v ON_ERROR_STOP=1 \
          --host "${POSTGRES_HOST:-127.0.0.1}" \
          --port "${POSTGRES_PORT:-5432}" \
          --username "${POSTGRES_USER:-bim_user}" \
          --dbname "${POSTGRES_DB:-bim_platform}" -tAc \
          "SELECT DISTINCT storage_key FROM container_files ORDER BY storage_key" \
        > "$TMP_DIR/storage-keys.txt"
      ;;
  esac

  MIRROR_DIR="$TMP_DIR/minio/$TIMESTAMP"
  DB_FILE_COUNT=0
  while IFS= read -r STORAGE_KEY; do
    [[ -z "$STORAGE_KEY" ]] && continue
    DB_FILE_COUNT=$((DB_FILE_COUNT + 1))
    if [[ "$STORAGE_KEY" == /* || "$STORAGE_KEY" == *".."* ]]; then
      echo "❌ 不正なstorage_keyを検出しました" >&2
      exit 1
    fi
    if [[ ! -f "$MIRROR_DIR/$STORAGE_KEY" ]]; then
      echo "❌ MinIO objectが不足しています: $STORAGE_KEY" >&2
      exit 1
    fi
  done < "$TMP_DIR/storage-keys.txt"

  MINIO_FILE_COUNT=0
  if [[ -d "$MIRROR_DIR" ]]; then
    MINIO_FILE_COUNT=$(find "$MIRROR_DIR" -type f | wc -l)
  fi
  if [[ "$MINIO_FILE_COUNT" -ne "$DB_FILE_COUNT" ]]; then
    echo "❌ PostgreSQL / MinIO object数が一致しません (DB=$DB_FILE_COUNT MinIO=$MINIO_FILE_COUNT)" >&2
    exit 1
  fi
  echo "  ✅ file objects: $DB_FILE_COUNT"
fi

printf 'backup_kind=%s\npostgres_mode=%s\npostgres_database=%s\nminio_mode=%s\n' \
  "$BACKUP_KIND" "$POSTGRES_BACKUP_MODE" "${POSTGRES_DB:-bim_platform}" "$MINIO_BACKUP_MODE" \
  > "$TMP_DIR/backup-manifest.txt"

# 設定ファイルのスナップショット
echo "  ⚙️  config snapshot..."
cp "$ENV_FILE" "$TMP_DIR/env.snapshot"
cp "$COMPOSE_FILE" "$TMP_DIR/compose.yml"
cp frontend/nginx.conf "$TMP_DIR/nginx.conf" 2>/dev/null || true

# バンドル → 暗号化
echo "  🔒 encrypting bundle..."
BACKUP_PREFIX="backup"
if [[ "$BACKUP_KIND" == "db-only" ]]; then BACKUP_PREFIX="backup-db-only"; fi
tar -czf - -C "$TMP_DIR" . \
  | openssl enc -aes-256-cbc -pbkdf2 -salt \
      -pass env:BACKUP_ENCRYPTION_KEY \
      > "$BACKUP_DIR/$BACKUP_PREFIX-$TIMESTAMP.tar.gz.enc"

# 世代管理。DB-only 実行で完全バックアップを削除してはならない。
if [[ "$BACKUP_KIND" == "full" ]]; then
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'backup-[0-9]*.tar.gz.enc' \
    -mtime +"$RETENTION_DAYS" -delete
else
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'backup-db-only-*.tar.gz.enc' \
    -mtime +"$RETENTION_DAYS" -delete
fi

BACKUP_FILE="$BACKUP_DIR/$BACKUP_PREFIX-$TIMESTAMP.tar.gz.enc"
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ バックアップ完了: $BACKUP_FILE ($SIZE)"
if [[ "$BACKUP_KIND" == "db-only" ]]; then
  echo "⚠️  DB-only: MinIOを含まないため完全バックアップではありません"
fi
echo "   世代保持: 直近 ${RETENTION_DAYS} 日"

# 監視連携ポイント: このスクリプトの exit code と最終行を監視基盤/通知へ送る
