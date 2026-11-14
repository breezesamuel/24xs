#!/usr/bin/env bash
set -a; source "F:/2026/24xs/scripts/business/upstash.env"; set +a
API="$KV_REST_API_URL"; TOK="$KV_REST_API_TOKEN"
H=(-H "Authorization: Bearer $TOK")
echo "=== /keys 正确语法: POST + 不同参数 (Upstash 各版本差异) ==="
for style in \
  '{"match":"*","cursor":"0","count":100}' \
  '{"match":"bds_*","cursor":"0"}' \
  '{"match":"bds_order_%","count":100}' \
  '{"match":"bds_order_*"}'
do
  printf "  POST /keys %s -> " "$(echo "$style" | head -c 40)"
  R=$(curl -sk -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" -d "$style" "$API/keys" 2>/dev/null | head -c 120)
  echo "$R"
done
echo "=== Upstash 是否支持 LIST (redis 命令式) ==="
R=$(curl -sk -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" -d '{"command":"KEYS","args":["bds_order_*"]}' "$API/command" 2>/dev/null | head -c 200)
echo "  /command KEYS: $R"
R2=$(curl -sk -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" -d '{"command":"KEYS","args":["*"],"count":50}' "$API/command" 2>/dev/null | head -c 200)
echo "  /command KEYS *: $R2"
echo "=== 已知能 GET 的订单键 (确认 out_trade_no 规律, 用于反推) ==="
for k in \
  "bds_order_BDS_OWNER_INCOME_trial_1794397396701" \
  "bds_order_BDS_OWNER_INCOME_CN_trial_1794397396958"; do
  printf "  GET %-55s " "$k"
  curl -sk "${H[@]}" "$API/get/$k" 2>/dev/null | head -c 90; echo
done
