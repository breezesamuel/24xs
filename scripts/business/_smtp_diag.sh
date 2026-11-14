#!/usr/bin/env bash
# 诊断 CN 邮箱: SMTP 配置 + 连通性 (为什么一直 SMTP timeout)
echo "=== 1. CN SMTP 环境变量 (只看键名+是否配, 不打印密码) ==="
grep -oE "^(SMTP_[A-Z_]+|EMAIL_[A-Z_]+|MAIL_[A-Z_]+)=" /opt/bingdashan/.env /etc/bingdashan-cn.env 2>/dev/null | sed -E 's#/opt/bingdashan/.*:/[opt] /; s#/etc/bingdashan-cn.env:/[cn] /' | sort -u
echo ""
echo "=== 2. SMTP_HOST/PORT/USER 具体值 (密码打码) ==="
grep -hE "^(SMTP_|EMAIL_)" /opt/bingdashan/.env /etc/bingdashan-cn.env 2>/dev/null | sed -E 's/(PASSWORD=|AUTH_CODE=|CODE=).*/\1******/' | head -12
echo ""
echo "=== 3. CN 能否连通 QQ SMTP 465 (超时说明网络挡) ==="
timeout 12 bash -c 'echo QUIT | openssl s_client -connect smtp.qq.com:465 -quiet 2>/dev/null | head -c 40' 2>/dev/null && echo "  465 可达" || echo "  ⚠️ 465 连不上 (CN 网络可能挡 465)"
echo ""
echo "=== 4. 试 587/465 端口 + 是否有其它 SMTP (如阿里/腾讯企业邮) ==="
for hp in "smtp.qq.com:465" "smtp.qq.com:587" "smtp.exmail.qq.com:465"; do
  r=$(timeout 8 bash -c "echo QUIT | openssl s_client -connect $hp -quiet 2>/dev/null" 2>/dev/null | head -c 20)
  echo "  $hp -> $( [ -n "$r" ] && echo 可达 || echo 挡" )"
done
echo ""
echo "=== 5. 最近 mail 成功率 (ok:true 有没有成功过) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
mail=d.get('mail',[])
ok=sum(1 for m in mail if isinstance(m,dict) and m.get('ok'))
bad=sum(1 for m in mail if isinstance(m,dict) and not m.get('ok'))
print('  成功:',ok,' 失败:',bad, '总:',len(mail))
errs=set(str(m.get('error')) for m in mail if isinstance(m,dict) and not m.get('ok'))
print('  失败原因:', list(errs)[:5])
"
echo done
