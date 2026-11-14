#!/usr/bin/env bash
# 找"经营日报"生成器 (它统计出 6已付/9待付, 必有数据源)
echo "=== 1. CN 上找日报/统计相关脚本 + cron ==="
grep -rlnE "经营日报|新订单|成交.*元|待付|新线索|热搜" /www/wwwroot/tools-cn.highkingflower.com /var/lib/bingdashan-cn /etc/cron* /etc/systemd/system 2>/dev/null | grep -vE 'node_modules|\.git' | head -15
echo "=== 2. cron / timer (每天 8 点) ==="
crontab -l 2>/dev/null | grep -iE "daily|8:00|report|日报" | head
ls /etc/systemd/system/*.timer 2>/dev/null | head
systemctl list-timers 2>/dev/null | head -8
echo "=== 3. 找 '已付 6 / 待付 9' 的统计口径代码 ==="
grep -rlnE "待付|pending.*order|orders.*pending|bds_order|listByRef" /www/wwwroot/tools-cn.highkingflower.com/api 2>/dev/null | head
echo "done"
