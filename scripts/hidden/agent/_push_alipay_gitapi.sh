#!/usr/bin/env bash
# 推 alipay.js 到 remote main (已存在文件, 需带 sha)
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
B64=$(python -c "import base64;print(base64.b64encode(open('$ABS','rb').read()).decode())")
# 取现有文件 sha
SHA=$(gh api "repos/$REPO/contents/$REL" -q '.sha' 2>/dev/null)
echo "现有 alipay.js sha: ${SHA:0:12}..."
if [ -n "$SHA" ]; then
  gh api -X PUT "repos/$REPO/contents/$REL" -f message="feat: wire /api/cashback route + record-on-payment in alipay.js" -f branch=main -f content="$B64" -f encoding=base64 -f sha="$SHA" >/dev/null 2>&1 \
    && echo "[git] alipay.js 已推 (带 sha)" || echo "[git] alipay.js 推送仍失败"
else
  echo "[git] 取 sha 失败 (文件可能不在远端)"
fi
echo "=== 验证 ==="
gh api "repos/$REPO/contents/$REL" -q '.content' 2>/dev/null > /tmp/_ali_b64.txt
python -c "import base64;raw=base64.b64decode(open('/tmp/_ali_b64.txt').read()).decode('utf-8','replace');print('  remote /api/cashback:', '/api/cashback' in raw, '| cashback record:', 'cashback.js' in raw)" 2>/dev/null || echo "  (验证失败)"
echo "=== done ==="
