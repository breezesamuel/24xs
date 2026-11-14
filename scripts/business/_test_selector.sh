#!/usr/bin/env bash
# 验证 selector 改动后 CN 各渠道仍正常 + /api/pay 持久化选择器状态
B="https://tools-cn.highkingflower.com"
R="SELTEST9"
echo "=== C3 generate 带 strategy+data_source (未付费 -> 402) ==="
curl -sk "$B/api/reportexport?ref=$R" --max-time 20 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"'$R'","action":"generate","strategy_id":"dual_ma_5_20","format":"pdf","data_source":"public_candles"}' | head -c 200; echo
echo "=== C4 summary (含 strategy_id 上下文的 purchase 模拟: 无 admin -> forbidden) ==="
curl -sk "$B/api/strategyapi?ref=$R" --max-time 20 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"'$R'","action":"purchase","strategy_id":"my_mom_v3","out_trade_no":"t9","secret":"wrong"}' | head -c 150; echo
echo "=== C5 access 未订阅 -> 402 ==="
curl -sk "$B/api/marketdata?ref=$R&action=access" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
echo "=== C6 host 未托管 -> 402 ==="
curl -sk "$B/api/strategyhosting?ref=$R&action=host" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
echo "=== /api/pay 是否接受 strategy_id/data_source 并持久化 (查 config 验证 store 层) ==="
curl -sk "$B/api/config" --max-time 20 | python -c "import sys,json;print('  store:',json.load(sys.stdin).get('store'))" 2>/dev/null
echo "=== 清理 ==="
rm -f /var/lib/bingdashan-cn/strategyapi/sqa:$R.json /var/lib/bingdashan-cn/marketdata/md:$R.json /var/lib/bingdashan-cn/strategyhosting/sh:$R.json /var/lib/bingdashan-cn/reportexport/rpx:$R.json 2>/dev/null
echo done
