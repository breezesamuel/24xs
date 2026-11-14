#!/usr/bin/env bash
# 从 db.json.orders(153) 捞出 pending 9 单 + 看 business.js 统计口径
echo "=== 1. business.js 怎么算 ordersPending (口径) ==="
sed -n '300,340p' /opt/bingdashan/scripts/ops/business.js
echo ""
echo "=== 2. db.json.orders 全量状态分布 ==="
python -c "
import json, collections
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
print('orders 总数:', len(orders))
print('状态分布:', dict(collections.Counter(str(o.get('status','?')).lower() for o in orders if isinstance(o,dict))))
print()
print('--- 字段结构 (首条) ---')
if orders: print('  ', json.dumps({k:orders[0].get(k) for k in list(orders[0].keys())[:18]}, ensure_ascii=False))
"
echo ""
echo "=== 3. 捞出 PENDING 订单 (待付) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
pend=[o for o in orders if isinstance(o,dict) and str(o.get('status','')).lower() in ('pending','waiting','unpaid','created','notpaid','wait','wait_buyer_pay','open','new')]
print('待付订单数:', len(pend))
now=0
import time
for i,o in enumerate(sorted(pend, key=lambda x: x.get('created_at') or x.get('ts') or x.get('at') or 0),1):
    print(f'  #{i} '+json.dumps({k:o.get(k) for k in ('id','order_no','out_trade_no','orderId','ref','userId','user','actorId','plan','slug','item','amount','value','status','created_at','ts','channel','carrier','paid_at') if k in o}, ensure_ascii=False))
"
echo "done"
