#!/usr/bin/env bash
# 测 CN /api/recovery (第 7 渠道) + 合规红线 (拒扫描他人无主资金)
echo "=== 1. 7 渠道端点全 200? ==="
for e in "bounty?action=tasks" "cashback?action=rate" "writerewards?action=rate" "charity?action=total" "bandwidth?action=rate" "recovery?action=rate" "config"; do
  printf "  %s: " "$e"; curl -sk "https://tools-cn.highkingflower.com/api/$e" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
done
echo "=== 2. 合规红线测试 ==="
echo "  (a) 无 owner_ref:"
curl -sk "https://tools-cn.highkingflower.com/api/recovery?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"found":{"amount":100,"asset":"USDC","source":"old_addr","authorized":true}}' | head -c 120; echo
echo "  (b) 未授权 (扫他人无主资金 -> 必须拒):"
curl -sk "https://tools-cn.highkingflower.com/api/recovery?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"SOMEONE","found":{"amount":5000,"asset":"USDT","source":"dead_wallet","authorized":false}}' | head -c 160; echo
echo "  (c) 无来源:"
curl -sk "https://tools-cn.highkingflower.com/api/recovery?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"ME","found":{"amount":10,"asset":"USDC","authorized":true}}' | head -c 120; echo
echo "  (d) 合法: 本人 + 授权 + 来源:"
curl -sk "https://tools-cn.highkingflower.com/api/recovery?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"RECOVT","found":{"amount":200,"asset":"USDC","source":"my_old_exchange","authorized":true}}' | head -c 200; echo
echo "=== 3. 幂等 (重复同条 -> duplicate) ==="
curl -sk "https://tools-cn.highkingflower.com/api/recovery?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"RECOVT","found":{"amount":200,"asset":"USDC","source":"my_old_exchange","authorized":true}}' | head -c 80; echo " (应 duplicate)"
echo "=== 4. summary ==="
curl -sk "https://tools-cn.highkingflower.com/api/recovery?ref=RECOVT" --max-time 20 | head -c 200; echo
echo "=== 5. 清理测试数据 ==="
rm -f /var/lib/bingdashan-cn/recovery/rc:RECOVT.json 2>/dev/null
echo "已清理"
