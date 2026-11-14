#!/usr/bin/env bash
# 在 CN site_cn_server.mjs 加 /api/contact -> track.js 路由 (mirror track 块)
F=/www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs
cp "$F" "${F}.bak_contact_$(date +%s)"
# 1. isAlipay 判断加 contact
sed -i 's#const isAlipay = !(sub === "track" || ARCADE_ROUTES.has(sub) || sub === "autoops.js");#const isAlipay = !(sub === "track" \|\| sub === "contact" \|\| ARCADE_ROUTES.has(sub) \|\| sub === "autoops.js");#' "$F"
# 2. 在 track 路由块后加 contact 路由块
python3 - "$F" <<'PY'
import sys
f=sys.argv[1]
s=open(f).read()
anchor='''      if (sub === "track") {
        const mod = await loadHandler("api/track.js");
        return await callHandler(mod, req, res, query, body);
      }
'''
addition='''      if (sub === "contact") {
        const mod = await loadHandler("api/track.js");
        return await callHandler(mod, req, res, query, body);
      }
'''
if 'sub === "contact"' not in s:
    s=s.replace(anchor, anchor+addition, 1)
    open(f,'w').write(s)
    print('  已插入 /api/contact 路由')
else:
    print('  已存在, 跳过')
PY
echo "=== 校验 mjs 语法 ==="
node --check "$F" && echo "  site_cn_server.mjs 语法 OK"
echo ""
echo "=== 重启 CN + 测 /api/contact ==="
systemctl restart bingdashan-cn && sleep 3
echo "  CN 状态: $(systemctl is-active bingdashan-cn)"
curl -sk -X POST "https://tools-cn.highkingflower.com/api/contact" --max-time 20 -H "Content-Type: application/json" -d '{"e":"register_email","r":"aodm","email":"aodm_test@example.com"}' | head -c 200; echo
echo ""
echo "=== 确认 contact_email_map 落盘 ==="
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
cat "$FSDIR/contact_email_map.json" 2>/dev/null && echo " (已落盘)" || echo "  (还没)"
echo done
