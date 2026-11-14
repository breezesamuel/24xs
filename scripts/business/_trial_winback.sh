#!/usr/bin/env bash
# trial 流失用户挽回 (4 个真实公网 IP 体验用户) + 生成升级链接/话术
python -c "
import json, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
tl=d.get('trialLedger',[])
# 真实体验用户: 排除 127_0_0_1 (本机) 和 diag (自测探针)
real=[t for t in tl if isinstance(t,dict) and '127_0_0_1' not in str(t.get('visitor') or '') and 'diag' not in str(t.get('visitor') or '') and 'alipay_test' not in str(t.get('visitor') or '')]
now=datetime.datetime.now().timestamp()*1000
B='https://tools-cn.highkingflower.com/api/pay'
print('=== 真实 trial 体验用户 (可挽回升级) ===', len(real), '人')
lines=['rank\tref\tvisitor\ttrial日\t距今天\t升级链接(pro¥60)\t挽回话术']
for i,t in enumerate(sorted(real,key=lambda x:x.get('at') or 0),1):
    vid=str(t.get('visitor') or '').split(':')[-1]
    ts=t.get('at') or 0
    age_d=round((now-ts)/86400000,1)
    # 升级链接: trial 已用过 -> 推 pro 月度 ¥60 (ref=vid 收款后激活)
    link=f'{B}?plan=pro&slug=tool&ref={vid}'
    msg=f'您的 7 天体验({age_d}天前)已结束。解锁全部工具 + 专业回测报告(C3) + 行情数据订阅, 专业月度 ¥60/31天, 限时新用户 9 折。专属升级链接: {link}'
    print(f'  {i}. ref={vid} ({t.get(\"visitor\")}) | trial {datetime.datetime.utcfromtimestamp(ts/1000).strftime(\"%m-%d\")} | {age_d}天 (已过期{max(0,age_d-7)}天)')
    print(f'     升级: {link}')
    lines.append(f'{i}\t{vid}\t{t.get(\"visitor\")}\t{datetime.datetime.utcfromtimestamp(ts/1000).strftime(\"%m-%d\")}\t{age_d}\t{link}\t{msg}')
open('/opt/bingdashan/data/billing/trial_winback.tsv','w').write('\n'.join(lines)+'\n')
print()
print('实收潜力 (4 人全升级 pro ¥60): ¥%d (9折后 ¥%d)'%(60*len(real), round(60*0.9*len(real))))
print('已写 /opt/bingdashan/data/billing/trial_winback.tsv')
"
echo ""
echo "=== 建 systemd timer: 每天扫过期 trial + 生成待挽回清单 (自动, 不造数据) ==="
cat > /opt/bingdashan/scripts/ops/trial_winback_scan.sh <<'SCAN'
#!/usr/bin/env bash
# 每天扫一次: 找过期 trial 体验用户, 写待挽回清单 (不自动发邮件, 留人确认)
python3 - <<'PY'
import json, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
tl=[t for t in d.get('trialLedger',[]) if isinstance(t,dict)]
now=datetime.datetime.now().timestamp()*1000
real=[t for t in tl if '127_0_0_1' not in str(t.get('visitor') or '') and 'diag' not in str(t.get('visitor') or '')]
expired=[t for t in real if (now-(t.get('at') or 0)) > 7*86400000]
out={'generated':datetime.datetime.now().isoformat(),'total_real':len(real),'expired_winback':len(expired),
     'refs':[str(t.get('visitor') or '').split(':')[-1] for t in expired]}
open('/opt/bingdashan/data/runtime/trial_winback.json','w').write(json.dumps(out,ensure_ascii=False))
print('  过期可挽回 trial 用户:', len(expired), out['refs'])
PY
SCAN
chmod +x /opt/bingdashan/scripts/ops/trial_winback_scan.sh
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh
cat > /etc/systemd/system/bd-trial-winback.service <<'SVC'
[Unit]
Description=丙大山 过期trial用户挽回扫描
After=network.target
[Service]
WorkingDirectory=/opt/bingdashan
ExecStart=/bin/bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh
User=root
SVC
cat > /etc/systemd/system/bd-trial-winback.timer <<'TMR'
[Unit]
Description=每天 09:00 扫过期trial用户
[Timer]
OnCalendar=09:00
Persistent=true
Unit=bd-trial-winback.service
[Install]
WantedBy=timers.target
TMR
systemctl daemon-reload
systemctl enable bd-trial-winback.timer 2>/dev/null
systemctl start bd-trial-winback.timer 2>/dev/null
echo "  timer: $(systemctl is-active bd-trial-winback.timer)"
echo done
