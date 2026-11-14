#!/usr/bin/env bash
set -a; source "F:/2026/24xs/scripts/business/upstash.env"; set +a
API="$KV_REST_API_URL"; TOK="$KV_REST_API_TOKEN"
H=(-H "Authorization: Bearer $TOK" -H "Content-Type: application/json")
D="F:/2026/24xs/scripts/business/_data"; mkdir -p "$D" 2>/dev/null
# 按 alipay.js 已知前缀逐个 scan (全库 scan 常被禁)
PREFS=(bds_order bds_subwall orders_by_ref track_ subwall_ coinsettle_ cbk_ by_ wr_ "2026" "20")
> "$D/_allkeys.txt"
for P in "${PREFS[@]}"; do
  R=$(curl -sk -X POST "${H[@]}" -d "{\"match\":\"$P*\",\"count\":500,\"cursor\":\"0\"}" "$API/scan" 2>/dev/null)
  N=$(echo "$R" | python -c "import sys,json
try:
  d=json.load(sys.stdin)
  ks=d.get('keys',[])
  print(len(ks))
  open('$D/_scan_$P.txt','w').write('\n'.join(ks))
except Exception as e:
  print(0)" 2>/dev/null)
  echo "  $P* : $N 键"
done
# 汇总 + 前缀分布
cat "$D"/_scan_*.txt 2>/dev/null | grep -v '^$' | sort -u > "$D/_allkeys.txt"
echo "=== 去重后总键数: $(grep -c . "$D/_allkeys.txt" || echo 0) ==="
echo "=== 前缀分布 ==="
sed -E 's/_[0-9a-zA-Z].*//; s/([a-z_]+).*/\1/' "$D/_allkeys.txt" 2>/dev/null | sort | uniq -c | sort -rn | head -25
echo "=== bds_order* 键 (订单) ==="
grep -E '^bds_order' "$D/_allkeys.txt" 2>/dev/null | head -20
echo "=== 任意含 order 的键 ==="
grep -iE 'order' "$D/_allkeys.txt" 2>/dev/null | head -20
