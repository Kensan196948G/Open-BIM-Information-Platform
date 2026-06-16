#!/usr/bin/env bash
# install-service.sh — systemd サービスとして登録する (要 root)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SYSTEMD_DIR="$PROJECT_DIR/infra/systemd"

if [[ "$EUID" -ne 0 ]]; then
  echo "❌ このスクリプトは root で実行してください: sudo $0" >&2
  exit 1
fi

MODE="${1:-full}"  # full | demo | both

install_service() {
  local name="$1"
  local src="$SYSTEMD_DIR/${name}.service"
  local dst="/etc/systemd/system/${name}.service"

  # Replace placeholder path with actual project directory
  sed "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" "$src" > "$dst"
  chmod 644 "$dst"
  systemctl daemon-reload
  systemctl enable "$name"
  echo "✅ $name を登録・有効化しました"
}

case "$MODE" in
  full)
    install_service "bim-platform"
    systemctl start bim-platform
    echo "🚀 bim-platform を起動しました"
    ;;
  demo)
    install_service "bim-platform-demo"
    systemctl start bim-platform-demo
    echo "🚀 bim-platform-demo を起動しました"
    ;;
  both)
    install_service "bim-platform"
    install_service "bim-platform-demo"
    systemctl start bim-platform
    echo "🚀 bim-platform を起動しました (demo は手動で: systemctl start bim-platform-demo)"
    ;;
  *)
    echo "使い方: $0 [full|demo|both]" >&2
    exit 1
    ;;
esac

LAN_IP=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || hostname -I | awk '{print $1}')
echo ""
echo "📌 次回起動時から自動的に開始されます"
echo "   フル: http://${LAN_IP}:5173  |  デモ: http://${LAN_IP}:3000"
