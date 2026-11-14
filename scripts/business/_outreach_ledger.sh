#!/usr/bin/env bash
# 建"待人工触达台账"(8单manual + 5个trial, 含金额/链接/话术/勾选状态) + 收款自动对账
python3 - <<'PY'
import json, datetime, time
db=json.load(open('/opt/bingdashan/data/db.json'))
now=datetime.datetime.now().isoformat()
# 8 单 manual (有升级链接的实收口径)
manual=[o for o in db.get('orders',[]) if o.get('channel')=='manual' and o.get('status')=='pending']
MAP={'y':('proY',500),'v':('team',299),'q':('pro3',150),'p':('pro',60),'m':('pro',60),'t':('trial',1)}
B='https://tools-cn.highkingflower.com/api/pay'
items=[]
for o in sorted(manual,key=lambda x:-(float(x.get('amount') or 0))):
    plan=o.get('plan'); pp,real=MAP.get(plan,('pro',60))
    vid=str(o.get('visitor') or '').split(':')[-1]
    items.append({'kind':'manual_8','order_id':o.get('id'),'ref':vid,'visitor':o.get('visitor'),
                  'intent':plan,'billed':o.get('amount'),'collect':real,'pay_link':f'{B}?plan={pp}&slug=tool&ref={vid}',
                  'status':'pending_outreach','note':'大额走分期/对公(¥899意向实收¥500), 中小额直接点链接'})
# 5 过期 trial
tl=[t for t in db.get('trialLedger',[]) if isinstance(t,dict) and '127_0_0_1' not in str(t.get('visitor') or '') and 'diag' not in str(t.get('visitor') or '')]
exp=[t for t in tl if (time.time()*1000-(t.get('at') or 0))>7*86400000]
for t in exp:
    vid=str(t.get('visitor') or '').split(':')[-1]
    items.append({'kind':'trial_5','ref':vid,'visitor':t.get('visitor'),'intent':'trial→pro',
                  'billed':1,'collect':60,'pay_link':f'{B}?plan=pro&slug=tool&ref={vid}',
                  'status':'pending_outreach','note':'已过期, 9折 ¥54, 无邮箱需人工补联系方式'})
# 台账落盘 (可反复勾对)
ledger={'generated':now,'items':items,
        'total_collect':sum(i['collect'] for i in items),
        'manual_total':sum(i['collect'] for i in items if i['kind']=='manual_8'),
        'trial_total':sum(i['collect'] for i in items if i['kind']=='trial_5')}
open('/opt/bingdashan/data/billing/outreach_ledger.json','w').write(json.dumps(ledger,ensure_ascii=False,indent=2))
print('=== 待人工触达台账 (共 %d 单, 实收合计 ¥%d) ==='%(len(items),ledger['total_collect']))
print('  manual 8单 实收 ¥%d + trial 5人 实收 ¥%d'%(ledger['manual_total'],ledger['trial_total']))
for i,it in enumerate(items,1):
    flag='🔥' if it['collect']>=299 else ('⚠️' if it['collect']>=150 else '·')
    print(f'  {i}. {flag} [{it["kind"]}] ref={it["ref"]} {it.get("visitor","")} | 意向{it["intent"]} 实收¥{it["collect"]} | {it["note"]}')
print()
print('台账已写: /opt/bingdashan/data/billing/outreach_ledger.json')
PY
echo ""
echo "=== 收款自动对账: 把台账 + 到账监测 合并 (收一笔自动勾掉一笔) ==="
cat > /opt/bingdashan/scripts/ops/outreach_reconcile.sh <<'REC'
#!/usr/bin/env bash
# 对账: 台账里 pending_outreach 的单, 若 db.json 里对应 ref/订单 已变 paid -> 自动勾 collected
python3 - <<'PY'
import json, datetime
db=json.load(open('/opt/bingdashan/data/db.json'))
led=json.load(open('/opt/bingdashan/data/billing/outreach_ledger.json'))
# 建已付款索引
paid_refs=set()
for o in db.get('orders',[]):
    if o.get('paid') is True or o.get('status')=='paid':
        vid=str(o.get('visitor') or '').split(':')[-1]
        paid_refs.add(vid)
        paid_refs.add(o.get('id') or '')
changed=False
for it in led['items']:
    if it['status']=='pending_outreach' and (it['ref'] in paid_refs or it.get('order_id') in paid_refs):
        it['status']='collected'; it['collected_at']=datetime.datetime.now().isoformat(); changed=True
collected=sum(1 for i in led['items'] if i['status']=='collected')
pending=sum(1 for i in led['items'] if i['status']=='pending_outreach')
led['reconciled_at']=datetime.datetime.now().isoformat()
led['collected_count']=collected; led['pending_count']=pending
open('/opt/bingdashan/data/billing/outreach_ledger.json','w').write(json.dumps(led,ensure_ascii=False,indent=2))
amt=sum(i['collect'] for i in led['items'] if i['status']=='collected')
print('  已收款 %d 单 ¥%d | 待触达 %d 单'%(collected,amt,pending))
for i in led['items']:
    if i['status']=='pending_outreach' and i['collect']>=299:
        print('    仍待:', i['ref'], i.get('intent'), '¥'+str(i['collect']), i['pay_link'])
PY
REC
chmod +x /opt/bingdashan/scripts/ops/outreach_reconcile.sh
echo "  对账脚本已建 (收一笔自动勾掉)"
echo "=== 跑一次对账 ==="
bash /opt/bingdashan/scripts/ops/outreach_reconcile.sh
echo done
