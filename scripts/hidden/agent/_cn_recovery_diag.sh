#!/usr/bin/env bash
# 诊断: /api/recovery POST 时, 经 CN shim 后 alipay.js 收到的 data 是什么
echo "=== 直连 node 测 /api/recovery (看 body 是否到) ==="
curl -s "http://127.0.0.1:8794/api/recovery?action=record" --max-time 15 \
  -H "Content-Type: application/json" -X POST \
  -d '{"ref":"DBG","found":{"amount":200,"asset":"USDC","source":"old","authorized":true}}' -o /tmp/_dbg.json -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
echo "  结果:"; cat /tmp/_dbg.json 2>/dev/null | head -c 200; echo
echo "=== 直连 node 扁平 body (amount 顶层) ==="
curl -s "http://127.0.0.1:8794/api/recovery?action=record" --max-time 15 \
  -H "Content-Type: application/json" -X POST \
  -d '{"ref":"DBG2","amount":200,"asset":"USDC","source":"old","authorized":true}' -o /tmp/_dbg2.json -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
cat /tmp/_dbg2.json 2>/dev/null | head -c 200; echo
echo "=== 看 CN shim 是否 merge body (CN-SRV-DIAG) ==="
tail -3 /www/wwwlogs/bingdashan-cn.log 2>/dev/null | grep -oE "CN-SRV-DIAG bodyKeys=[^ ]*" | head -3
echo "done"
