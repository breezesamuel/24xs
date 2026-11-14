#!/usr/bin/env bash
# 找服务端创建 manual 订单的入口 (强制 contact 字段的根因修复点)
echo "=== 1. server.js 里订单创建端点 (POST order / register) ==="
grep -nE "POST.*order|order.*POST|registerOrder|createOrder|manualStatus|'manual'|意向|登记" /opt/bingdashan/server.js 2>/dev/null | grep -viE "test|probe" | head -25
echo ""
echo "=== 2. commerce.js 订单登记函数 ==="
grep -nE "function|manual|contact|register|create|intent" /opt/bingdashan/packages/core/billing/commerce.js 2>/dev/null | grep -viE "test|probe" | head -25
echo ""
echo "=== 3. 一个 manual 订单的完整字段 (确认有无 contact 字段) ==="
python3 -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
manual=[o for o in d.get('orders',[]) if o.get('channel')=='manual']
if manual:
    import pprint
    for o in manual[:2]:
        print(json.dumps(o, ensure_ascii=False, indent=2))
        print('---')
"
echo "done"
