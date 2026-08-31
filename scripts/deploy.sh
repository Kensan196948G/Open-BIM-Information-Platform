#!/usr/bin/env bash
#
# deploy.sh — 固定commitからの段階的デプロイ / ロールバック
#
# モード:
#   local   : このホスト上で docker compose を使いデプロイ（デフォルト）
#   remote  : SSH先ホストでデプロイ（PROD_HOST / PROD_USER / SSH鍵が必要）
#   rollback <ref>: 指定の安定タグ/commitへコードを戻し再デプロイ
#
# 使い方（例）:
#   ./scripts/deploy.sh local origin/main
#   PROD_HOST=xxx PROD_USER=ubuntu ./scripts/deploy.sh remote origin/main
#   ./scripts/deploy.sh rollback v0.1.0
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

MODE="${1:-local}"
REF="${2:-origin/main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

run_local() {
  echo "🚀 デプロイ開始: $REF (local)"
  git fetch origin --tags
  git checkout --detach "$REF"
  git rev-parse HEAD > /tmp/bim-deploy-commit.txt

  echo "📦 イメージビルド"
  docker compose -f "$COMPOSE_FILE" build backend frontend

  echo "🗄️ マイグレーション（migrate サービスで自動適用）"
  docker compose -f "$COMPOSE_FILE" up -d --no-deps migrate || true
  docker compose -f "$COMPOSE_FILE" up -d

  echo "🔍 スモーク: /health"
  HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health}"
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 10 "$HEALTH_URL" 2>/dev/null \
      | python3 "$PROJECT_DIR/scripts/validate_health_response.py"; then
      echo "✅ /health OK"
      return 0
    fi
    sleep 2
  done
  echo "❌ /health が正常なJSONを返しません（status/database=ok を期待）" >&2
  return 1
}

run_remote() {
  if [[ -z "${PROD_HOST:-}" || -z "${PROD_USER:-}" ]]; then
    echo "❌ PROD_HOST / PROD_USER が未設定です" >&2
    exit 1
  fi
  echo "🚀 リモートデプロイ: $PROD_USER@$PROD_HOST ($REF)"
  ssh -p "${PROD_SSH_PORT:-22}" "$PROD_USER@$PROD_HOST" \
    "cd ${PROD_DIR:-$PROJECT_DIR} && git fetch origin --tags && git checkout --detach '$REF' && ./scripts/deploy.sh local '$REF'"
}

rollback() {
  TARGET="${1:?rollback先のrefが必要}"
  echo "⏪ ロールバック: $TARGET"
  run_local "$TARGET"
  echo "✅ ロールバック完了: $TARGET"
}

case "$MODE" in
  local) run_local ;;
  remote) run_remote ;;
  rollback) rollback "$REF" ;;
  *)
    echo "使い方: $0 [local|remote|rollback] [ref]" >&2
    exit 1
    ;;
esac
