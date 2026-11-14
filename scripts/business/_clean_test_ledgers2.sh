#!/usr/bin/env bash
# 正确删除测试账本 (文件名带冒号: ofc:OFCP1.json 等)
cd /var/lib/bingdashan-cn
echo "=== 删除测试 ref 账本 (精确) ==="
rm -f "overfitcheck/ofc:OFCP1.json"
rm -f "papercombo/pc:PCT1.json"
rm -f "quantcompute/qc:QCTEST1.json"
rm -f "quantannual/qa:QATEST1.json"
# reportexport/rpx:E2EPAY.json 是早期 E2E 测试, 也清掉 (非真实客户)
rm -f "reportexport/rpx:E2EPAY.json"
echo "  已删"
echo ""
echo "=== 清理后各渠道账本 ==="
for d in overfitcheck papercombo quantcompute quantannual reportexport; do
  echo "  $d/:"; ls "$d"/*.json 2>/dev/null | sed 's/^/    /' || echo "    (空)"
done
echo ""
echo "=== 重读 /api/revenue ==="
systemctl restart bingdashan-cn && sleep 3
curl -s "http://127.0.0.1:8794/api/revenue" | python3 -c "
import json,sys
d=json.load(sys.stdin)
anyreal=False
for c in d['channels']:
    if c.get('revenue_yuan') or c.get('revenue_coin') or c.get('paid_entries'):
        anyreal=True
        print('  %s: 付费条目=%s ¥营收=%s 币营收=%s' % (c['sub'], c.get('paid_entries',0), c.get('revenue_yuan',0), c.get('revenue_coin',0)))
if not anyreal:
    print('  (所有渠道无真实客户收入 — 测试账本已清, 真实收入从下一个付费客户开始)')
print('  存量待收: ¥%s (outreach %s + 对公 %s)' % (d['stock']['total_pending_yuan'], d['stock']['outreach']['amount_yuan'], d['stock']['corporate']['amount_yuan']))
"
echo done
