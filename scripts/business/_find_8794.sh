#!/usr/bin/env bash
# 找 8794 端口是谁在跑 + /api/track 真身在哪个文件
echo "=== 1. 8794 端口进程 (nginx proxy 到这) ==="
ss -ltnp 2>/dev/null | grep 8794 || netstat -ltnp 2>/dev/null | grep 8794
echo "=== 2. bingdashan-cn systemd 跑什么 (WorkingDir/ExecStart) ==="
systemctl cat bingdashan-cn 2>/dev/null | grep -iE "ExecStart|WorkingDir|User" | head
echo ""
echo "=== 3. /www/wwwroot/tools-cn 里 /api/track 真身 (它才是 CN 工具站的 node 服务) ==="
grep -rlniE "'/api/track'|\"/api/track\"|api/track|track_" /www/wwwroot/tools-cn.highkingflower.com 2>/dev/null | grep -viE "node_modules|\.git|l_|w2_|p_|index.html" | head
echo "=== 4. 看 tools-cn 的 alipay.js / 独立 track handler 在哪 ==="
ls -1 /www/wwwroot/tools-cn.highkingflower.com/api/track.js 2>/dev/null && echo "  有 api/track.js"
grep -nE "'/api/track'|/api/track|api/track" /www/wwwroot/tools-cn.highkingflower.com/api/*.js 2>/dev/null | head
echo "=== 5. 8794 服务的实际代码目录 (找它的 server 入口) ==="
ps aux 2>/dev/null | grep -iE "8794|bingdashan|node.*tools-cn" | grep -v grep | head -5
echo done
