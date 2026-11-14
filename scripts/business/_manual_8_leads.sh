#!/usr/bin/env bash
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
print('=== leads 全量 ===')
for ld in d.get('leads',[]):
    if isinstance(ld,dict):
        print('  ', json.dumps({k:ld.get(k) for k in ld.keys() if ld.get(k) is not None}, ensure_ascii=False)[:300])
print()
print('=== 全库所有非空 email/phone (去重, 标来源表) ===')
seen={}
for key,arr in d.items():
    if not isinstance(arr,list): continue
    for rec in arr:
        if isinstance(rec,dict):
            em=rec.get('email') or rec.get('to'); ph=rec.get('phone') or rec.get('mobile')
            if em: seen[em]=seen.get(em,set())|{key}
            if ph: seen['PH:'+ph]=seen.get('PH:'+ph,set())|{key}
n=0
for k,v in seen.items():
    n+=1
    if n>50: print('  ... (更多)'); break
    print('  ', k, '<-', ','.join(sorted(v)))
if not n: print('  (全库无任何 email/phone 记录)')
print()
print('=== mail 表 (33 条, 看发件/收件/内容摘要) ===')
for m in d.get('mail',[])[:8]:
    if isinstance(m,dict):
        keep={k:m.get(k) for k in ('id','to','from','subject','type','channel','at','ts','note','to_ip','to_visitor') if m.get(k) is not None}
        print('  ', json.dumps(keep, ensure_ascii=False)[:200])
"
echo "done"
