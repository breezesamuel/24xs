#!/usr/bin/env bash
# 把 trial-winback 扫描接上"自动发邮件" (有邮箱的试到自动发, 匿名IP的标记待人工)
cat > /opt/bingdashan/scripts/ops/trial_winback_scan.sh <<'SCAN'
#!/usr/bin/env bash
# 每天扫过期 trial 用户: 有邮箱->自动发升级邮件; 无邮箱(匿名IP)->写待人工清单 (不造假, 全留审计)
python3 - <<'PY'
import json, datetime, os
db=json.load(open('/opt/bingdashan/data/db.json'))
now=datetime.datetime.now().timestamp()*1000
tl=[t for t in db.get('trialLedger',[]) if isinstance(t,dict)]
real=[t for t in tl if '127_0_0_1' not in str(t.get('visitor') or '') and 'diag' not in str(t.get('visitor') or '')]
expired=[t for t in real if (now-(t.get('at') or 0)) > 7*86400000]

# 建 "访客vid -> 邮箱" 映射 (从 visitors/leads/orders + 服务端留资 contact_email_map)
vid2email={}
def add(src, vid, em):
    if em and vid: vid2email.setdefault(vid, em)
for k in ('visitors','leads','orders'):
    for r in db.get(k,[]):
        if not isinstance(r,dict): continue
        v=str(r.get('visitor') or '')
        vid=v.split(':')[-1] if v else ''
        em=r.get('email')
        add(None, vid, em)
# 服务端留资 (channels 注册时用户主动留的邮箱, 最可信的触达渠道)
try:
    fmap=open('/opt/bingdashan/data/billing/../..','r') if False else None
except: pass
# 读 contact_email_map: CN 是 file store, 键名 contact_email_map
import glob as _glob
for cf in _glob.glob('/var/lib/bingdashan-cn/contact_email_map.json'):
    try:
        cm=json.load(open(cf))
        for vid,em in cm.items(): add('contact_map', vid, em)
    except: pass

B='https://tools-cn.highkingflower.com/api/pay'
sent, need_contact = [], []
for t in expired:
    vid=str(t.get('visitor') or '').split(':')[-1]
    email=vid2email.get(vid)
    link=f'{B}?plan=pro&slug=tool&ref={vid}'
    if email:
        # 有邮箱 -> 自动发 (调用 send_upgrade_mail.py)
        try:
            import subprocess
            r=subprocess.run(['python3','/opt/bingdashan/scripts/ops/send_upgrade_mail.py',email,'pro','60',link,vid],capture_output=True,text=True,timeout=60)
            ok='sent: True' in (r.stdout+r.stderr)
            sent.append({'vid':vid,'to':email,'ok':ok})
        except Exception as e:
            sent.append({'vid':vid,'to':email,'ok':False,'error':str(e)})
    else:
        need_contact.append({'vid':vid,'visitor':t.get('visitor'),'link':link})

out={'generated':datetime.datetime.now().isoformat(),
     'expired_total':len(expired),'auto_mailed':len(sent),'need_contact':len(need_contact),
     'sent':sent,'need_contact':need_contact}
open('/opt/bingdashan/data/runtime/trial_winback.json','w').write(json.dumps(out,ensure_ascii=False))
print('  过期 trial:', len(expired), '| 自动发邮件:', len(sent), '| 待人工(无邮箱):', len(need_contact))
for s in sent: print('    发:', s.get('to'), 'ok=', s.get('ok'))
for n in need_contact[:10]: print('    待人工:', n.get('vid'), n.get('visitor'), '->', n.get('link'))
PY
SCAN
chmod +x /opt/bingdashan/scripts/ops/trial_winback_scan.sh
echo "=== 跑一次 (看当前有多少可自动发/多少待人工) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1
echo ""
echo "=== timer 确认 active ==="
systemctl is-active bd-trial-winback.timer
echo done
