#!/usr/bin/env bash
echo "=== /api/pay 返回内容 (看 form 结构 + out_trade_no) ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay" --max-time 25 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=BODYPROOF&slug=ch&amount=1" 2>&1 | head -c 500
echo ""
echo "=== 含 out_trade_no? ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay" --max-time 25 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=BODYPROOF&slug=ch&amount=1" 2>&1 | grep -oE 'out_trade_no[^&<]{0,50}' | head -2
