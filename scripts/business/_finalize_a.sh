#!/usr/bin/env bash
# A 收尾: 按 site_ledger 口径锁定未付订单 + 出 /tmp/pending_9.tsv + 3 套个性化话术 + 收入估算
python -c "
import json, time, datetime, os
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
# site_ledger 口径: pending = paid !== true (即未付款, 含 status=pending 且非 void_test 的真实待付)
# void_test 是自测单(paid 可能也非 true 但 voided), 排除; 排除 selfTest/synthetic
def is_excl(o):
    if o.get('status')=='void_test': return True
    if o.get('voided') or o.get('selfTest') or o.get('synthetic'): return True
    v=str(o.get('visitor') or '')
    return ('127_0_0_1' in v) and not o.get('channel')  # 本机探针且无线上渠道
pending=[o for o in orders if isinstance(o,dict) and o.get('paid') is not True and not is_excl(o)]
print('=== 锁定未付订单 (site_ledger 口径: paid!==true, 排除 void_test/自测/本机探针) ===')
print('数量:', len(pending))
now=time.time()
plan_name={'t':'7天试用','m':'月度会员','v':'年度会员','q':'季度会员','y':'年付会员','p':'专业版','default':'会员'}
rows=[]
for o in sorted(pending, key=lambda x:(x.get('createdAt') or 0)):
    ts=o.get('createdAt') or 0
    age_d=round((now-ts)/86400000,1) if ts else 999
    if age_d<7: urg='URGENT_LT7D'
    elif age_d<30: urg='URGENT_LT30D'
    elif age_d<90: urg='NORMAL'
    else: urg='STALE_GT90D'
    try: human=datetime.datetime.utcfromtimestamp(ts/1000).strftime('%m-%d %H:%M') if ts else '?'
    except: human='?'
    rows.append({
      'id':o.get('id'),'visitor':o.get('visitor') or '','channel':o.get('channel') or 'none',
      'plan':o.get('plan'),'plan_name':plan_name.get(o.get('plan'),o.get('plan') or '?'),
      'amount':o.get('amount'),'currency':o.get('currency','CNY'),'created':human,'age_d':age_d,'urgency':urg
    })
    print(f'  {o.get(\"id\")} | {o.get(\"visitor\")} | ch={o.get(\"channel\") or \"-\"} | {plan_name.get(o.get(\"plan\"),o.get(\"plan\"))} | ¥{o.get(\"amount\")}{o.get(\"currency\",\"CNY\")} | {human} ({age_d}d前) | {urg}')
# TSV
out='F:/opt_bds_pending.tsv' if False else None
tsv_lines=['rank\tid\tvisitor\tchannel\tplan\tplan_name\tamount\tcurrency\tcreated\tage_days\turgency']
for i,r in enumerate(rows,1):
    tsv_lines.append(f'{i}\t{r[\"id\"]}\t{r[\"visitor\"]}\t{r[\"channel\"]}\t{r[\"plan\"]}\t{r[\"plan_name\"]}\t{r[\"amount\"]}\t{r[\"currency\"]}\t{r[\"created\"]}\t{r[\"age_d\"]}\t{r[\"urgency\"]}')
open('/opt/bingdashan/data/billing/pending_orders.tsv','w').write('\n'.join(tsv_lines)+'\n')
total=sum(float(r['amount'] or 0) for r in rows if r['currency']=='CNY')
print()
print(f'=== 收入估算: 未付 {len(rows)} 单 · CNY 合计 ¥{total:.0f} · 按 40% 挽回率 预期 ≈ ¥{total*0.4:.0f}')
print('TSV 已写: /opt/bingdashan/data/billing/pending_orders.tsv')
print()
print('=== 3 套个性化挽回话术 (按紧急度分层, 直接可用) ===')
print()
print('【模板 A · 紧急(<7天, 刚下单未付) 短信/微信】')
for r in rows:
    if r['urgency']=='URGENT_LT7D':
        print(f'  → {r[\"id\"]}({r[\"visitor\"]}): 您刚选的 {r[\"plan_name\"]}(¥{r[\"amount\"]}) 还没付, 名额保留 24h, 现在完成首单立减 ¥5, 7 天解锁全部工具。👉[支付链接]')
print()
print('【模板 B · 次紧急(7-30天) 邮件/微信】')
for r in rows:
    if r['urgency']=='URGENT_LT30D':
        print(f'  → {r[\"id\"]}({r[\"visitor\"]}): 您 {r[\"created\"]} 下单的 {r[\"plan_name\"]}(¥{r[\"amount\"]}) 一直没收尾。我们给您留了 48h 优惠窗, 补一句支付方式或改期都行, 别错过本季最低价。')
print()
print('【模板 C · 温和(>30天/陈旧, 批量唤醒) 邮件】')
for r in rows:
    if r['urgency'] in ('NORMAL','STALE_GT90D'):
        print(f'  → {r[\"id\"]}({r[\"visitor\"]}): 好久没见。您之前意向的 {r[\"plan_name\"]} 最近上新了 3 个工具 + 回测报告导出(C3), 老用户回归享 8 折。要不要我帮您留着?')
"
echo "done"
