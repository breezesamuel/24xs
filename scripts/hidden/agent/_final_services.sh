#!/bin/bash
# 让两个 oneshot 门服务反映干净状态, 确认不再 failed
echo "=== 重启 bd-audit + bd-reconcile (oneshot, 跑一次核对) ==="
systemctl restart bd-audit 2>&1
sleep 1
echo "  bd-audit: $(systemctl is-active bd-audit 2>/dev/null)"
systemctl restart bd-reconcile 2>&1
sleep 1
echo "  bd-reconcile: $(systemctl is-active bd-reconcile 2>/dev/null)"
echo
echo "=== 这两个 oneshot 是 timer 触发的, 手动 restart 跑一次即结束 ==="
echo "=== 验证: 它们的 timer 在调度吗? ==="
for t in bd-audit bd-reconcile; do
  [ -f "/etc/systemd/system/${t}.timer" ] && echo "  ${t}.timer: $(systemctl is-active ${t}.timer 2>/dev/null)"
done
echo
echo "=== 全部 bingdashan 相关服务最终健康总览 ==="
for s in bingdashan bingdashan-cn bd-audit bd-reconcile bd-pay-email-watch agent-auditor bds-alert-relay bingdashan-spider; do
  echo "  $s: $(systemctl is-active $s 2>/dev/null)"
done
echo
echo "=== 最终对账/审计结论 ==="
cd /opt/bingdashan
echo -n "  audit: "; python3 scripts/ops/ledger_audit.py 2>&1 | grep -E "门禁通过|门禁未通过" | head -1
echo -n "  reconcile: "; /usr/local/bin/node scripts/ops/reconcile.js 2>&1 | grep -E "真实到账|净额|✘" | head -3
