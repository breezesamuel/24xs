#!/usr/bin/env bash
# 读 site_ledger.summarizeOrders 的 pending 统计逻辑 + 锁定 9 条 + 出 TSV + 3 套话术
echo "=== site_ledger.js: summarizeOrders 怎么算 pending ==="
SL=/opt/bingdashan/packages/core/billing/site_ledger.js
[ -f "$SL" ] || SL=$(find /opt/bingdashan/packages -name 'site_ledger*' 2>/dev/null | head -1)
echo "文件: $SL"
grep -nE "pending|summarizeOrders|void_test|voided|selfTest|status|paid|count" "$SL" 2>/dev/null | head -40
echo ""
echo "=== summarizeOrders 函数体 ==="
awk '/function summarizeOrders|summarizeOrders *=|function summarizeOrders/,/^}/' "$SL" 2>/dev/null | head -60
echo ""
echo "=== 直接复算: 用 site_ledger 的真实口径算 pending 数 + 锁定 9 条 id ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
# 真实口径假设: pending = status=='pending' 且 未 voided/void_test 且 是真实客户(非 selfTest/压测)
# 排除 void_test 状态(已在 status=pending 里天然排除); 排除自测/本机探针 visitor
def is_test(o):
    v=str(o.get('visitor') or '')
    r=str(o.get('voidReason') or '')
    return ('void_test' in str(o.get('status'))) or ('selfTest' in str(o.get('selfTest'))) or ('127_0_0_1' in v and not o.get('channel'))
pend=[o for o in orders if isinstance(o,dict) and o.get('status')=='pending']
real=[o for o in pend if not is_test(o)]
print('status=pending 全部:', len(pend))
print('排除自测/本机后真实待付:', len(real))
for o in sorted(real, key=lambda x:(x.get('createdAt') or 0)):
    print('  ', o.get('id'),'| plan',o.get('plan'),'| ¥',o.get('amount'),o.get('currency'),'| ch',o.get('channel'),'|',o.get('visitor'))
"
echo "done"
