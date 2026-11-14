#!/usr/bin/env bash
# 用可复用模块发 1 封 (带重试, 避开 QQ 频控), 验证 send_upgrade_mail.py 真能发
sleep 5   # 避开刚才的频控窗口
cd /opt/bingdashan
export $(grep -hE '^SMTP_' .env 2>/dev/null | xargs) 2>/dev/null
for i in 1 2 3; do
  echo "--- 尝试 $i ---"
  out=$(python3 scripts/ops/send_upgrade_mail.py "460123249@qq.com" "pro" "60" "https://tools-cn.highkingflower.com/api/pay?plan=pro&slug=tool&ref=SELTEST" "SELTEST" 2>&1)
  echo "$out"
  echo "$out" | grep -q "sent: True" && { echo "  ✅ 成功"; break; }
  sleep 8   # 频控退避
done
echo ""
echo "=== 审计记录 (upgrade_mail.jsonl) ==="
cat /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null | tail -3
echo done
