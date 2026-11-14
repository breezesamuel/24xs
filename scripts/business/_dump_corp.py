#!/usr/bin/env python3
import json, os
d=json.load(open('/opt/bingdashan/data/billing/corporate_899.json'))
items=d if isinstance(d,list) else (d.get('items') or d.get('orders') or [])
print("对公单数:", len(items))
for i in items:
    if isinstance(i, dict):
        print(json.dumps({k:i.get(k) for k in ('order_id','ref','corporate_amount','status','customer_name') if i.get(k) is not None}, ensure_ascii=False)[:200])
