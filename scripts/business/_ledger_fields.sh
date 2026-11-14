#!/usr/bin/env bash
# 看真实台账字段结构 (修看板金额字段)
echo "=== outreach_ledger.json 单条真实字段 ==="
python3 -c "import json;d=json.load(open('/opt/bingdashan/data/billing/outreach_ledger.json'));items=d if isinstance(d,list) else d.get('items',[]);print(json.dumps(items[0],ensure_ascii=False)[:400] if items else 'empty')"
echo ""
echo "=== corporate_899.json 单条真实字段 ==="
python3 -c "import json;d=json.load(open('/opt/bingdashan/data/billing/corporate_899.json'));items=d if isinstance(d,list) else (d.get('items') or d.get('orders') or []);print(json.dumps(items[0],ensure_ascii=False)[:400] if items else 'empty')"
echo "done"
