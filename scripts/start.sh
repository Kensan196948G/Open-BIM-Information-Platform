#!/usr/bin/env bash
# start.sh — Open BIM Information Platform startup script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MODE="${1:-full}"  # full | demo

# ---------------------------------------------------------------------------
# Detect primary LAN IP (Linux/macOS fallback)
# ---------------------------------------------------------------------------
LAN_IP=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' \
         || ipconfig getifaddr en0 2>/dev/null \
         || hostname -I 2>/dev/null | awk '{print $1}' \
         || echo "localhost")

# ---------------------------------------------------------------------------
# Find an available TCP port starting from $1, step +1 until free
# ---------------------------------------------------------------------------
find_free_port() {
  local port="${1:-3000}"
  local max_search=100
  local count=0
  while [ "$count" -lt "$max_search" ]; do
    # Try ss (Linux), then lsof (macOS/Linux), then /proc/net/tcp fallback
    if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
      port=$((port + 1)); count=$((count + 1)); continue
    fi
    if command -v lsof &>/dev/null && lsof -iTCP:"${port}" -sTCP:LISTEN &>/dev/null 2>&1; then
      port=$((port + 1)); count=$((count + 1)); continue
    fi
    break
  done
  echo "$port"
}

cd "$PROJECT_DIR"

# ---------------------------------------------------------------------------
# DEMO mode — frontend only, mock data, no backend required
# ---------------------------------------------------------------------------
if [[ "$MODE" == "demo" ]]; then
  DEMO_PORT=$(find_free_port 3000)
  export DEMO_PORT

  echo "🔍 空きポートを検索中..."
  echo "   → ポート ${DEMO_PORT} が利用可能です"
  echo ""
  echo "🚀 デモモード起動 (モックデータ使用 / バックエンド不要)"
  docker compose -f docker-compose.demo.yml up -d --remove-orphans
  echo ""
  echo "✅ Open BIM プラットフォーム (デモ) が起動しました"
  echo ""
  echo "  🌐 WebUI:    http://${LAN_IP}:${DEMO_PORT}"
  echo "  🔑 ログイン: demo@example.com / pass1234"
  echo ""
  echo "  ┌────────────────────────────────────────┐"
  echo "  │  ブラウザで上記 URL を開いてください   │"
  echo "  │  Ctrl+C で停止 / サービス登録は:       │"
  echo "  │    sudo ./scripts/install-service.sh   │"
  echo "  └────────────────────────────────────────┘"
  echo ""

# ---------------------------------------------------------------------------
# FULL mode — complete stack (frontend + backend + DB + Redis + MinIO)
# ---------------------------------------------------------------------------
else
  FRONTEND_PORT=$(find_free_port 5173)
  BACKEND_PORT=$(find_free_port 8000)
  MINIO_PORT=$(find_free_port 9001)
  export FRONTEND_PORT BACKEND_PORT MINIO_PORT

  echo "🔍 空きポートを検索中..."
  echo "   → WebUI:   ${FRONTEND_PORT}"
  echo "   → API:     ${BACKEND_PORT}"
  echo "   → MinIO:   ${MINIO_PORT}"
  echo ""
  echo "🚀 フルスタック起動 (本番モード)"
  FRONTEND_PORT="$FRONTEND_PORT" BACKEND_PORT="$BACKEND_PORT" \
    docker compose up -d --remove-orphans
  echo ""
  echo "✅ Open BIM プラットフォームが起動しました"
  echo ""
  echo "  🌐 WebUI:       http://${LAN_IP}:${FRONTEND_PORT}"
  echo "  🔧 API:         http://${LAN_IP}:${BACKEND_PORT}/api/v1"
  echo "  📊 API Docs:    http://${LAN_IP}:${BACKEND_PORT}/docs"
  echo "  🗄️  MinIO:       http://${LAN_IP}:${MINIO_PORT}"
  echo ""
  echo "  ┌────────────────────────────────────────┐"
  echo "  │  ブラウザで上記 URL を開いてください   │"
  echo "  │  停止:  docker compose down            │"
  echo "  │  ログ:  docker compose logs -f         │"
  echo "  └────────────────────────────────────────┘"
  echo ""
fi
