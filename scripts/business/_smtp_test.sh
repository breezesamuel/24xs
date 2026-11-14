#!/usr/bin/env bash
# 验证 SMTP 凭证 + 直接发 1 封测试邮件 (证明能走水: 自动触达通道真通)
echo "=== 1. 验证 SMTP 登录 (QQ 授权码) ==="
python3 - <<'PY'
import smtplib, ssl, os, json
host, port, user, auth = "smtp.qq.com", 465, "460123249@qq.com", os.popen("grep -h '^SMTP_AUTH=' /opt/bingdashan/.env | head -1 | cut -d= -f2").read().strip()
if not auth:
    auth = os.popen("grep -h '^SMTP_PASS=' /opt/bingdashan/.env | head -1 | cut -d= -f2").read().strip()
print("  AUTH 长度:", len(auth))
try:
    ctx = ssl.create_default_context()
    s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
    s.login(user, auth)
    print("  ✅ SMTP 登录成功 (凭证有效)")
    # 发 1 封测试邮件给自己, 验证全链路
    msg = "From: 460123249@qq.com\r\nTo: 460123249@qq.com\r\nSubject: [丙大山] 自动触达通道自检 OK\r\n\r\n这封是系统自检邮件, 证明 trial 到期自动升级邮件通道可用.\r\n"
    s.sendmail(user, ["460123249@qq.com"], msg)
    print("  ✅ 测试邮件已发出 (通道真通)")
    s.quit()
except Exception as e:
    print("  ⚠️ SMTP 失败:", e)
PY
echo ""
echo "=== 2. 最近 mail 成功率 ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
mail=d.get('mail',[])
ok=sum(1 for m in mail if isinstance(m,dict) and m.get('ok'))
bad=sum(1 for m in mail if isinstance(m,dict) and not m.get('ok'))
errs=sorted(set(str(m.get('error')) for m in mail if isinstance(m,dict) and not m.get('ok')))
print('  成功:',ok,'失败:',bad,'总:',len(mail))
print('  失败原因:',errs[:5])
"
echo done
