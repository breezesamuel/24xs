#!/usr/bin/env bash
# 诊断 CN body bug: 看 node 端到底收到啥 (加临时 log 到 site_cn_server.mjs 的 Alipay/writerewards 分支)
echo "=== CN site_cn_server.mjs 是否有 body 读取 (readBody) ==="
grep -n "readBody\|function readBody\|req.on(\"data\"\|shimReq\|searchParams.set" /www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs 2>/dev/null | head -8
echo "=== 当前 nginx body 相关 (修复后) ==="
grep -nE "Content-Length|http2|proxy_pass" /www/server/panel/vhost/nginx/tools-cn.highkingflower.com.conf 2>/dev/null | head -6
echo "=== 直接打 node 127.0.0.1:8794 测 body (绕 nginx, 看 node 本身能否读) ==="
curl -s "http://127.0.0.1:8794/api/pay" --max-time 15 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=NODEONLY&amount=1" -o /tmp/_node.html -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
grep -oE 'out_trade_no[^&]{0,40}' /tmp/_node.html 2>/dev/null | head -1
echo "(NODEONLY = node 本身能读 body; 空/m10 = node readBody 也有问题)"
