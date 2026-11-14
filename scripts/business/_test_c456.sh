#!/usr/bin/env bash
# 测 C4/C5/C6 全链路 (CN)
B="https://tools-cn.highkingflower.com"
R="C456TEST"
echo "=== C4 strategyapi rate ==="
curl -sk "$B/api/strategyapi?action=rate" --max-time 20 | head -c 200; echo
echo "=== C4 summary 未购 -> 0 额度 ==="
curl -sk "$B/api/strategyapi?ref=$R&action=summary" --max-time 20 | head -c 200; echo
echo "=== C4 purchase 无 admin -> forbidden ==="
curl -sk "$B/api/strategyapi?ref=$R" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"'$R'","action":"purchase","out_trade_no":"t1","secret":"wrong"}' | head -c 150; echo
echo "=== C5 marketdata rate ==="
curl -sk "$B/api/marketdata?action=rate" --max-time 20 | head -c 200; echo
echo "=== C5 access 未订阅 -> 402 need_payment ==="
curl -sk "$B/api/marketdata?ref=$R&action=access" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
curl -sk "$B/api/marketdata?ref=$R&action=access" --max-time 20 | head -c 180; echo
echo "=== C6 strategyhosting rate ==="
curl -sk "$B/api/strategyhosting?action=rate" --max-time 20 | head -c 200; echo
echo "=== C6 host 未托管 -> 402 need_payment ==="
curl -sk "$B/api/strategyhosting?ref=$R&action=host" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
curl -sk "$B/api/strategyhosting?ref=$R&action=host" --max-time 20 | head -c 180; echo
echo "=== 清理测试账本 ==="
rm -f /var/lib/bingdashan-cn/strategyapi/sqa:$R.json /var/lib/bingdashan-cn/marketdata/md:$R.json /var/lib/bingdashan-cn/strategyhosting/sh:$R.json 2>/dev/null
echo done
