#!/usr/bin/env bash
# 同步 revenue.html + /api/revenue 到 CN + 实测读真台账
cd /www/wwwroot/tools-cn.highkingflower.com
node --check api/alipay.js && echo "  语法 OK"
systemctl restart bingdashan-cn && sleep 3
echo "  CN: $(systemctl is-active bingdashan-cn)"
echo ""
echo "=== 实测 /api/revenue (读真台账 + 渠道账本, 不造假) ==="
curl -s "http://127.0.0.1:8794/api/revenue" | python3 -c "
import json,sys
d=json.load(sys.stdin)
if not d.get('ok'):
    print('  接口失败:', d); sys.exit(0)
s=d['stock']
print('  存量待收: outreach %s单¥%s + 对公 %s单¥%s = 合计¥%s (待收≠已到账)' % (s['outreach']['pending'],s['outreach']['amount_yuan'],s['corporate']['pending'],s['corporate']['amount_yuan'],s['total_pending_yuan']))
print('  渠道账本:')
for c in d['channels']:
    print('    %-22s 有账本=%s 付费条目=%s 余额度=%s ¥营收=%s 币营收=%s' % (c.get('sub','?'), c.get('has_ledger'), c.get('paid_entries',0), c.get('quota',0), c.get('revenue_yuan',0), c.get('revenue_coin',0)))
print('  渠道合计 ¥营收=%s 币营收=%s' % (d['total_channel_revenue_yuan'], d['total_channel_revenue_coin']))
print('  诚实边界:', d['honesty'])
"
echo ""
echo "=== revenue.html 静态页 (CN serve) ==="
curl -s -o /dev/null -w "  /revenue.html HTTP %{http_code}\n" "http://127.0.0.1:8794/revenue.html"
echo done
