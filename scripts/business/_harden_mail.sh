#!/usr/bin/env bash
# 硬化 send_upgrade_mail.py: 直接读 .env 文件解析 SMTP_PASS (不用 popen grep, 最稳)
python3 - <<'PY'
f='/opt/bingdashan/scripts/ops/send_upgrade_mail.py'
s=open(f,encoding='utf-8').read()
import re
# 替换 auth 行: 直接解析 .env 文件
newauth = '''def _smtp_pass():
    import os
    for ef in ("/opt/bingdashan/.env","/etc/bingdashan-cn.env"):
        try:
            for line in open(ef, encoding="utf-8", errors="replace"):
                line=line.strip()
                if line.startswith("SMTP_PASS="): return line.split("=",1)[1].strip()
                if line.startswith("SMTP_AUTH="): return line.split("=",1)[1].strip()
        except Exception:
            pass
    return os.environ.get("SMTP_PASS","") or os.environ.get("SMTP_AUTH","")
auth = _smtp_pass()'''
s=re.sub(r"auth = \(os\.environ.*?SMTP_AUTH',''\)\)", newauth, s, count=1)
if 'def _smtp_pass' not in s:
    # 兜底: 替换旧的 auth = ... 行
    s=re.sub(r"auth = .*", "auth = _smtp_pass()", s, count=1)
open(f,'w',encoding='utf-8').write(s)
print('已硬化 auth 读取 (直接解析 .env)')
print([l for l in s.splitlines() if 'def _smtp_pass' in l or l.strip().startswith('auth =')][:2])
PY
echo "=== 直接测发 (aodm) ==="
python3 /opt/bingdashan/scripts/ops/send_upgrade_mail.py "aodm_dbg@example.com" "pro" "60" "https://tools-cn.highkingflower.com/api/pay?plan=pro&slug=tool&ref=aodm" "aodm" 2>&1 | head -4
echo ""
echo "=== 把 winback 里脆弱的 env 传参去掉 (现在 mail 自己读 .env, 不需要 winback 传) ==="
python3 - <<'PY2'
f='/opt/bingdashan/scripts/ops/trial_winback_scan.sh'
s=open(f,encoding='utf-8').read()
# 简化: subprocess 直接跑, 不需要 env= (mail 自己读 .env)
s=s.replace("""import os as _os; _env=dict(_os.environ); _env['SMTP_PASS']=_os.popen("grep -h '^SMTP_PASS=' /opt/bingdashan/.env | head -1 | cut -d= -f2").read().strip(); r=_sp.run(['python3','/opt/bingdashan/scripts/ops/send_upgrade_mail.py',email,'pro','60',link,vid],stdout=_sp.PIPE,stderr=_sp.STDOUT,universal_newlines=True,timeout=60,env=_env)""",
"""r=_sp.run(['python3','/opt/bingdashan/scripts/ops/send_upgrade_mail.py',email,'pro','60',link,vid],stdout=_sp.PIPE,stderr=_sp.STDOUT,universal_newlines=True,timeout=90)""")
open(f,'w',encoding='utf-8').write(s)
print('winback subprocess 已简化')
PY
echo "=== 跑 winback (aodm 应 ok=True) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -8
echo "=== 发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "(无)"
echo done
