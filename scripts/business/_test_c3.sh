#!/usr/bin/env bash
# 测 C3 /api/reportexport 全链路 (CN)
B="https://tools-cn.highkingflower.com/api/reportexport"
R="C3TEST"
echo "=== (a) rate (价格/格式/合规) ==="
curl -sk "$B?action=rate" --max-time 20 | head -c 240; echo
echo "=== (b) generate 未付费 -> need_payment (HTTP 402) ==="
curl -sk "$B?ref=$R" --max-time 20 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"'"$R"'","action":"generate","strategy_id":"mom_v1","format":"pdf","version":1}' | head -c 240; echo
echo "=== (c) 管理员 record 模拟已付费解锁 (需 ADMIN_SECRET; CN 未配 -> 应 forbidden) ==="
curl -sk "$B?ref=$R" --max-time 20 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"'"$R"'","action":"record","strategy_id":"mom_v1","format":"pdf","paid_via":"alipay","secret":"wrong"}' | head -c 160; echo
echo "=== (d) 清理测试账本 ==="
rm -f /var/lib/bingdashan-cn/reportexport/rpx:$R.json 2>/dev/null
echo done
