#!/usr/bin/env bash
# 确认 contact 落盘 + 跑 winback 看是否自动发
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
echo "=== contact 相关落盘文件 ==="
ls -1 "$FSDIR"/contact* "$FSDIR"/track_contact* 2>/dev/null
echo "--- 找所有含 aodm_test 的文件 ---"
grep -rl "aodm_test@example.com" "$FSDIR" 2>/dev/null | head
echo ""
echo "=== 再发一次 /api/contact (确认) ==="
curl -sk -X POST "https://tools-cn.highkingflower.com/api/contact" --max-time 20 -H "Content-Type: application/json" -d '{"e":"register_email","r":"aodm","email":"aodm_test@example.com"}'; echo
sleep 1
echo "=== 再查落盘 ==="
ls -1 "$FSDIR"/contact* 2>/dev/null
cat "$FSDIR"/contact_email_map.json 2>/dev/null && echo ""
echo ""
echo "=== 跑 winback 扫描 (应自动给 aodm 发升级邮件) ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -12
echo "=== 自动发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "  (无)"
echo done
