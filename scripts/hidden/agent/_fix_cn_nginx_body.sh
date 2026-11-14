#!/usr/bin/env bash
# 根治 CN nginx body 透传 (让 ?a=post / 支付宝建单 经公网正常收 body)
# 方案: 备份 conf -> 加 proxy_set_header Content-Length -> 关 http2 (对 POST 最稳) -> nginx -t -> reload
CONF=/www/server/panel/vhost/nginx/tools-cn.highkingflower.com.conf
BAK="${CONF}.bak_bodyfix_$(date +%s)"
cp "$CONF" "$BAK"
echo "已备份: $BAK"

# 1. 若缺 Content-Length 转发, 加 (在 proxy_pass 行后)
if ! grep -q "proxy_set_header Content-Length" "$CONF"; then
  sed -i '/proxy_pass http:\/\/127.0.0.1:8794;/a\        proxy_set_header Content-Length $http_content_length;' "$CONF"
  echo "已加 proxy_set_header Content-Length"
else
  echo "Content-Length 已存在"
fi

# 2. http2 对 POST body 偶发不稳; 把 listen 443 ssl 的 http2 关掉 (HTTP/1.1 代理最稳)
if grep -q "^    http2 on;" "$CONF"; then
  sed -i 's/^    http2 on;/    # http2 off (POST body 透传稳定优先)/' "$CONF"
  echo "已关 http2 (改注释)"
fi

echo "=== nginx -t ==="
nginx -t 2>&1 | tail -3
echo "=== reload ==="
nginx -s reload 2>&1 || systemctl reload nginx 2>&1
sleep 2
echo "=== 重测: 经 nginx 公网 POST body 是否到 node (建单看 out_trade_no 含不含 ref) ==="
# 用 /api/pay 建单 (urlencoded body 带 ref), 看返回 out_trade_no 是否含 MONELOOP
curl -sk "https://tools-cn.highkingflower.com/api/pay" --max-time 30 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=BODYFIX&slug=ch&amount=1" 2>&1 | grep -oE '"out_trade_no":"[^"]+"' | head -1
echo "(若 out_trade_no 含 BODYFIX = body 透传修复成功; 若含 m10 默认 = 仍丢 body)"
