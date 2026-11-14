#!/usr/bin/env bash
set -a; source "F:/2026/24xs/scripts/business/upstash.env"; set +a
API="$KV_REST_API_URL"; TOK="$KV_REST_API_TOKEN"
echo "=== /scan 原始返回 (track_* 已知有数据) ==="
echo "--- POST /scan match=track_* ---"
curl -sk -X POST -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d '{"match":"track_*","count":50,"cursor":"0"}' "$API/scan" 2>&1 | head -c 500; echo
echo "--- GET /keys?match=track_* ---"
curl -sk -H "Authorization: Bearer $TOK" "$API/keys?match=track_*&count=50" 2>&1 | head -c 400; echo
echo "=== 直接 GET 已知的 track 键 (确认数据在) ==="
curl -sk -H "Authorization: Bearer $TOK" "$API/get/track_20261112" 2>&1 | head -c 200; echo
echo "=== 试 alipay.js 里 saveOrder 用的确切键名: 看它怎么拼 bds_order_ ==="
# 已知 track_20261112 存在 -> 说明键名规则对; 订单键是 bds_order_<out_trade_no>
# out_trade_no 形如 BDS_<ref>_<plan>_<ts>。试一个可能的:
for k in "bds_order_BDS_OWNER_INCOME_trial_1794397396701" "bds_order_BDS"; do
  printf "  GET %-50s " "$k"
  curl -sk -H "Authorization: Bearer $TOK" "$API/get/$k" 2>&1 | head -c 80; echo
done
