#!/usr/bin/env bash
echo "=== 1. 落地页 /get.html 能访问 (CN) ==="
code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 20 "https://tools-cn.highkingflower.com/get.html")
echo "  /get.html -> HTTP $code"
curl -sk --max-time 20 "https://tools-cn.highkingflower.com/get.html" | grep -oE "<title>[^<]*</title>|免费试 7 天|留个邮箱" | head -3
echo ""
echo "=== 2. 落地页留资全链路 (模拟用户留邮箱 -> /api/contact 持久化 -> winback 能读到) ==="
curl -sk -X POST "https://tools-cn.highkingflower.com/api/contact" --max-time 20 -H "Content-Type: application/json" \
  -d '{"e":"register_email","r":"GET","email":"newuser@example.com"}' | head -c 150; echo
sleep 1
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
echo "  contact_email_map 现在:"
cat "$FSDIR/contact_email_map.json" 2>/dev/null; echo
echo ""
echo "=== 3. 分享链接 (可发出去的获客 URL) ==="
echo "  主落地页: https://tools-cn.highkingflower.com/get.html?ref=<渠道码>"
echo "  (ref=渠道码 让留资归属到渠道, 便于统计哪条链接带来新 trial 用户)"
echo "  例: https://tools-cn.highkingflower.com/get.html?ref=wechat"
echo "      https://tools-cn.highkingflower.com/get.html?ref=xhs"
echo "      https://tools-cn.highkingflower.com/get.html?ref=github"
echo done
