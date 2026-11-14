#!/usr/bin/env bash
# 验证 alipay 支付链接真能"建单+跳转收银台" (用 ¥1 trial 链接, 不真付款)
B="https://tools-cn.highkingflower.com"
echo "=== 1. 访问 trial 链接 (¥1, ref=aofl), 看是否 302/HTML 跳支付宝收银台 ==="
# /api/pay 返回 200 + HTML 表单 (自动 submit 到 alipay gateway), 不是 302
RESP=$(curl -sk "$B/api/pay?plan=trial&slug=tool&ref=aofl" --max-time 25 -D /tmp/_hdr.txt 2>/dev/null)
echo "  HTTP 头:"; head -5 /tmp/_hdr.txt
echo "  响应体前 300 字:"; echo "$RESP" | head -c 300; echo
echo ""
echo "=== 2. 是否含支付宝网关 (openapi.alipay.com) + out_trade_no (证明建单成功) ==="
if echo "$RESP" | grep -q "openapi.alipay.com"; then echo "  ✅ 含支付宝网关, 链接可跳收银台"; else echo "  ⚠️ 未检测到支付宝网关"; fi
if echo "$RESP" | grep -qE "out_trade_no|BDS_"; then echo "  ✅ 含订单标识, 建单成功"; else echo "  订单标识: $(echo "$RESP" | grep -oE 'BDS_[A-Za-z0-9_]+' | head -1)"; fi
echo ""
echo "=== 3. 验证链接对应的订单已被 CN 记录 (查 db.json 新订单) ==="
sleep 1
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
# 找 ref=aofl 且 plan=trial 的 created 单
new=[o for o in orders if 'aofl' in str(o.get('visitor') or '') and o.get('status') in ('created','pending')]
print('  ref=aofl 的订单:', len(new))
for o in new[-3:]:
    print('   ', o.get('id'),'| plan',o.get('plan'),'|',o.get('status'),'| ¥',o.get('amount'))
"
echo done
