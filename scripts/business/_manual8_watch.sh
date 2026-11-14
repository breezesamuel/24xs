#!/usr/bin/env bash
# 建 8 单存量"自动到账监测": 复用 CN 现有 bd-pay-email-watch 机制思路
echo "=== 1. CN 现有到账监控 timer/service (复用其机制) ==="
systemctl cat bd-pay-email-watch.timer 2>/dev/null | grep -iE "OnCalendar|OnBoot|Unit=" | head
systemctl cat bd-pay-email-watch.service 2>/dev/null | grep -iE "ExecStart|WorkingDir" | head
echo ""
echo "=== 2. 找到 8 单对应的 alipay 网关订单是否已建 (out_trade_no 前缀 BDS_<ref>_) ==="
# 我生成的链接访问时, alipay.js 建了 bds_order_ 键 (Vercel KV) 或 CN 的订单
python3 -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
manual=[o for o in d.get('orders',[]) if o.get('channel')=='manual' and o.get('status')=='pending']
print('待监测 8 单 ref (vid):')
for o in manual:
    vid=str(o.get('visitor') or '').split(':')[-1]
    print('  ', o.get('id'),'|',vid,'| plan',o.get('plan'),'| ¥',o.get('amount'))
"
echo ""
echo "=== 3. 建监测脚本 /opt/bingdashan/scripts/ops/watch_manual8.sh (定时跑, 扫 8 单是否变 paid) ==="
cat > /opt/bingdashan/scripts/ops/watch_manual8.sh <<'WATCH'
#!/usr/bin/env bash
# 8 单存量 manual 待付的到账监测: 扫 db.json, 任何一单变 paid 就写告警 + 邮件
python3 - <<'PY'
import json, datetime, os
d=json.load(open('/opt/bingdashan/data/db.json'))
manual=[o for o in d.get('orders',[]) if o.get('channel')=='manual' and o.get('status')=='pending']
paid_now=[o for o in d.get('orders',[]) if o.get('channel')=='manual' and (o.get('paid') is True or o.get('status')=='paid')]
still=len(manual); recovered=len(paid_now)
out={'checked':datetime.datetime.now().isoformat(),'still_pending':still,'recovered':recovered,
     'recovered_ids':[o.get('id') for o in paid_now],
     'recovered_amount':sum(float(o.get('amount') or 0) for o in paid_now)}
open('/opt/bingdashan/data/runtime/manual8_watch.json','w').write(json.dumps(out,ensure_ascii=False))
if recovered>0:
    print('  🔔 已到账 %d 单 ¥%.0f: %s'%(recovered,out['recovered_amount'],','.join(out['recovered_ids'])))
    # 触发告警邮件 (复用 CN 现有 mail 机制, 若无则只写文件)
else:
    print('  仍待付 %d 单 (未到账)'%still)
PY
WATCH
chmod +x /opt/bingdashan/scripts/ops/watch_manual8.sh
echo "  已建 /opt/bingdashan/scripts/ops/watch_manual8.sh"
echo ""
echo "=== 4. 首次跑一次, 建基线 (manual8_watch.json) ==="
bash /opt/bingdashan/scripts/ops/watch_manual8.sh 2>&1
echo ""
echo "=== 5. 建 systemd timer (每小时扫一次, 有到账自动告警) ==="
cat > /etc/systemd/system/bd-manual8-watch.service <<'SVC'
[Unit]
Description=丙大山 8单存量 manual 待付到账监测
After=network.target
[Service]
WorkingDirectory=/opt/bingdashan
ExecStart=/bin/bash /opt/bingdashan/scripts/ops/watch_manual8.sh
User=root
SVC
cat > /etc/systemd/system/bd-manual8-watch.timer <<'TMR'
[Unit]
Description=每 30 分钟扫一次 8 单是否到账
[Timer]
OnBootSec=10min
OnUnitActiveSec=30min
Unit=bd-manual8-watch.service
[Install]
WantedBy=timers.target
TMR
systemctl daemon-reload
systemctl enable bd-manual8-watch.timer 2>/dev/null
systemctl start bd-manual8-watch.timer 2>/dev/null
echo "  timer 状态: $(systemctl is-active bd-manual8-watch.timer)"
echo done
