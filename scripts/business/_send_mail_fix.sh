#!/usr/bin/env bash
# 修 UTF-8 编码 + 发 1 封真·验证邮件 (中文正文, QQ SMTP) 证明自动触达通道通
python3 - <<'PY'
import smtplib, ssl, os, base64, time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate

host, port, user = "smtp.qq.com", 465, "460123249@qq.com"
auth = os.popen("grep -h '^SMTP_AUTH=' /opt/bingdashan/.env | head -1 | cut -d= -f2").read().strip()

msg = MIMEText("这是一封中文正文自检邮件 (丙大山自动触达通道验证)。证明 trial 到期自动升级邮件可正常发出, 客户无需切回浏览器/点按钮/等人工核账。", "html", "utf-8")
msg["From"] = user
msg["To"] = "460123249@qq.com"
msg["Subject"] = Header("[丙大山] 自动升级邮件通道自检 OK (中文正文)", "utf-8")
msg["Date"] = formatdate(localtime=True)

try:
    ctx = ssl.create_default_context()
    s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=40)
    s.login(user, auth)
    s.sendmail(user, ["460123249@qq.com"], msg.as_string())
    s.quit()
    print("✅ 中文验证邮件已发出 (UTF-8+HTML 编码修复成功, 自动触达通道真通)")
except Exception as e:
    print("⚠️ 仍失败:", e)
PY
echo ""
echo "=== 落一个可复用的 send_upgrade_mail.py (CN 端, 供 trial 到期自动升级 timer 调) ==="
cat > /opt/bingdashan/scripts/ops/send_upgrade_mail.py <<'PY2'
#!/usr/bin/env python3
"""给 trial 到期用户发升级邮件 (UTF-8 中文, QQ SMTP). 用法:
   python3 send_upgrade_mail.py <to_email> <plan> <price> <upgrade_link> [ref]
"""
import smtplib, ssl, os, sys, json
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate

def send(to, plan, price, link, ref=""):
    host = os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER", "460123249@qq.com")
    auth = os.popen(f"grep -h '^SMTP_AUTH=' /opt/bingdashan/.env | head -1 | cut -d= -f2").read().strip() or os.environ.get("SMTP_PASS","")
    body = f"""<div style='font-family:sans-serif;max-width:520px;margin:auto'>
      <h2>您的 7 天体验即将到期</h2>
      <p>体验 <b>{plan}</b> 已使用 7 天。升级解锁全部工具 + 专业回测报告(C3) + 行情数据订阅 + 策略托管:</p>
      <table><tr><td>专业·月度</td><td><b>¥{price}/31天</b></td></tr></table>
      <p><b>限时新用户 9 折</b> · 升级后: 全部工具 + API + 数据导出 + 优先支持</p>
      <a href="{link}" style='display:inline-block;background:#22c55e;color:#04120a;padding:10px 18px;border-radius:8px;font-weight:700;text-decoration:none'>立即升级 ¥{price}</a>
      <p style='color:#888;font-size:12px'>丙大山工具站 · 本邮件仅提醒, 历史回测不代表未来收益, 非投资建议。退订请回复 U。</p>
      {('<p style="color:#666">您的账号: '+ref+'</p>') if ref else ''}
    </div>"""
    msg = MIMEText(body, "html", "utf-8")
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = Header(f"[丙大山] 体验到期 · 升级享 9 折 ({plan} ¥{price})", "utf-8")
    msg["Date"] = formatdate(localtime=True)
    ctx = ssl.create_default_context()
    s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=40)
    s.login(user, auth)
    s.sendmail(user, [to], msg.as_string())
    s.quit()
    # 记审计 (写 db.json.outbound 或 runtime, 不造假)
    try:
        rec = {"to": to, "plan": plan, "price": price, "link": link, "ref": ref, "ok": True, "at": int(time.time()*1000)}
        p = "/opt/bingdashan/data/runtime/upgrade_mail.jsonl"
        import time as _t; rec["at"] = int(_t.time()*1000)
        open(p, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
    except: pass
    return True

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("用法: send_upgrade_mail.py <to> <plan> <price> <link> [ref]"); sys.exit(1)
    ok = send(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv)>5 else "")
    print("sent:", ok)
PY2
chmod +x /opt/bingdashan/scripts/ops/send_upgrade_mail.py
echo "已建 /opt/bingdashan/scripts/ops/send_upgrade_mail.py"
echo done
