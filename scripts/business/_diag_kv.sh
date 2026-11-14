#!/usr/bin/env bash
set -a; source "F:/2026/24xs/scripts/business/upstash.env"; set +a
API="$KV_REST_API_URL"; TOK="$KV_REST_API_TOKEN"
echo "=== 1. SCAN 原始返回 (看是否 error) ==="
curl -sk -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"match":"*","count":100,"cursor":""}' "$API/scan" 2>/dev/null | head -c 400; echo
echo "=== 2. KEYS 端点 (另一种) ==="
curl -sk -H "Authorization: Bearer $TOK" "$API/keys?match=*&count=100" 2>/dev/null | head -c 300; echo
echo "=== 3. 试 GET 一个可能的订单键 (alipay.js 用 bds_order_<单号>) ==="
for k in "bds_order_x" "orders_by_ref_demo_user_a" "track_20261112" "subwall_subwall:x"; do
  printf "  GET %-28s " "$k"
  curl -sk -H "Authorization: Bearer $TOK" "$API/get/$k" 2>/dev/null | head -c 100; echo
done
echo "=== 4. 这个 KV 的 URL (确认是不是 Vercel 用的那个) ==="
echo "  $API"
