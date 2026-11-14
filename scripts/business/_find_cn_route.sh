#!/usr/bin/env bash
# 找 CN 路由 /api/track 的配置 + 加 /api/contact + 验证
echo "=== 1. CN 怎么路由 /api/track (找 nginx conf) ==="
grep -rlniE "api/track" /www/server/panel/vhost /etc/nginx /www/wwwroot/tools-cn.highkingflower.com 2>/dev/null | grep -viE "node_modules|\.git|track\.js" | head
echo ""
echo "=== 2. 该站 nginx conf (含 highkingflower 的) ==="
for f in /www/server/panel/vhost/nginx/*.conf; do
  if grep -lq "highkingflower" "$f" 2>/dev/null; then echo "  -> $f"; fi
done
echo ""
echo "=== 3. 看 track/contact 在 nginx 里怎么写的 (location 块) ==="
for f in /www/server/panel/vhost/nginx/*.conf; do
  if grep -q "highkingflower" "$f" 2>/dev/null; then
    grep -niE "api/track|api/contact|location /api" "$f" 2>/dev/null | head -15
    echo "  (文件: $f)"
  fi
done
echo ""
echo "=== 4. 当前 200/404 确认 ==="
curl -sk -o /dev/null -w "  /api/track=%{http_code} " "https://tools-cn.highkingflower.com/api/track" --max-time 15
curl -sk -o /dev/null -w "  /api/contact=%{http_code}\n" "https://tools-cn.highkingflower.com/api/contact" --max-time 15
echo done
