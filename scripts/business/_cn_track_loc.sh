#!/usr/bin/env bash
echo "=== handle() 里 /api/track 端点定义 (精确行) ==="
grep -nE "'/api/track'|\"/api/track\"|api/track" /opt/bingdashan/server.js 2>/dev/null | head
echo ""
echo "=== 看 handle() 函数体开头 (880行附近) 怎么 dispatch + 怎么存 kv/file ==="
sed -n '880,905p' /opt/bingdashan/server.js 2>/dev/null
echo ""
echo "=== 找 /api/ 端点处理段 (if url==='.../api/...') ==="
grep -nE "url === '/api/|url==\"/api/|req.url.includes\('/api|pathname.*api/|path === '/api" /opt/bingdashan/server.js 2>/dev/null | head -20
echo done
