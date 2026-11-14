#!/usr/bin/env bash
# 拉 8 单 manual 大单 (¥2697 存量可收款) 的完整字段 + 出催收清单 + 逐单话术
python -c "
import json, time, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
manual=[o for o in orders if isinstance(o,dict) and o.get('status')=='pending' and o.get('channel')=='manual']
print('manual 渠道 pending 单数:', len(manual))
now=time.time()
rows=[]
for o in sorted(manual, key=lambda x: -(float(x.get('amount') or 0))):
    ts=o.get('createdAt') or 0
    age_d=round((now-ts)/86400000,1) if ts else None
    try: human=datetime.datetime.utcfromtimestamp(ts/1000).strftime('%m-%d') if ts else '?'
    except: human='?'
    rows.append({'id':o.get('id'),'plan':o.get('plan'),'amt':float(o.get('amount') or 0),'cur':o.get('currency','CNY'),
      'visitor':o.get('visitor'),'email':o.get('email'),'created':human,'age_d':age_d,
      'months':o.get('months'),'trial':o.get('trial')})
total=sum(r['amt'] for r in rows)
print('合计: ¥%.0f'%total)
print()
print('=== 按金额降序 催收清单 ===')
for i,r in enumerate(rows,1):
    urg='🔥大单' if r['amt']>=899 else ('⚠️中大' if r['amt']>=269 else '一般')
    print(f'  {i}. {r[\"id\"]} | {r[\"plan\"]} | ¥{r[\"amt\"]:.0f} | {r[\"months\"]}月 | visitor={r[\"visitor\"]} | email={r[\"email\"] or \"(无)\"} | {r[\"created\"]} ({r[\"age_d\"]}d) | {urg}')
print()
print('=== 逐单催收话术 (按金额/联系人类型匹配) ===')
plan_name={'m':'月度','v':'年度','y':'年付','q':'季度','p':'专业版','t':'7天试用','default':'会员'}
for r in rows:
    pn=plan_name.get(r['plan'],r['plan'])
    contact = r['email'] if r['email'] else (r['visitor'] or '')
    if r['amt']>=899:
        msg=f\"【丙大山】您意向的 {pn}会员(¥{r['amt']:.0f}) 我们为您保留名额。大额订单支持分期/对公, 专属客服 1对1 协助开通 + 赠送 30 天优先支持。回电/回复我帮您锁定本季最低价。\"
        chan='邮件/电话 (大额)'
    elif r['amt']>=269:
        msg=f\"【丙大山】您选的 {pn}会员(¥{r['amt']:.0f}) 还差最后一步。现在完成享 8 折 + 免费回测报告(C3)一份, 48h 有效。\"
        chan='微信/邮件'
    else:
        msg=f\"【丙大山】您的 {pn} 订单(¥{r['amt']:.0f}) 待支付, 小额 7 天体验可立减 ¥5。\"
        chan='短信/微信'
    print(f'  [{r[\"id\"]} {pn} ¥{r[\"amt\"]:.0f}] 联系: {contact} ({chan})')
    print(f'    {msg}')
"
echo ""
echo "=== 写 TSV (可供群发/CRM 导入) ==="
python -c "
import json, time, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
manual=[o for o in orders if isinstance(o,dict) and o.get('status')=='pending' and o.get('channel')=='manual']
now=time.time()
lines=['rank\tid\tplan\tamount\tcurrency\tmonths\tvisitor\temail\tcreated\tage_days']
for i,o in enumerate(sorted(manual,key=lambda x:-(float(x.get('amount') or 0))),1):
    ts=o.get('createdAt') or 0
    age=round((now-ts)/86400000,1) if ts else ''
    lines.append(f\"{i}\t{o.get('id')}\t{o.get('plan')}\t{o.get('amount')}\t{o.get('currency','CNY')}\t{o.get('months')}\t{o.get('visitor')}\t{o.get('email') or ''}\t{ts}\t{age}\")
open('/opt/bingdashan/data/billing/manual_pending.tsv','w').write('\n'.join(lines)+'\n')
print('  已写 /opt/bingdashan/data/billing/manual_pending.tsv (%d 单)'%len(manual))
"
echo done
