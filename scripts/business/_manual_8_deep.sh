#!/usr/bin/env bash
# 深挖: 8 单 manual 待付的真实联系方式 (扩大匹配: 全库 email/phone/ref/visitor + 时间窗 + IP 变体)
python -c "
import json, re, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
# 8 单的关键特征 (visitor 里的 IP + visitor id + createdAt 时间窗 + plan)
manual=[o for o in d.get('orders',[]) if isinstance(o,dict) and o.get('status')=='pending' and o.get('channel')=='manual']
print('=== 8 单 manual 特征 ===')
feats=[]
for o in manual:
    v=str(o.get('visitor') or '')
    # visitor 形如 ip:101_228_2_131:mvgeerdl -> ip=101_228_2_131, vid=mvgeerdl
    parts=v.split(':')
    ipd = parts[1].replace('_','.') if len(parts)>=2 else ''
    vid = parts[2] if len(parts)>=3 else ''
    ts=o.get('createdAt') or 0
    day=datetime.datetime.utcfromtimestamp(ts/1000).strftime('%m-%d') if ts else ''
    feats.append({'id':o.get('id'),'ip':ipd,'vid':vid,'plan':o.get('plan'),'amt':o.get('amount'),'day':day,'ts':ts})
    print(f'  {o.get(\"id\")} | IP {ipd} | vid {vid} | {o.get(\"plan\")} ¥{o.get(\"amount\")} | {day}')
print()
ips=set(f['ip'] for f in feats if f['ip'])
vids=set(f['vid'] for f in feats if f['vid'])
# 时间窗: 8 单都在 10-20 ~ 11-02
min_ts=min(f['ts'] for f in feats if f['ts']); max_ts=max(f['ts'] for f in feats if f['ts'])
print(f'时间窗: {datetime.datetime.utcfromtimestamp(min_ts/1000).strftime(\"%m-%d\")} ~ {datetime.datetime.utcfromtimestamp(max_ts/1000).strftime(\"%m-%d\")}')
print()

# ---- 全库搜: 任何字段含这些 IP(点/下划线两变体) 或 vid 的记录 ----
def search_all():
    found={}
    for key,arr in d.items():
        if not isinstance(arr,list): continue
        for rec in arr:
            if not isinstance(rec,dict): continue
            s=json.dumps(rec,ensure_ascii=False)
            hits=[]
            for ip in ips:
                if ip in s or ip.replace('.','_') in s: hits.append(('ip',ip))
            for vid in vids:
                if vid in s: hits.append(('vid',vid))
            if hits:
                found.setdefault(key,[]).append((rec,hits))
    return found
found=search_all()
print('=== 全库匹配命中 (IP/vid 任一出现) ===')
for key,recs in found.items():
    print(f'  表 {key}: {len(recs)} 条命中')
    for rec,hits in recs[:8]:
        keep={k:rec.get(k) for k in ('id','email','phone','ref','visitor','ip','plan','status','created_at','at','ts','note','owner','user') if rec.get(k) is not None}
        print(f'    命中{hits}:', json.dumps(keep, ensure_ascii=False)[:200])
print()

# ---- leads + 含邮箱的 34 条 全量列出 (人工看哪条是这 8 单) ----
print('=== leads 全量 (3 条) ===')
for ld in d.get('leads',[]):
    if isinstance(ld,dict):
        print('  ', json.dumps({k:ld.get(k) for k in ('id','email','phone','name','ip','plan','status','created_at','note','ref') if ld.get(k) is not None}, ensure_ascii=False)[:240])
print()
print('=== 全库所有非空 email (去重, 标注来源表) ===')
seen={}
for key,arr in d.items():
    if not isinstance(arr,list): continue
    for rec in arr:
        if isinstance(rec,dict):
            em=rec.get('email') or rec.get('to')
            if em: seen[em]=seen.get(em,[])+[key]
for em,srcs in list(seen.items())[:40]:
    uniq=list(dict.fromkeys(srcs))
    print(f'  {em}  <- {\",\".join(uniq)}')
"
echo done
