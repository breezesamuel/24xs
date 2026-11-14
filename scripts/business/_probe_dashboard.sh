#!/usr/bin/env bash
# 看 dashboard.html 现有内容 + bds-engines.js 怎么读账本 (复用真实数据源)
echo "=== dashboard.html 读什么 (前60行 + 关键 fetch/字段) ==="
head -60 /www/wwwroot/tools-cn.highkingflower.com/dashboard.html 2>/dev/null
echo "..."
grep -nE "fetch\(|/api/|outreach|corporate|ledger|revenue|amount|status" /www/wwwroot/tools-cn.highkingflower.com/dashboard.html 2>/dev/null | head -25
echo ""
echo "=== bds-engines.js 读账本的方式 (有没有现成可复用接口) ==="
grep -nE "outreach_ledger|corporate_899|billing|readFile|/api/|module\.exports|function .*[Ll]edger|fetch" /www/wwwroot/tools-cn.highkingflower.com/bds-engines.js 2>/dev/null | head -30
echo "done"
