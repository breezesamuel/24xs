#!/usr/bin/env bash
# CN 的 /api/track 实际存到哪 + 能否带 email 字段 (复用现有端点, 不新建)
echo "=== 1. CN /api/track 存到哪 (file store 哪个文件) ==="
curl -sk -X POST "https://tools-cn.highkingflower.com/api/track" --max-time 15 \
  -H "Content-Type: application/json" -d '{"t":1,"p":"/probe","e":"probe","r":"probecode"}' | head -c 150; echo
echo "  CN track 落盘位置 (FILE_STORE_DIR):"
FSDIR=$(grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env | cut -d= -f2)
ls -1 "$FSDIR"/track_*.json 2>/dev/null | tail -3
echo ""
echo "=== 2. CN /v1/ 下有没有 contact/留资端点 (可能已有) ==="
for ep in "contact" "lead" "leads" "signup" "subscribe" "mail" "notify"; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 10 "https://tools-cn.highkingflower.com/v1/$ep" 2>/dev/null)
  echo "  /v1/$ep -> $code"
done
echo ""
echo "=== 3. CN 的 track 落盘文件结构 (看它存哪些字段, email 能不能塞进去) ==="
LAST=$(ls -t "$FSDIR"/track_*.json 2>/dev/null | head -1)
echo "  最新: $LAST"
cat "$LAST" 2>/dev/null | head -c 400; echo
echo done
