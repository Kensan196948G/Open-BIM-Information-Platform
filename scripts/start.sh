#!/usr/bin/env bash
# start.sh — Open BIM Information Platform startup script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MODE="${1:-full}"  # full | demo

# Detect primary LAN IP
LAN_IP=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || hostname -I | awk '{print $1}')

cd "$PROJECT_DIR"

if [[ "$MODE" == "demo" ]]; then
  PORT=3000
  echo "🚀 デモモード起動 (mock データ使用)"
  docker compose -f docker-compose.demo.yml up -d --remove-orphans
  echo ""
  echo "✅ Open BIM プラットフォーム (デモ) が起動しました"
  echo ""
  echo "  🌐 WebUI:    http://${LAN_IP}:${PORT}"
  echo "  🔑 ログイン: demo@example.com / pass1234"
  echo ""
else
  FRONTEND_PORT=5173
  BACKEND_PORT=8000
  echo "🚀 フルスタック起動 (本番モード)"
  docker compose up -d --remove-orphans
  echo ""
  echo "✅ Open BIM プラットフォームが起動しました"
  echo ""
  echo "  🌐 WebUI:       http://${LAN_IP}:${FRONTEND_PORT}"
  echo "  🔧 API:         http://${LAN_IP}:${BACKEND_PORT}/api/v1"
  echo "  📊 API Docs:    http://${LAN_IP}:${BACKEND_PORT}/docs"
  echo "  🗄️  MinIO:       http://${LAN_IP}:9001"
  echo ""
fi
