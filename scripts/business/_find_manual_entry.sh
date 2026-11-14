#!/usr/bin/env bash
# 找 manual 意向单的登记入口 (CN 生产系统 /opt/bingdashan)
echo "=== 1. 搜 'channel:manual' / 'channel':'manual' 的写入源 ==="
grep -rnE "channel.*['\"]?manual['\"]?|manual.*channel" /opt/bingdashan --include="*.js" --include="*.mjs" --include="*.cjs" 2>/dev/null | grep -v node_modules | grep -vE "\.out|\.result" | head -20
echo ""
echo "=== 2. 搜 'pending' 订单创建 (status:pending + channel) ==="
grep -rnE "status.*pending|pending.*status|channel:.manual|createOrder|registerOrder|addOrder|意向|登记" /opt/bingdashan --include="*.js" --include="*.mjs" 2>/dev/null | grep -v node_modules | grep -viE "test|probe|regress" | head -20
echo ""
echo "=== 3. db.json.orders 的写入函数 (哪个模块 save orders) ==="
grep -rnE "orders.*push|orders\]\.|db\.orders|\.orders\.push|saveOrders|appendOrder|orders:" /opt/bingdashan/core /opt/bingdashan/scripts /opt/bingdashan/web /opt/bingdashan/api 2>/dev/null --include="*.js" --include="*.mjs" | grep -v node_modules | head -20
echo ""
echo "=== 4. 一个 manual 单的完整字段 (看有没有 contact/note 字段可堵) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
manual=[o for o in d.get('orders',[]) if o.get('channel')=='manual']
if manual:
    print('  全字段:', json.dumps(manual[0], ensure_ascii=False, indent=2)[:800])
"
echo "done"
