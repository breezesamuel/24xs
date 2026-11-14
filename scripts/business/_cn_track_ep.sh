#!/usr/bin/env bash
# 找 CN server.js 里 /api/track 端点的定义 (它一定注册在某处, 可能是 _ENDPOINT_REGISTRY + 一个 handler)
echo "=== 搜 track 端点注册 (registry.add / 路由映射 含 track) ==="
grep -nE "track" /opt/bingdashan/server.js 2>/dev/null | grep -iE "registry|route|endpoint|register|handle|'/api|\"/api|add\(|= *function|=>" | head -20
echo ""
echo "=== 搜 '/api/' 字符串出现 (看 CN 到底有没有 /api/track 路由, 还是全走 /v1) ==="
grep -nE "'/api/|\"/api/" /opt/bingdashan/server.js 2>/dev/null | head -20
echo ""
echo "=== 搜 track 端点 handler (可能叫 trackStats / handleTrack) ==="
grep -nE "function.*[Tt]rack|trackStats|handleTrack|apiTrack|/api/track" /opt/bingdashan/server.js 2>/dev/null | head
echo ""
echo "=== 找 'track_' 键写入 (落盘逻辑在哪) ==="
grep -nE "track_|track_day|dayKey|track_day" /opt/bingdashan/server.js 2>/dev/null | head
echo done
