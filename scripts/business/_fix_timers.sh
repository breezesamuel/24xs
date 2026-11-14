#!/usr/bin/env bash
# 修三个 timer 真正 active (enable + start, 看为什么之前 inactive)
echo "=== 当前 timer 详细状态 ==="
for t in bd-manual8-watch bd-trial-winback bd-pay-email-watch; do
  echo "--- $t ---"
  systemctl is-enabled $t 2>/dev/null
  systemctl is-active $t 2>/dev/null
  systemctl status $t --no-pager 2>/dev/null | head -4
done
echo ""
echo "=== 重新 enable + start 三个赚钱 timer ==="
for t in bd-manual8-watch bd-trial-winback; do
  systemctl daemon-reload
  systemctl enable $t.timer 2>&1 | head -1
  systemctl restart $t.timer 2>&1 | head -1
  echo "  $t -> $(systemctl is-active $t.timer 2>/dev/null)"
done
echo ""
echo "=== pay-email-watch (现有系统, 确认它的 timer 在不在跑) ==="
systemctl list-timers 2>/dev/null | grep -iE "manual8|trial|pay-email" | head
echo ""
echo "=== 若 timer 文件有语法问题, 看 unit ==="
cat /etc/systemd/system/bd-manual8-watch.timer 2>/dev/null
echo "---"
cat /etc/systemd/system/bd-trial-winback.timer 2>/dev/null
echo done
