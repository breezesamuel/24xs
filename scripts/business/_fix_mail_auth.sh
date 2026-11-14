#!/usr/bin/env bash
# 修 send_upgrade_mail.py: 读 SMTP_PASS (CN 实际用的键), 不是 SMTP_AUTH
python3 - <<'PY'
f='/opt/bingdashan/scripts/ops/send_upgrade_mail.py'
s=open(f,encoding='utf-8').read()
import re
# 替换 auth 读取行: 优先 env SMTP_PASS, 再 grep .env 的 SMTP_PASS, 再 SMTP_AUTH
s=re.sub(r'auth = .*', 
         "auth = (os.environ.get('SMTP_PASS') or os.popen(\"grep -h '^SMTP_PASS=' /opt/bingdashan/.env | head -1 | cut -d= -f2\").read().strip() or os.environ.get('SMTP_AUTH',''))",
         s, count=1)
open(f,'w',encoding='utf-8').write(s)
print('已修:', [l for l in s.splitlines() if 'auth =' in l][:1])
PY
echo "=== 直接测发 1 封 (aodm, 应真发出) ==="
python3 /opt/bingdashan/scripts/ops/send_upgrade_mail.py "aodm_dbg@example.com" "pro" "60" "https://tools-cn.highkingflower.com/api/pay?plan=pro&slug=tool&ref=aodm" "aodm" 2>&1 | head -5
echo "=== 跑 winback (aodm 应自动发成功) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -8
echo "=== 发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "(无)"
echo done
