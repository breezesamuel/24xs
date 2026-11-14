#!/usr/bin/env bash
# 确认 Vercel 主站订单存储层 (kv/supabase), 为拉 9 单做准备
echo "=== 1. Vercel 主站 storeKind ==="
curl -sk "https://tools.highkingflower.com/api/config" --max-time 20 | grep -oE '"store":"[a-z]+"' | head -1
echo "=== 2. Vercel 有没有订单列端点 (探) ==="
for e in "orders" "bds_orders" "admin/orders" "loop"; do
  printf "  /api/%-14s " "$e"
  code=$(curl -sk "https://tools.highkingflower.com/api/$e" --max-time 15 -o /tmp/_v.json -w "%{http_code}" 2>/dev/null)
  echo "HTTP $code"; head -c 120 /tmp/_v.json 2>/dev/null; echo
done
echo "=== 3. 本地 24xs 仓库: Vercel 部署用的 .env / upstash 配置 (键名) ==="
if [ -f "F:/2026/24xs/.env" ]; then
  grep -oE "^[A-Z_]*(KV|UPSTASH|SUPABASE|REACT_APP|REPO)[A-Z_]*=" "F:/2026/24xs/.env" 2>/dev/null | head
  echo "  (本地 .env 行数: $(wc -l < 'F:/2026/24xs/.env'))"
fi
echo "done"
