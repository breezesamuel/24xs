#!/usr/bin/env bash
# 全链路终验: /api/contact 留资 -> 落盘 -> winback 自动发
echo "=== 1. 发 /api/contact (aodm 留邮箱) ==="
curl -sk -X POST "https://tools-cn.highkingflower.com/api/contact" --max-time 20 -H "Content-Type: application/json" -d '{"e":"register_email","r":"aodm","email":"aodm_wb@example.com"}'; echo
sleep 1
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
echo "=== 2. 落盘文件 ==="
ls -la "$FSDIR"/contact_email_map.json 2>/dev/null && cat "$FSDIR/contact_email_map.json" 2>/dev/null || echo "  仍无文件 -> 看 track.js 的 email 分支实际行为"
echo ""
echo "=== 3. track.js 的 email 分支 (确认逻辑对不对) ==="
grep -nE "register_email|persist_email|contact_email_map" /www/wwwroot/tools-cn.highkingflower.com/api/track.js | head
echo ""
echo "=== 4. 若 aodm 已留邮箱, 跑 winback 应自动发 ==="
bash /opt/bingdashan/scripts/ops/trial_winback_scan.sh 2>&1 | head -8
echo "=== 5. 发信审计 ==="
tail -3 /opt/bingdashan/data/runtime/upgrade_mail.jsonl 2>/dev/null || echo "  (无)"
echo done
