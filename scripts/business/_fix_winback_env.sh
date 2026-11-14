#!/usr/bin/env bash
# 修 winback: 给 send_upgrade_mail 子进程传 SMTP_PASS env (subprocess 不继承 shell 的)
python3 - <<'PY'
f='/opt/bingdashan/scripts/ops/trial_winback_scan.sh'
s=open(f,encoding='utf-8').read()
# 在 subprocess.run 调用处加 env= 传递 SMTP_PASS
old="r=_sp.run(['python3','/opt/bingdashan/scripts/ops/send_upgrade_mail.py',email,'pro','60',link,vid],stdout=_sp.PIPE,stderr=_sp.STDOUT,universal_newlines=True,timeout=60)"
new="import os as _os; _env=dict(_os.environ); _env['SMTP_PASS']=_os.popen(\"grep -h '^SMTP_PASS=' /opt/bingdashan/.env | head -1 | cut -d= -f2\").read().strip(); r=_sp.run(['python3','/opt/bingdashan/scripts/ops/send_upgrade_mail.py',email,'pro','60',link,vid],stdout=_sp.PIPE,stderr=_sp.STDOUT,universal_newlines=True,timeout=60,env=_env)"
if old in s:
    s=s.replace(old,new,1); open(f,'w',encoding='utf-8').write(s); print('  已加 env=SMTP_PASS')
else:
    print('  未找到 subprocess 行, 打印当前:'); [print('   ',l.strip()) for l in s.splitlines() if '_sp.run' in l]
PY
echo "=== 跑 winback (aodm 应 ok=True 真发出) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -8
echo "=== 发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "(无)"
echo done
