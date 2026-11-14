#!/usr/bin/env bash
# 确认 CN /api/pay body 透传真正修复: out_trade_no 含 ref (= body 的 plan/ref 到达 alipay.js)
echo "=== 经 nginx /api/pay 建单 (body 带 ref=BODYPROOF) ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay" --max-time 25 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=BODYPROOF&slug=ch&amount=1" -o /tmp/_bp.html -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
echo "out_trade_no:"
grep -oE '"out_trade_no":"[^"]+"' /tmp/_bp.html 2>/dev/null | head -1
echo "(含 BODYPROOF = body 的 ref 到达 alipay.js, 订单不再默认 m10)"
echo ""
echo "=== 对照: 不带 body 的 GET (默认 m10) ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay?plan=trial&ref=GETONLY&amount=1" --max-time 20 -o /tmp/_g.html 2>&1
grep -oE '"out_trade_no":"[^"]+"' /tmp/_g.html 2>/dev/null | head -1
echo "(GET 带 query ref=GETONLY, 应含 GETONLY)"
