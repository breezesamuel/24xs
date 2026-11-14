#!/usr/bin/env bash
python3 - <<'FIX'
f='/opt/bingdashan/scripts/ops/trial_winback_scan.sh'
s=open(f,encoding='utf-8').read()
s=s.replace("'sent: True' in (r.stdout+r.stderr)", "r.returncode==0")
s=s.replace("'sent: True' in (r.stdout + r.stderr)", "r.returncode==0")
open(f,'w',encoding='utf-8').write(s)
print('winback 成功判定 -> returncode==0 :', "returncode" in s)
FIX
echo "=== 再跑 winback ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -8
echo "=== 发信审计 ==="
tail -2 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null
echo done
