#!/usr/bin/env bash
# 诊断 send_upgrade_mail.py 的 auth 读取 (哪一步 None)
echo "=== send_upgrade_mail.py 的 auth 读取行 ==="
grep -nE "SMTP_AUTH|SMTP_PASS|os.popen|auth *=|f\"grep|f'grep" /opt/bingdashan/scripts/ops/send_upgrade_mail.py | head
echo ""
echo "=== 直接跑 send_upgrade_mail.py 看真实报错 (aodm) ==="
python3 /opt/bingdashan/scripts/ops/send_upgrade_mail.py "aodm_dbg@example.com" "pro" "60" "https://tools-cn.highkingflower.com/api/pay?plan=pro&slug=tool&ref=aodm" "aodm" 2>&1 | head -8
echo ""
echo "=== CN 哪个 env 有 SMTP 凭证 ==="
grep -lE "SMTP_AUTH|SMTP_PASS" /opt/bingdashan/.env /etc/bingdashan-cn.env 2>/dev/null
grep -hE "^SMTP_(AUTH|PASS|USER|HOST)=" /opt/bingdashan/.env 2>/dev/null | sed -E 's/(=.{4}).*/\1.../' | head
echo done
