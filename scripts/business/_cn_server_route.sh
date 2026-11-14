#!/usr/bin/env bash
# 找 CN server.js 路由结构 + 最小加 /api/contact
echo "=== CN server.js 里 /api/track 怎么注册 (路由机制) ==="
grep -nE "api/track|/api/track|apiTrack|case '/api" /opt/bingdashan/server.js 2>/dev/null | head -15
echo ""
echo "=== 找它的路由分发方式 (fetch handler / express / 自研 router) ==="
grep -nE "function (router|route|handle)|routes\[|REGISTRY|endpoint|apiRouter|createServer|http\.createServer|addEventListener.*request" /opt/bingdashan/server.js 2>/dev/null | head -15
echo ""
echo "=== /api/track 的具体实现行号 ==="
grep -nE "track" /opt/bingdashan/server.js 2>/dev/null | head -10
echo done
