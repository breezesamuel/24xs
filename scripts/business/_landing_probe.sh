#!/usr/bin/env bash
# 找 CN 工具站静态页部署位置 + 现有注册/试用/订阅入口 (落地页复用这些)
echo "=== 1. CN 工具站静态根目录 + 现有页面 ==="
ls -1 /www/wwwroot/tools-cn.highkingflower.com/*.html 2>/dev/null | head -20
echo "--- 现有入口页 (channels/index/订阅墙) ---"
for p in index.html channels.html subwall.html paid.html trial.html; do
  [ -f "/www/wwwroot/tools-cn.highkingflower.com/$p" ] && echo "  有: $p"
done
echo ""
echo "=== 2. 现有"注册/试用/订阅"入口在哪 (落地页要导流到这) ==="
grep -rlniE "注册|试用|subwall|trial|立即订阅|开通" /www/wwwroot/tools-cn.highkingflower.com/*.html 2>/dev/null | head
echo ""
echo "=== 3. 站点 SEO 现状 (title/meta/description, 看缺什么) ==="
for p in index.html channels.html; do
  f="/www/wwwroot/tools-cn.highkingflower.com/$p"
  [ -f "$f" ] && { echo "  --- $p ---"; grep -oiE "<title>[^<]*</title>|<meta name=\"description\"[^>]*>|<meta name=\"keywords\"[^>]*>" "$f" 2>/dev/null | head -4; }
done
echo ""
echo "=== 4. 站点域名 (落地页放哪个域) ==="
grep -hoE "server_name.*" /www/server/panel/vhost/nginx/tools-cn.highkingflower.com.conf 2>/dev/null | head
echo done
