#!/usr/bin/env bash
# 诊断: CN node 是否卡死 (GET 通不通? POST 才卡?)
echo "=== GET /api/config (无 body, 应快速) ==="
curl -sk "https://tools-cn.highkingflower.com/api/config" --max-time 15 -o /dev/null -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
echo "=== GET /api/pay (无 body, 看是否 200 收银台 form) ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay?plan=trial&ref=GETPROBE&amount=1" --max-time 15 -o /dev/null -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
echo "=== CN node 进程 + 最近日志 ==="
ps aux | grep -E "site_cn_server|bingdashan" | grep -v grep | head -3
tail -5 /www/wwwlogs/bingdashan-cn.error.log 2>/dev/null
echo "=== systemctl 状态 ==="
systemctl is-active bingdashan-cn
echo "done"
