#!/usr/bin/env bash
#
# restore-drill.sh — 隔離環境への復元演習（バックアップが読めることの証明）
#
# 使い方:
#   BACKUP_ENCRYPTION_KEY='...' ./scripts/restore-drill.sh ./backups/backup-YYYYmmdd-HHMMSS.tar.gz.enc
#
# 実施内容:
#   1) 復号・展開
#   2) 隔離用 PostgreSQL / MinIO を起動（docker-compose.restore.yml）
#   3) DB リストア / MinIO mirror
#   4) 件数・監査トリガー・全ファイルSHA-256 を検証
#   5) RPO/RTO 相当時間を出力
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

BACKUP_FILE="${1:?使い方: restore-drill.sh <backup-file.tar.gz.enc>}"
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "❌ バックアップファイルが見つかりません: $BACKUP_FILE" >&2
  exit 1
fi

if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
  echo "❌ BACKUP_ENCRYPTION_KEY が設定されていません" >&2
  exit 1
fi

START_TS="$(date +%s)"
TMP_DIR="$(mktemp -d)"
cleanup() {
  echo "🧹 隔離環境を停止します..."
  docker compose -f docker-compose.restore.yml down --volumes >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "🔓 復号・展開: $BACKUP_FILE"
openssl enc -d -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_ENCRYPTION_KEY \
  -in "$BACKUP_FILE" | tar -xzf - -C "$TMP_DIR"

echo "🚀 隔離環境を起動..."
docker compose -f docker-compose.restore.yml up -d --wait postgres minio

echo "💾 PostgreSQL リストア..."
gunzip -c "$TMP_DIR/postgres.sql.gz" \
  | docker compose -f docker-compose.restore.yml exec -T postgres \
      psql -v ON_ERROR_STOP=1 -U bim_user -d bim_platform

DB_ONLY=false
if [[ -f "$TMP_DIR/minio.NOT_INCLUDED" ]]; then DB_ONLY=true; fi
DB_FILE_COUNT=$(docker compose -f docker-compose.restore.yml exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U bim_user -d bim_platform -tAc \
  "SELECT count(*) FROM container_files" | tr -d '[:space:]')
[[ "$DB_FILE_COUNT" =~ ^[0-9]+$ ]] || {
  echo "❌ container_files件数を取得できません: $DB_FILE_COUNT" >&2
  exit 1
}

echo "📦 MinIO mirror..."
MINIO_SRC_DIR="$(find "$TMP_DIR/minio" -mindepth 1 -maxdepth 1 -type d | head -1 || true)"
if [[ -z "$MINIO_SRC_DIR" ]]; then
  if [[ "$DB_ONLY" == "false" && "$DB_FILE_COUNT" -gt 0 ]]; then
    echo "❌ 完全バックアップにMinIO objectがありません (DB=$DB_FILE_COUNT)" >&2
    exit 1
  fi
  echo "  ⚠️  MinIOバックアップ対象なし"
else
  docker run --rm \
    --network bim_platform_restore_net \
    -e "MC_HOST_restore=http://minioadmin:minioadmin123@minio:9000" \
    minio/mc --config-dir /tmp/.mc mb --ignore-existing restore/bim-containers
  docker run --rm \
    --network bim_platform_restore_net \
    -e "MC_HOST_restore=http://minioadmin:minioadmin123@minio:9000" \
    -v "$TMP_DIR/minio:/backup:ro" \
    minio/mc --config-dir /tmp/.mc mirror --overwrite "/backup/$(basename "$MINIO_SRC_DIR")" restore/bim-containers
fi

echo "🔎 検証: レコード件数"
for TABLE in projects information_containers container_files requirements_documents audit_logs revoked_tokens; do
  COUNT=$(docker compose -f docker-compose.restore.yml exec -T postgres \
    psql -U bim_user -d bim_platform -tAc "SELECT count(*) FROM $TABLE" || echo "N/A")
  echo "  $TABLE: $COUNT"
done

echo "🔎 検証: 監査ログ immutable トリガー"
TRIGGER=$(docker compose -f docker-compose.restore.yml exec -T postgres \
  psql -U bim_user -d bim_platform -tAc \
  "SELECT tgname FROM pg_trigger WHERE tgname='audit_logs_no_modify'" || echo "MISSING")
echo "  trigger: ${TRIGGER:-MISSING}"
[[ "$TRIGGER" == "audit_logs_no_modify" ]] || { echo "❌ 監査トリガーがありません" >&2; exit 1; }

echo "🔎 検証: 全ファイルSHA-256"
if [[ "$DB_ONLY" == "true" ]]; then
  echo "  ⚠️  DB-only backup のためファイル検証対象外"
else
  docker compose -f docker-compose.restore.yml exec -T postgres \
    psql -U bim_user -d bim_platform -tAc \
    "SELECT storage_key || '|' || coalesce(checksum_sha256, '') FROM container_files ORDER BY created_at" \
    > "$TMP_DIR/files-to-verify.txt"
  mapfile -t FILES < "$TMP_DIR/files-to-verify.txt"
  VERIFIED=0
  for ENTRY in "${FILES[@]}"; do
    if [[ -z "$ENTRY" ]]; then
      echo "  ❌ storage_keyが空のfile recordを検出" >&2
      exit 1
    fi
    KEY="${ENTRY%%|*}"
    EXPECTED="${ENTRY##*|}"
    if [[ -z "$EXPECTED" ]]; then
      echo "  ❌ $KEY  checksum_sha256が未設定" >&2
      exit 1
    fi
    ACTUAL=$(docker run --rm \
      --network bim_platform_restore_net \
      -e "MC_HOST_restore=http://minioadmin:minioadmin123@minio:9000" \
      minio/mc cat "restore/bim-containers/$KEY" | sha256sum | cut -d' ' -f1)
    if [[ "$ACTUAL" == "$EXPECTED" ]]; then
      echo "  ✅ $KEY"
      VERIFIED=$((VERIFIED + 1))
    else
      echo "  ❌ $KEY  hash不一致 (expected=$EXPECTED actual=$ACTUAL)" >&2
      exit 1
    fi
  done
  if [[ "$VERIFIED" -ne "$DB_FILE_COUNT" ]]; then
    echo "❌ SHA-256検証件数がDB件数と一致しません (DB=$DB_FILE_COUNT verified=$VERIFIED)" >&2
    exit 1
  fi
fi

END_TS="$(date +%s)"
ELAPSED=$((END_TS - START_TS))
echo ""
echo "🎉 復元演習成功"
echo "   所要時間: ${ELAPSED} 秒（手順ベースの参考値。RTO目標: 8時間以内）"
echo "   復元時点: バックアップ日時ベース（RPO目標: 24時間以内）"
