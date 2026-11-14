#!/usr/bin/env bash
echo "=== 1. closure 订单账本 orders.json ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/billing/orders.json'))
print('类型:', type(d).__name__, '| 条数:', len(d) if hasattr(d,'__len__') else '?')
if isinstance(d,list):
    from collections import Counter
    print('状态分布:', dict(Counter(o.get('status','?') for o in d if isinstance(o,dict))))
    print('--- 前 15 条 ---')
    for o in d[:15]:
        if isinstance(o,dict):
            print('  ', {k:o.get(k) for k in ('order_no','out_trade_no','ref','user','plan','amount','status','created_at','slug') if k in o})
elif isinstance(d,dict):
    print('顶层键:', list(d.keys())[:20])
" 2>&1
echo ""
echo "=== 2. funnel.jsonl (漏斗事件, 找待付) ==="
echo "总行数: $(wc -l < /opt/bingdashan/data/billing/funnel.jsonl 2>/dev/null)"
echo "--- 含 pending/wait/unpaid 的行 ---"
grep -iE '"(status|stage|event)".*"(pending|waiting|unpaid|待付|created|notpaid)"' /opt/bingdashan/data/billing/funnel.jsonl 2>/dev/null | tail -20 | head -12
echo "--- 最近 8 行 (漏斗最新状态) ---"
tail -8 /opt/bingdashan/data/billing/funnel.jsonl 2>/dev/null
