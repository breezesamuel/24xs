#!/usr/bin/env bash
# 摸清 CN 现有的 对公/大额 人工核销系统 (manual-verify + fulfillment), 复用给 ¥899 两单
echo "=== 1. manual-verify.html 的核销端点 (前端调哪个 API) ==="
grep -oE "/v1/[a-z_]+|/api/[a-z_]+|action=[a-z_]+|method: *'[A-Z]+'|fetch\('[^']+'" /opt/bingdashan/web/manual-verify.html 2>/dev/null | sort -u | head -15
echo ""
echo "=== 2. fulfillment.advance 收款核销逻辑 (对公打款->入账) ==="
grep -nE "function advance|advance\(|fulfill|paid:true|幂等|ful-|recordRevenue|入账" /opt/bingdashan/scripts/ops/fulfillment_rehearse.js 2>/dev/null | head -12
echo ""
echo "=== 3. 对公收款台账/端点 (大额打款登记在哪) ==="
grep -rniE "corporate|bank_transfer|bankTransfer|对公打款|大额|manualReceipt|receipt|打款.*到账" /opt/bingdashan/server.js 2>/dev/null | grep -viE "test|probe" | head -10
echo ""
echo "=== 4. 有没有现成"给某单生成对公收款单"的端点 ==="
grep -rniE "invoice|收款单|对公.*单|bank.*receipt|corporate.*order|生成.*收款" /opt/bingdashan/server.js 2>/dev/null | grep -viE "test|probe" | head -10
echo ""
echo "=== 5. 2 单 ¥899 现在的订单状态 (确认还是 pending) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
for o in d.get('orders',[]):
    if o.get('id') in ('mvgevdw6xm1av','mvi21kh7wvntq'):
        print(' ', o.get('id'),'| plan',o.get('plan'),'| ¥',o.get('amount'),'|',o.get('status'),'| visitor',o.get('visitor'))
"
echo done
