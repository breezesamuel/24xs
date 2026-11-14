#!/usr/bin/env bash
# 读 business.js 里 ord 的来源函数 (怎么算 pending=9) + 锁定 9 条 + 出 TSV + 话术
echo "=== business.js: ord / money 统计函数定义 (找 pending 怎么算) ==="
grep -nE "function.*[Mm]oney|ord *=|pending *:|pendingAmount|countPending|sumPending|void_test|voided|filter\(" /opt/bingdashan/scripts/ops/business.js | head -30
echo ""
echo "=== 读 ord 计算逻辑上下文 (160-175 行附近 + 函数体) ==="
sed -n '120,175p' /opt/bingdashan/scripts/ops/business.js
echo ""
echo "=== 按'排除 void_test + 排除 manual + 排除 USD'锁定可挽回的线上真实单 ==="
python -c "
import json, time, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
pend=[o for o in orders if isinstance(o,dict) and o.get('status')=='pending']
# 可挽回线上真实单: 非 manual 渠道(人工线下不算) + CNY 币种 + 非 void_test
recoverable=[o for o in pend if o.get('channel')!='manual' and o.get('currency','CNY')=='CNY']
print('可挽回线上真实单 (排除 manual+USD):', len(recoverable))
now=time.time()
for i,o in enumerate(sorted(recoverable, key=lambda x:(x.get('createdAt') or 0)),1):
    ts=o.get('createdAt') or 0
    age_d=round((now-ts)/86400000,1) if ts else None
    urg='🔥<7d' if (age_d is not None and age_d<7) else ('⚠️<30d' if (age_d is not None and age_d<30) else ('一般<90d' if (age_d is not None and age_d<90) else '陈旧>90d'))
    try: human=datetime.datetime.utcfromtimestamp(ts/1000).strftime('%m-%d %H:%M') if ts else '?'
    except: human='?'
    print(f'  {i}. {o.get(\"id\")} | plan={o.get(\"plan\")} | ¥{o.get(\"amount\")} | ch={o.get(\"channel\")} | {o.get(\"visitor\")} | 创建 {human} ({age_d}d前) | {urg}')
total=sum(float(o.get('amount') or 0) for o in recoverable)
print(f'  合计 ¥{total:.0f} · 40% 挽回 ≈ ¥{total*0.4:.0f}')
"
echo "done"
