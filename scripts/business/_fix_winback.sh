#!/usr/bin/env bash
# 重写 winback: 正确读 /var/lib/bingdashan-cn/contact_email_map.json + 自动发
cat > /opt/bingdashan/scripts/ops/trial_winback_scan.sh <<'SCAN'
#!/usr/bin/env bash
python3 - <<'PY'
import json, datetime, subprocess, os, glob
db=json.load(open('/opt/bingdashan/data/db.json'))
now=datetime.datetime.now().timestamp()*1000
tl=[t for t in db.get('trialLedger',[]) if isinstance(t,dict)]
real=[t for t in tl if '127_0_0_1' not in str(t.get('visitor') or '') and 'diag' not in str(t.get('visitor') or '')]
expired=[t for t in real if (now-(t.get('at') or 0)) > 7*86400000]
vid2email={}
def add(vid,em):
    if em and vid: vid2email.setdefault(vid,em)
for k in ('visitors','leads','orders'):
    for r in db.get(k,[]):
        if not isinstance(r,dict): continue
        v=str(r.get('visitor') or ''); add(v.split(':')[-1] if v else '', r.get('email'))
# 服务端留资 contact_email_map (CN file store)
for cf in glob.glob('/var/lib/bingdashan-cn/contact_email_map.json'):
    try:
        for vid,em in json.load(open(cf)).items(): add(vid,em)
    except: pass
B='https://tools-cn.highkingflower.com/api/pay'
sent, need_contact = [], []
for t in expired:
    vid=str(t.get('visitor') or '').split(':')[-1]
    email=vid2email.get(vid)
    link=f'{B}?plan=pro&slug=tool&ref={vid}'
    if email:
        try:
            r=subprocess.run(['python3','/opt/bingdashan/scripts/ops/send_upgrade_mail.py',email,'pro','60',link,vid],capture_output=True,text=True,timeout=60)
            sent.append({'vid':vid,'to':email,'ok':'sent: True' in (r.stdout+r.stderr)})
        except Exception as e:
            sent.append({'vid':vid,'to':email,'ok':False,'error':str(e)})
    else:
        need_contact.append({'vid':vid,'visitor':t.get('visitor'),'link':link})
out={'generated':datetime.datetime.now().isoformat(),'expired_total':len(expired),
     'auto_mailed':len(sent),'need_contact':len(need_contact),'sent':sent,'need_contact':need_contact}
open('/opt/bingdashan/data/runtime/trial_winback.json','w').write(json.dumps(out,ensure_ascii=False))
print('  过期 trial:', len(expired), '| 自动发邮件:', len(sent), '| 待人工(无邮箱):', len(need_contact))
for s in sent: print('    发:', s.get('to'), 'ok=', s.get('ok'), s.get('error',''))
PY
SCAN
chmod +x /opt/bingdashan/scripts/ops/trial_winback_scan.sh
echo "=== 跑 (aodm 有邮箱, 应自动发 1 封) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -10
echo "=== 发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "(无)"
echo done
