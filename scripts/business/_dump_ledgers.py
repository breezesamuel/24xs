#!/usr/bin/env python3
import json, os, sys
bl = '/opt/bingdashan/data/billing'
outreach = []
corp = []
try:
    d=json.load(open(os.path.join(bl,'outreach_ledger.json')))
    outreach = d if isinstance(d,list) else d.get('items',[])
except Exception as e:
    print("ERR outreach:",e,file=sys.stderr)
try:
    d=json.load(open(os.path.join(bl,'corporate_899.json')))
    corp = d if isinstance(d,list) else (d.get('items') or d.get('orders') or [])
except Exception as e:
    print("ERR corp:",e,file=sys.stderr)

rows_out = [{k:(i.get(k) if k!='kind' else i.get('kind','?')) for k in ('kind','order_id','ref','status','billed','collect','plan','pay_link','note')} if False else None or {k:i.get(k,(i.get('kind','?'),None)[0] if k=='kind' else None) for k in ('kind','order_id','ref','status','billed','collect','plan','pay_link','note')} for i in outreach][0] if False else []
rows_corp = []
for i in corp:
    rows_corp.append({k:i.get(k) for k in ('order_id','ref','corporate_amount','amount','status','customer_name','remit_memo','verify_flow','account_note','payment_type') if i.get(k) is not None})
# compact
rows_out=[]
for i in outreach:
    rows_out.append({'kind':i.get('kind','?'),'order_id':i.get('order_id',''),'ref':i.get('ref',''),'status':i.get('status','?'),'billed':i.get('billed',0),'collect':i.get('collect',0),'plan':i.get('plan','?'),'pay_link':i.get('pay_link',''),'note':i.get('note','')})
pending_out=[r for r in rows_out if r['status'] not in ('paid','collected','done','verified')]
pending_corp=[r for r in rows_corp if r['status'] not in ('paid','collected','done','verified')]
total_yuan=sum(r['collect'] for r in pending_out)+sum(r.get('amount') or r.get('corporate_amount') or 0 for r in pending_corp)
print(f"PENDING_OUT={len(pending_out)} PENDING_CORP={len(pending_corp)} TOTAL_YUAN={total_yuan}")
for r in pending_out: print("OUT",json.dumps(r,ensure_ascii=False)[:140])
for r in pending_corp: print("CORP",json.dumps(r,ensure_ascii=False)[:140])
