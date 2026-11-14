#!/usr/bin/env bash
# 干净重写 send_upgrade_mail.py (不 patch, 整个文件重写, python3.6 兼容)
cat > /opt/bingdashan/scripts/ops/send_upgrade_mail.py <<'PYMAIL'
#!/usr/bin/env python3
# 给 trial 到期用户发升级邮件 (UTF-8 中文, QQ SMTP). python3.6 兼容.
# 用法: python3 send_upgrade_mail.py <to_email> <plan> <price> <upgrade_link> [ref]
import smtplib, ssl, os, sys, json, time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate

def _smtp_creds():
    host, port = os.environ.get("SMTP_HOST","smtp.qq.com"), int(os.environ.get("SMTP_PORT","465"))
    user = os.environ.get("SMTP_USER","460123249@qq.com")
    auth = ""
    for ef in ("/opt/bingdashan/.env","/etc/bingdashan-cn.env"):
        try:
            for line in open(ef, encoding="utf-8", errors="replace"):
                line=line.strip()
                if line.startswith("SMTP_PASS="):
                    auth=line.split("=",1)[1].strip(); break
                if line.startswith("SMTP_AUTH=") and not auth:
                    auth=line.split("=",1)[1].strip()
        except Exception:
            pass
    if not auth:
        auth=os.environ.get("SMTP_PASS","") or os.environ.get("SMTP_AUTH","")
    return host, port, user, auth

def send(to, plan, price, link, ref=""):
    host, port, user, auth = _smtp_creds()
    if not auth:
        raise RuntimeError("SMTP_PASS 未配置, 无法发信")
    body = """<div style='font-family:sans-serif;max-width:520px;margin:auto'>
      <h2>您的 7 天体验即将到期</h2>
      <p>体验 <b>{plan}</b> 已使用 7 天。升级解锁全部工具 + 专业回测报告(C3) + 行情数据订阅 + 策略托管:</p>
      <table><tr><td>专业·月度</td><td><b>¥{price}/31天</b></td></tr></table>
      <p><b>限时新用户 9 折</b> · 升级后: 全部工具 + API + 数据导出 + 优先支持</p>
      <a href="{link}" style='display:inline-block;background:#22c55e;color:#04120a;padding:10px 18px;border-radius:8px;font-weight:700;text-decoration:none'>立即升级 ¥{price}</a>
      <p style='color:#888;font-size:12px'>丙大山工具站 · 本邮件仅提醒, 历史回测不代表未来收益, 非投资建议。退订请回复 U。</p>
      {refline}
    </div>""".format(plan=plan, price=price, link=link, refline=('<p style="color:#666">您的账号: '+ref+'</p>') if ref else '')
    msg = MIMEText(body, "html", "utf-8")
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = Header("[丙大山] 体验到期 · 升级享 9 折 ("+plan+" ¥"+str(price)+")", "utf-8")
    msg["Date"] = formatdate(localtime=True)
    ctx = ssl.create_default_context()
    s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=45)
    s.login(user, auth)
    s.sendmail(user, [to], msg.as_string())
    s.quit()
    try:
        rec={"to":to,"plan":plan,"price":price,"link":link,"ref":ref,"ok":True,"at":int(time.time()*1000)}
        open("/opt/bingdashan/data/runtime/upgrade_mail.jsonl","a").write(json.dumps(rec,ensure_ascii=False)+"\n")
    except Exception:
        pass
    return True

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("用法: send_upgrade_mail.py <to> <plan> <price> <link> [ref]"); sys.exit(1)
    try:
        ok = send(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv)>5 else "")
        print("sent:", ok)
    except Exception as e:
        print("ERR:", e)
PYMAIL
chmod +x /opt/bingdashan/scripts/ops/send_upgrade_mail.py
echo "=== 直接测发 (aodm) ==="
python3 /opt/bingdashan/scripts/ops/send_upgrade_mail.py "aodm_dbg@example.com" "pro" "60" "https://tools-cn.highkingflower.com/api/pay?plan=pro&slug=tool&ref=aodm" "aodm" 2>&1 | head -4
echo "=== winback 子进程简化 (去掉 env=) ==="
python3 - <<'PFW'
f='/opt/bingdashan/scripts/ops/trial_winback_scan.sh'
s=open(f,encoding='utf-8').read()
import re
s=re.sub(r"r=_sp\.run\(\['python3'[^)]*env=_env\)",
         "r=_sp.run(['python3','/opt/bingdashan/scripts/ops/send_upgrade_mail.py',email,'pro','60',link,vid],stdout=_sp.PIPE,stderr=_sp.STDOUT,universal_newlines=True,timeout=90)", s, count=1)
s=s.replace("import os as _os; _env=dict(_os.environ); _env['SMTP_PASS']=_os.popen(\"grep -h '^SMTP_PASS=' /opt/bingdashan/.env | head -1 | cut -d= -f2\").read().strip(); ","")
open(f,'w',encoding='utf-8').write(s)
print('winback 子进程已简化')
PFW
echo "=== 跑 winback (aodm 应 ok=True) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -8
echo "=== 发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "(无)"
echo done
