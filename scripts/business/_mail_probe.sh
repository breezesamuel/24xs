#!/usr/bin/env bash
# 摸清 CN 现有 mail 机制: SMTP 配置 + 怎么发 + 能否程序调用 (复用)
echo "=== 1. CN mail 配置 (SMTP/收件/凭证, 只看键名+是否配, 不打印密码) ==="
grep -oE "MAIL_[A-Z_]*|SMTP_[A-Z_]*|EMAIL_[A-Z_]*" /etc/bingdashan-cn.env 2>/dev/null | sort -u | while read -r k; do
  v=$(grep -E "^${k}=" /etc/bingdashan-cn.env 2>/dev/null | head -1 | cut -d= -f2-)
  [ -z "$v" ] && echo "  $k: (空)" || echo "  $k: 已配(len=${#v})"
done
echo ""
echo "=== 2. CN 有没有现成的发函脚本/库 (email_watch/mail 模块) ==="
find /opt/bingdashan -iname "*mail*" -o -iname "*email*" 2>/dev/null | grep -viE "node_modules|\.git" | head -15
echo ""
echo "=== 3. mail 模块怎么发 (找 SMTP send 入口 + 凭证来源) ==="
grep -rniE "smtplib|SMTP\(|sendmail|send_mail|def.*send.*mail|MAIL_HOST|MAIL_USER|QQ.*SMTP|smtp.qq" /opt/bingdashan --include="*.py" --include="*.js" 2>/dev/null | grep -viE "node_modules|\.git" | head -15
echo ""
echo "=== 4. db.json mail 表 (33条) 的发函记录结构 (看成功发过什么) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
mail=d.get('mail',[])
print('  mail 条数:', len(mail))
for m in mail[-4:]:
    if isinstance(m,dict):
        print('   ', json.dumps({k:m.get(k) for k in ('id','to','subject','ok','status','at','channel','error') if m.get(k) is not None}, ensure_ascii=False)[:200])
"
echo done
