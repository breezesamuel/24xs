#!/usr/bin/env bash
# 8 单 manual 待付的可达联系渠道排查 (email 全空, 找别的路径)
echo "=== 1. db.json 里这些 visitor IP 是否有关联邮箱/leads ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
# 目标 8 单的 visitor (去掉 ip: 前缀取 IP)
targets=['101_228_2_131','223_104_5_60','125_85_176_118','101_228_130_101','39_103_144_80']
leads=d.get('leads',[])
print('leads 表条数:', len(leads))
for ld in leads:
    if isinstance(ld,dict):
        s=json.dumps(ld,ensure_ascii=False)
        for t in targets:
            if t in s.replace('_','.'):
                print('  lead 命中:', json.dumps({k:ld.get(k) for k in ('email','phone','ip','visitor','created_at','plan','status') if k in ld}, ensure_ascii=False))
                break
# 邮箱散落在哪
print('--- 全库 email 字段非空的记录数 (mail/visitors/leads) ---')
cnt=0
for key in ('mail','visitors','leads','messages'):
    arr=d.get(key)
    if isinstance(arr,list):
        for x in arr:
            if isinstance(x,dict) and (x.get('email') or x.get('to') or x.get('from')):
                cnt+=1
print('  含邮箱的记录:', cnt)
"
echo ""
echo "=== 2. 支付宝买家信息 (这些 manual 单有没有关联 alipay trade 的买家) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
manual=[o for o in orders if o.get('status')=='pending' and o.get('channel')=='manual']
# 看这些单有没有 out_trade_no / alipay 买家
with_trade=[o for o in manual if o.get('out_trade_no') or o.get('alipay_no') or o.get('buyer')]
print('  manual 单里有 alipay trade 关联的:', len(with_trade))
for o in with_trade[:5]:
    print('   ', json.dumps({k:o.get(k) for k in ('id','out_trade_no','buyer','alipay_no','buyer_email','buyer_nick') if o.get(k)}, ensure_ascii=False))
"
echo ""
echo "=== 3. 访客表 (visitors) 里这些 IP 有没有留邮箱/联系方式 ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
visitors=d.get('visitors',[])
targets={'101.228.2.131','223.104.5.60','125.85.176.118','101.228.130.101','39.103.144.80'}
hit=0
for v in visitors:
    if isinstance(v,dict):
        ip=str(v.get('ip') or '')
        if ip in targets:
            hit+=1
            keep={k:v.get(k) for k in ('ip','email','ref','visitor','page','at') if v.get(k)}
            if any(k in keep for k in ('email','ref')):
                print('  访客带邮箱/ref:', json.dumps(keep, ensure_ascii=False))
print('  目标 IP 命中访客记录:', hit, '条')
"
echo "done"
