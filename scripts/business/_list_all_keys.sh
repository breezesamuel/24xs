#!/usr/bin/env bash
set -a; source "F:/2026/24xs/scripts/business/upstash.env"; set +a
API="$KV_REST_API_URL"; TOK="$KV_REST_API_TOKEN"
H=(-H "Authorization: Bearer $TOK")
echo "=== Upstash REST KEYS 端点 (正确语法: GET /keys?match=...) ==="
# REST API 用 /keys?match=...&count=N&cursor=
CURSOR=""
PAGE=0
> "F:/2026/24xs/scripts/business/_data/_allkeys.txt"
while :; do
  R=$(curl -sk "${H[@]}" "$API/keys?match=*&count=200&cursor=$CURSOR" 2>/dev/null)
  KEYS=$(echo "$R" | python -c "import sys,json
try:
  d=json.load(sys.stdin)
  print(' '.join(d.get('keys',[])))
except: pass" 2>/dev/null)
  NCUR=$(echo "$R" | python -c "import sys,json
try: print(json.load(sys.stdin).get('cursor',''))
except: print('')" 2>/dev/null)
  echo "$KEYS" | tr ' ' '\n' | grep -v '^$' >> "F:/2026/24xs/scripts/business/_data/_allkeys.txt"
  PAGE=$((PAGE+1))
  echo "  page $PAGE: +$(echo "$KEYS" | tr ' ' '\n' | grep -c . || echo 0) 键, cursor=$NCUR"
  if [ -z "$NCUR" ] || [ "$NCUR" = "0" ] || [ $PAGE -gt 40 ]; then break; fi
  CURSOR="$NCUR"
done
echo "=== 总键数: $(grep -c . F:/2026/24xs/scripts/business/_data/_allkeys.txt || echo 0) ==="
echo "=== 前缀分布 ==="
sort "F:/2026/24xs/scripts/business/_data/_allkeys.txt" | sed -E 's/_[0-9a-fA-F].*//' | sort | uniq -c | sort -rn | head -30
