#!/usr/bin/env bash
echo "=== orders.json 完整 items (closure 订单账本) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/billing/orders.json'))
items=d.get('items',[])
print('count 字段:', d.get('count'), '| items 实际:', len(items))
from collections import Counter
print('状态分布:', dict(Counter(str(i.get('status','?')).lower() for i in items if isinstance(i,dict))))
print()
print('--- 全部订单明细 (逐条, 关键字段) ---')
for i in items:
    if not isinstance(i,dict): continue
    keep={k:i.get(k) for k in ('id','order_no','out_trade_no','orderId','ref','user','userId','actorId','plan','slug','item','amount','value','price','status','state','created_at','ts','paid_at','channel','carrier') if k in i}
    print('  ', json.dumps(keep, ensure_ascii=False))
" 2>&1
echo ""
echo "=== 按状态分组: PENDING/待付 ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/billing/orders.json'))
items=d.get('items',[])
pend=[i for i in items if isinstance(i,dict) and str(i.get('status','')).lower() in ('pending','waiting','unpaid','created','notpaid','wait','wait_buyer_pay')]
print('待付订单数:', len(pend))
for i in pend:
    print('  ', json.dumps({k:i.get(k) for k in ('id','order_no','out_trade_no','orderId','ref','user','actorId','plan','slug','item','amount','value','status','created_at','ts') if k in i}, ensure_ascii=False))
" 2>&1
