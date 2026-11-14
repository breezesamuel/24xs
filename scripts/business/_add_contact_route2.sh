#!/usr/bin/env bash
F=/www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs
python3 - "$F" <<'PY'
import sys
f=sys.argv[1]
s=open(f,encoding='utf-8').read()
block='''      if (sub === "track") {
        const mod = await loadHandler("api/track.js");
        return await callHandler(mod, req, res, query, body);
      }
'''
addition='''      if (sub === "contact") {
        const mod = await loadHandler("api/track.js");
        return await callHandler(mod, req, res, query, body);
      }
'''
if 'sub === "contact"' in s and 'if (sub === "contact")' not in s:
    s=s.replace(block, block+addition, 1)
    open(f,'w',encoding='utf-8').write(s)
    print('  已插入 /api/contact 路由块')
elif 'if (sub === "contact")' in s:
    print('  路由块已存在')
else:
    print('  ⚠️ 未找到 track 块锚点 (可能缩进不同), 需手动')
PY
echo "=== 校验 + 重启 + 测 ==="
node --check "$F" && echo "  语法 OK"
systemctl restart bingdashan-cn && sleep 3
echo "  CN: $(systemctl is-active bingdashan-cn)"
echo "=== /api/contact 留资测试 ==="
curl -sk -X POST "https://tools-cn.highkingflower.com/api/contact" --max-time 20 -H "Content-Type: application/json" -d '{"e":"register_email","r":"aodm","email":"aodm_test@example.com"}' | head -c 200; echo
echo "=== contact_email_map 落盘 ==="
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
cat "$FSDIR/contact_email_map.json" 2>/dev/null && echo " (已落盘)" || echo "  (还没)"
echo done
