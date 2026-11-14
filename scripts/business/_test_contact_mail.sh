#!/usr/bin/env bash
# 端到端测: /api/contact 留资 -> winback 扫描自动发升级邮件
echo "=== 1. 测 /api/contact 留资 (一个已知过期 trial 的 vid, 假邮箱测试) ==="
# 用 aodm (过期 trial 用户), 留一个测试邮箱, 看是否持久化
curl -sk "https://tools-cn.highkingflower.com/api/contact" --max-time 20 -H "Content-Type: application/json" \
  -X POST -d '{"e":"register_email","r":"aodm","email":"winback_test@example.com"}' | head -c 200; echo
echo ""
echo "=== 2. 确认 contact_email_map 落盘 (CN file store) ==="
cat /var/lib/bingdashan-cn/contact_email_map.json 2>/dev/null || echo "  (尚未写入, 看 CN FILE_STORE_DIR 实际位置)"
grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env
cat "$(/etc/2>/dev/null)" 2>/dev/null
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
echo "  FILE_STORE_DIR=$FSDIR"
cat "$FSDIR/contact_email_map.json" 2>/dev/null && echo "  (已落盘)" || echo "  (该位置还没有)"
echo ""
echo "=== 3. 跑 winback 扫描 (应检测到 aodm 有邮箱 -> 自动发) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1
echo ""
echo "=== 4. 自动发信审计 (upgrade_mail.jsonl) ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "  (无记录)"
echo done
