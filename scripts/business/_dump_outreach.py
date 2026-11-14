#!/usr/bin/env python3
import json, os
d=json.load(open('/opt/bingdashan/data/billing/outreach_ledger.json'))
items=d if isinstance(d,list) else d.get('items',[])
print("manual/trial 单数:", len(items))
for i in items[:15]:
    print(json.dumps({k:i.get(k) for k in ('kind','order_id','ref','status','billed','collect','plan','pay_link') if i.get(k) is not None}, ensure_ascii=False)[:200])
