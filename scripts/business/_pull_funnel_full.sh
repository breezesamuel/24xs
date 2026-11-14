#!/usr/bin/env bash
# 读 funnel.jsonl 全量 + stage 分布 + 找"待付 9 单"的真实统计口径
echo "=== 1. funnel.jsonl 全量 (49 行) 按 stage 分类 ==="
python -c "
import json, collections
stages=collections.Counter(); created=[]; activated=0; by_id={}
for line in open('/opt/bingdashan/data/billing/funnel.jsonl'):
    line=line.strip()
    if not line: continue
    try: e=json.loads(line)
    except: continue
    st=e.get('stage','?')
    stages[st]+=1
    if st=='created': created.append(e)
    if st in ('activate','activated'): activated+=1
    oid=(e.get('meta') or {}).get('orderId') or e.get('orderId')
    if oid: by_id[oid]=e
print('stage 分布:', dict(stages))
print('created(未激活) 事件数:', len(created))
print('activate(已激活) 事件数:', activated)
print()
print('--- 全部 created 事件 (可能=待付订单) ---')
for e in created:
    print('  ', json.dumps({k:e.get(k) for k in ('ts','stage','actorId','channel','value','meta') if k in e}, ensure_ascii=False))
"
echo ""
echo "=== 2. 找日报/统计里'待付 9'的生成代码 ==="
grep -rlnE "待付|pending_orders|待付订单|unpaid" /opt/bingdashan --include="*.js" --include="*.mjs" --include="*.json" 2>/dev/null | grep -v node_modules | head -12
echo "--- 日报/经营报告生成器 (找输出'6已付/9待付'的) ---"
grep -rlnE "已付|成交.*元|经营日报|每日.*报|daily_report|dailyreport" /opt/bingdashan --include="*.js" --include="*.mjs" 2>/dev/null | grep -v node_modules | head -12
echo ""
echo "=== 3. 支付宝网关查单 (alipay trade.query 查待付) 的脚本/端点 ==="
grep -rnE "trade\.query|trade_query|WAIT_BUYER_PAY|待付|query.*pending" /opt/bingdashan/scripts 2>/dev/null | grep -v node_modules | head -12
echo ""
echo "=== 4. 看 db.json 里是否有独立订单/pending 表 ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
print('db.json 顶层键:', list(d.keys())[:30] if isinstance(d,dict) else type(d).__name__)
if isinstance(d,dict):
    for k,v in d.items():
        if isinstance(v,list):
            print('  列表', k, ':', len(v), '条')
"
echo "done"
