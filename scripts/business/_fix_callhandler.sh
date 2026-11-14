#!/usr/bin/env bash
# 修 CN callHandler: 把 body 挂到 req.body, 让 track.js 等 handler 能读到 (之前 body 被丢)
F=/www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs
cp "$F" "${F}.bak_body_$(date +%s)"
python3 - <<PY
f="$F"
s=open(f,encoding="utf-8").read()
# 在 await fn(req, shim) 前, 把 body/query 挂到 req (handler 通过 req.body / req.query 读)
old='  await fn(req, shim);'
new='  try { if (req) { req.body = body; req.query = query; } } catch (e) {}\n  await fn(req, shim);'
if old in s and "req.body = body" not in s:
    s=s.replace(old,new,1)
    open(f,"w",encoding="utf-8").write(s)
    print("  已把 body/query 挂到 req (handler 可读)")
else:
    print("  已存在或锚点不符")
PY
node --check "$F" && echo "  语法 OK"
systemctl restart bingdashan-cn && sleep 3
echo "  CN: $(systemctl is-active bingdashan-cn)"
echo ""
echo "=== 测 /api/contact 留资 (应真落盘) ==="
curl -sk -X POST "https://tools-cn.highkingflower.com/api/contact" --max-time 20 -H "Content-Type: application/json" -d '{"e":"register_email","r":"GET","email":"probe_new@example.com"}' | head -c 150; echo
sleep 1
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
echo "  contact_email_map:"; cat "$FSDIR/contact_email_map.json" 2>/dev/null; echo
echo done
