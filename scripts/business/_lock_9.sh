#!/usr/bin/env bash
# 拉全 21 条 pending 的完整字段 + 按 business.js 口径精确锁定"9 单" + 时间戳转可读
python -c "
import json, time, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
pend=[o for o in orders if isinstance(o,dict) and str(o.get('status','')).lower()=='pending']
print('=== 全部 21 条 pending 完整字段 (createdAt 转可读) ===')
for o in sorted(pend, key=lambda x: x.get('createdAt') or x.get('at') or 0):
    ts=o.get('createdAt') or o.get('at') or 0
    try: human=datetime.datetime.utcfromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M') if ts else '?'
    except: human='?'
    print(json.dumps({
      'id':o.get('id'),'plan':o.get('plan'),'amt':o.get('amount'),'cur':o.get('currency'),
      'status':o.get('status'),'ch':o.get('channel'),'visitor':o.get('visitor'),
      'invitedBy':o.get('invitedBy'),'trial':o.get('trial'),'months':o.get('months'),
      'created':human,'out_trade_no':o.get('out_trade_no'),'ref':o.get('ref'),
      **{k:o[k] for k in o if k in ('note','memo','source','email','phone','user') },
    }, ensure_ascii=False))
print()
print('=== 按 business.js 口径锁定 9 单 ===')
# business.js 排除 void_test; 真实待付 = pending 且非 manual 探针; 统计 alipay 渠道真实客户单
alipay_real=[o for o in pend if o.get('channel')=='alipay']
manual=[o for o in pend if o.get('channel')=='manual']
nochan=[o for o in pend if not o.get('channel')]
print(f'  channel=alipay 的 pending: {len(alipay_real)} 单')
print(f'  channel=manual 的 pending: {len(manual)} 单 (manual=人工/线下, 不走挽回话术)')
print(f'  无 channel 的 pending: {len(nochan)} 单')
print()
print('  -> 9 单 = alipay 渠道 pending (可挽回的真实线上待付) 或前 9 条 by createdAt')
print()
print('=== 9 单明细 (alipay 渠道, 按创建时间倒序, 紧急度) ===')
now=time.time()
alipay_sorted=sorted(alipay_real, key=lambda x:(x.get('createdAt') or x.get('at') or 0))
for i,o in enumerate(alipay_sorted,1):
    ts=o.get('createdAt') or o.get('at') or 0
    age_h = round((now-ts)/3600,1) if ts else None
    urg='🔥<24h' if (age_h is not None and age_h<24) else ('⚠️<7d' if (age_h is not None and age_h<7*24) else '一般')
    try: human=datetime.datetime.utcfromtimestamp(ts/1000).strftime('%m-%d %H:%M') if ts else '?'
    except: human='?'
    print(f'  {i}. {o.get(\"id\")} | plan={o.get(\"plan\")} | ¥{o.get(\"amount\")} | {o.get(\"visitor\") or \"(无visitor)\"} | 创建 {human} ({age_h}h前) | {urg}')
print()
total=sum(float(o.get('amount') or 0) for o in alipay_real)
print(f'  9 单名义合计 ¥{total:.0f} · 按 40% 挽回率 预期 ≈ ¥{total*0.4:.1f}')
"
echo ""
echo "=== business.js 里 ordersPending 的精确过滤条件 (找怎么从 21 算到 9) ==="
grep -nE "ordersPending|pendingAmount|ordersTotal|ordersPaid|filter.*pending|status.*pending" /opt/bingdashan/scripts/ops/business.js | head -20
echo "done"
