#!/usr/bin/env bash
#
# monitor.sh — 定期監視（cron/systemd timer 想定）
#
# チェック: /health・ディスク・コンテナ健康状態・バックアップ鮮度・証明書期限
# 通知: MONITOR_WEBHOOK_URL（Slack/Teams互換）または MONITOR_MAIL_TO
# 終了コード: 0=正常 / 1=Warning / 2=Critical
#
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

WARNINGS=()
CRITICALS=()

note() {
  local level="$1" msg="$2"
  echo "[$level] $msg"
  if [[ "$level" == "WARN" ]]; then WARNINGS+=("$msg"); fi
  if [[ "$level" == "CRIT" ]]; then CRITICALS+=("$msg"); fi
}

# 1) 死活
if [[ -n "${MONITOR_HEALTH_URL:-}" ]]; then
  if curl -sf --max-time 10 "$MONITOR_HEALTH_URL" >/dev/null 2>&1; then
    echo "[OK] health: $MONITOR_HEALTH_URL"
  else
    note CRIT "health 応答なし: $MONITOR_HEALTH_URL"
  fi
fi

# 2) ディスク
USAGE=$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')
if [[ -n "${USAGE:-}" ]]; then
  if (( USAGE >= 85 )); then note CRIT "ディスク使用率 ${USAGE}%"
  elif (( USAGE >= 70 )); then note WARN "ディスク使用率 ${USAGE}%"
  else echo "[OK] disk: ${USAGE}%"; fi
fi

# 3) コンテナ健康状態
if command -v docker >/dev/null 2>&1; then
  UNHEALTHY=$(docker ps --filter "name=bim_" --format '{{.Names}} {{.Status}}' | rg -i "unhealthy|restarting" || true)
  if [[ -n "$UNHEALTHY" ]]; then note CRIT "異常コンテナ: $UNHEALTHY"; fi
fi

# 4) バックアップ鮮度
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
NEWEST=$(ls -t "$BACKUP_DIR"/backup-*.tar.gz.enc 2>/dev/null | head -1 || true)
if [[ -n "$NEWEST" ]]; then
  AGE_H=$(( ($(date +%s) - $(stat -c %Y "$NEWEST")) / 3600 ))
  if (( AGE_H > 26 )); then note CRIT "バックアップが ${AGE_H} 時間前（24h以内を期待）"
  else echo "[OK] backup: ${AGE_H}h前 ($(basename "$NEWEST"))"; fi
else
  note CRIT "バックアップファイルなし"
fi

# 5) 証明書期限
CERT="${CERT_PATH:-$PROJECT_DIR/certs/fullchain.pem}"
if [[ -f "$CERT" ]]; then
  DAYS=$(openssl x509 -enddate -noout -in "$CERT" -checkend $((30*86400)) >/dev/null 2>&1 && echo OK || echo EXPIRING)
  if [[ "$DAYS" != "OK" ]]; then note WARN "証明書が30日以内に期限切れ: $CERT"; else echo "[OK] cert: 30日以上有効"; fi
fi

# 通知
if (( ${#CRITICALS[@]} > 0 || ${#WARNINGS[@]} > 0 )); then
  SUMMARY="Open BIM監視: CRIT=${#CRITICALS[@]} WARN=${#WARNINGS[@]}"
  if [[ -n "${MONITOR_WEBHOOK_URL:-}" ]]; then
    PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'text': '''$SUMMARY
$(printf '%s\n' "${CRITICALS[@]}" "${WARNINGS[@]}")'''}))")
    curl -sf -X POST -H 'Content-Type: application/json' -d "$PAYLOAD" "$MONITOR_WEBHOOK_URL" >/dev/null 2>&1 || true
  fi
  if [[ -n "${MONITOR_MAIL_TO:-}" ]]; then
    printf '%s\n' "$SUMMARY" "${CRITICALS[@]}" "${WARNINGS[@]}" | mail -s "$SUMMARY" "$MONITOR_MAIL_TO" 2>/dev/null || true
  fi
fi

if (( ${#CRITICALS[@]} > 0 )); then exit 2; fi
if (( ${#WARNINGS[@]} > 0 )); then exit 1; fi
exit 0
