#!/usr/bin/env bash
#
# av-eicar-test.sh — EICAR検体をアップロードし、AVが拒否することを確認する
#
# 前提: 本番構成（docker-compose.prod.yml）で backend + clamav が起動しており、
#       ログイン可能なユーザーと WIP 状態のコンテナがあること。
#
# 使い方:
#   BASE_URL=https://bim.example.com TOKEN=<access_token> \
#     PROJECT_ID=<id> CONTAINER_ID=<id> ./scripts/av-eicar-test.sh
#
set -euo pipefail

BASE_URL="${BASE_URL:?BASE_URL required (例: https://bim.example.com)}"
TOKEN="${TOKEN:?TOKEN required}"
PROJECT_ID="${PROJECT_ID:?PROJECT_ID required}"
CONTAINER_ID="${CONTAINER_ID:?CONTAINER_ID required}"

EICAR='X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
printf '%s' "$EICAR" > /tmp/eicar-test.txt

STATUS=$(curl -s -o /tmp/eicar-response.json -w '%{http_code}' \
  -X POST "$BASE_URL/api/v1/projects/$PROJECT_ID/containers/$CONTAINER_ID/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/eicar-test.txt;type=application/pdf;filename=eicar-test.pdf")

rm -f /tmp/eicar-test.txt /tmp/eicar-response.json

if [[ "$STATUS" == "422" ]]; then
  echo "✅ EICAR テスト成功: アップロードが拒否されました (HTTP 422)"
  exit 0
fi

echo "❌ EICAR テスト失敗: HTTP $STATUS（422 を期待）" >&2
exit 1
