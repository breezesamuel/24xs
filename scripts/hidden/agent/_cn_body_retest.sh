#!/usr/bin/env bash
# 重测 CN /api/pay body 透传 (nginx 修复后)
echo "=== CN /api/pay body 透传 ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay" --max-time 40 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=BODYFIX2&slug=ch&amount=1" \
  -o /tmp/_pay.html -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
echo "out_trade_no:"
grep -oE 'out_trade_no[^&]{0,40}' /tmp/_pay.html 2>/dev/null | head -1
echo "(含 BODYFIX2 = body 透传修复成功; 含 m10/默认 = 仍丢 body)"
