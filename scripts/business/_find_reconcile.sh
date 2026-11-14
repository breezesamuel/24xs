#!/usr/bin/env bash
echo "=== 1. bd-reconcile / bd-pay-email-watch timer 跑什么 ==="
systemctl cat bd-reconcile.timer 2>/dev/null | grep -iE 'OnCalendar|OnBoot|Unit=' | head
systemctl cat bd-reconcile.service 2>/dev/null | grep -iE 'ExecStart|WorkingDir' | head
echo "--- 找 reconcile 脚本本体 ---"
find /www /root /opt -maxdepth 4 -iname '*reconcile*' -o -iname '*pay*watch*' 2>/dev/null | grep -vE 'node_modules|\.git' | head
echo "=== 2. '待付' 的统计口径: 搜代码里 pending/unpaid 订单计数 ==="
grep -rnE "待付|pending.*[0-9]+|unpaid|WAIT_BUYER|listByRef|pendingCount" /www/wwwroot/tools-cn.highkingflower.com/api/autoops.js 2>/dev/null | head -12
echo "=== 3. autoops ?a=loop 的 pending 从哪来 (读哪些键) ==="
grep -nE "bds_order|listOrders|orders_by_ref|track_|kvGet\(|dget\(" /www/wwwroot/tools-cn.highkingflower.com/api/autoops.js 2>/dev/null | head -15
echo "done"
