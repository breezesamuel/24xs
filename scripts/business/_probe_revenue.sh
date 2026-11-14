#!/usr/bin/env bash
# 确认 /api/admin/dashboard 现状 + 能否读真台账 (决定 revenue.html 数据源)
echo "=== /api/admin/dashboard 现在返回什么 (CN 127.0.0.1:8794) ==="
curl -s "http://127.0.0.1:8794/api/admin/dashboard" 2>/dev/null | head -c 600
echo ""
echo ""
echo "=== alipay.js 里有没有 /api/admin/dashboard 实现 ==="
grep -n "admin/dashboard\|admin_dashboard\|/api/admin" /www/wwwroot/tools-cn.highkingflower.com/api/alipay.js 2>/dev/null | head -8
echo ""
echo "=== 台账真实路径 + 可读性 ==="
ls -la /opt/bingdashan/data/billing/outreach_ledger.json /opt/bingdashan/data/billing/corporate_899.json 2>/dev/null
echo "=== 9 渠道账本目录 (谁付过钱) ==="
ls /var/lib/bingdashan-cn/ 2>/dev/null | grep -iE "reportexport|strategyapi|marketdata|strategyhosting|overfitcheck|whitebox|papercombo|quantcompute|quantannual|cashback|bounty" | head -20
echo "done"
