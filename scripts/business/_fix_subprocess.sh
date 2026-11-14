#!/usr/bin/env bash
# 修 winback 的 subprocess (CN python3.6 不支持 capture_output, 用 stdout=PIPE)
python3 - <<'PY'
s=open('/opt/bingdashan/scripts/ops/trial_winback_scan.sh').read()
old='r=subprocess.run([\'python3\',\'/opt/bingdashan/scripts/ops/send_upgrade_mail.py\',email,\'pro\',\'60\',link,vid],capture_output=True,text=True,timeout=60)'
new='import subprocess as _sp,io; r=_sp.run([\'python3\',\'/opt/bingdashan/scripts/ops/send_upgrade_mail.py\',email,\'pro\',\'60\',link,vid],stdout=_sp.PIPE,stderr=_sp.STDOUT,universal_newlines=True,timeout=60)'
if old in s:
    s=s.replace(old,new,1)
    # 同时把后面用到 r.stdout 的改为 r.stdout (PIPE 模式 r.stdout 仍是 str, 通用)
    open('/opt/bingdashan/scripts/ops/trial_winback_scan.sh','w').write(s)
    print('  已修 subprocess (python3.6 兼容)')
else:
    print('  未找到目标行 (可能已改), 打印当前 subprocess 行:')
    for ln in s.splitlines():
        if 'subprocess.run' in ln: print('   ', ln.strip())
PY
echo "=== 再跑 winback (aodm 应真发出去) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -10
echo "=== 发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "(无)"
echo done
