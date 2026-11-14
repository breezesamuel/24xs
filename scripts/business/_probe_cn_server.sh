#!/usr/bin/env bash
# 看 CN server 怎么 serve 静态页 + 有没有读账本的接口 (决定 revenue.html 怎么取真数据)
echo "=== site_cn_server.mjs 路由/静态页/账本读取 ==="
grep -nE "get\.html|channels|readFile|sendFile|/api/|route|router|\.html|ledger" /www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs 2>/dev/null | head -40
echo ""
echo "=== 现有静态页清单 (CN 站点根目录) ==="
ls /www/wwwroot/tools-cn.highkingflower.com/*.html 2>/dev/null | head -20
echo ""
echo "=== 是否已有读账本的 /api (outreach_ledger 等) ==="
grep -rln "outreach_ledger\|corporate_899\|billing" /www/wwwroot/tools-cn.highkingflower.com/*.js /www/wwwroot/tools-cn.highkingflower.com/*.mjs 2>/dev/null | head -8
echo "done"
