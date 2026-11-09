#!/bin/bash
# 深挖审计门"钱漏" + 全系统健康状态
echo "=== 1. 审计门那笔'钱漏' mvklhggzx6pz0 的完整订单 ==="
python3 - /opt/bingdashan/data/db.json <<'PYEOF'
import json,sys
db=json.load(open(sys.argv[1]))
o=None
for it in db.get("orders",[]):
    if it.get("id")=="mvklhggzx6pz0": o=it;break
if o:
    print("  订单:", json.dumps(o,ensure_ascii=False,indent=2))
    print("  解读: status=%s paid=%s channel=%s amount=%s trial=%s" % (
        o.get("status"),o.get("paid"),o.get("channel"),o.get("amount"),o.get("trial")))
PYEOF
echo
echo "=== 2. 为什么审计门判'钱漏' (ledger_audit 的判定逻辑) ==="
grep -nE "钱漏|已付未记账|已付但没记账|漏|revenue|记账" /opt/bingdashan/scripts/ops/ledger_audit.py 2>/dev/null | head -15
echo
echo "=== 3. 收款通道形态: 现在是商户网关(支付宝)还是个人收款码? ==="
grep -nE "收款码|商户网关|alipay|personal|manual|高风险" /opt/bingdashan/scripts/ops/ledger_audit.py 2>/dev/null | head -10
echo
echo "=== 4. 全部 bingdashan* 服务健康总览 ==="
for s in bingdashan-cn bd-audit bd-pay-email-watch agent-auditor bds-alert-relay bingdashan-spider; do
  st=$(systemctl is-active "$s" 2>/dev/null)
  echo "  $s: $st"
done
echo
echo "=== 5. 是否有 failed 的 bingdashan 相关服务 ==="
systemctl list-units --state=failed --type=service 2>/dev/null | grep -iE "bds|bingdashan|bd-" | head
