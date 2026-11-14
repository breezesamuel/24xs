#!/usr/bin/env bash
F=/www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs
echo "=== 当前 isAlipay 行 (精确) ==="
grep -nE 'isAlipay' "$F" | head -3
echo "=== 当前 track 路由块 (精确, 看缩进/字符) ==="
grep -nE 'sub === "track"|loadHandler\("api/track' "$F" | head -3
echo "=== 看第 162-175 行 cat -A (查 CRLF/特殊字符) ==="
sed -n '162,176p' "$F" | cat -A | head -20
echo done
