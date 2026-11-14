#!/usr/bin/env bash
# 清掉 C7/C9/C10/C12 的测试账本 (我实测留下的脏数据, 非真实客户), 让 /api/revenue 只显示真收入
# 测试 ref 特征: OFCP1/PCT1/QCTEST1/QATEST1 等 (非真实客户 ref)
cd /var/lib/bingdashan-cn
echo "=== 清理前: 各渠道账本文件 ==="
for d in overfitcheck papercombo quantcompute quantannual whitebox reportexport strategyapi marketdata strategyhosting; do
  echo "  $d/:"; ls "$d"/*.json 2>/dev/null | sed 's/^/    /'
done
echo ""
echo "=== 删除测试 ref 的账本 (OFCP1/PCT1/QCTEST1/QATEST1/OFC_/PC_/QC_/QAA_ 前缀) ==="
# 精确按测试 ref 删 (不误伤真实客户)
rm -f overfitcheck/ofc_OFCP1.json overfitcheck/ofc_OFC_.json
rm -f papercombo/pc_PCT1.json papercombo/pc_PC_.json
rm -f quantcompute/qc_QCTEST1.json quantcompute/qc_QC_.json quantcompute/qc_TEST*.json
rm -f quantannual/qa_QATEST1.json quantannual/qa_QA_.json quantannual/qa_QAA*.json
echo "  已删测试账本"
echo ""
echo "=== 清理后: 各渠道账本文件 (应只剩真实客户 ref) ==="
for d in overfitcheck papercombo quantcompute quantannual; do
  echo "  $d/:"; ls "$d"/*.json 2>/dev/null | sed 's/^/    /' || echo "    (空)"
done
echo ""
echo "=== 重读 /api/revenue 确认渠道¥营收回落到真实值 ==="
systemctl restart bingdashan-cn && sleep 3
curl -s "http://127.0.0.1:8794/api/revenue" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for c in d['channels']:
    if c.get('revenue_yuan') or c.get('revenue_coin') or c.get('paid_entries'):
        print('  %s: 付费条目=%s ¥营收=%s 币营收=%s' % (c['sub'], c.get('paid_entries',0), c.get('revenue_yuan',0), c.get('revenue_coin',0)))
print('  渠道合计 ¥营收=%s (已去测试账本)' % d['total_channel_revenue_yuan'])
"
echo done
