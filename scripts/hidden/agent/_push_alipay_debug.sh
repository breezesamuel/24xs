#!/usr/bin/env bash
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
B64=$(python -c "import base64;print(base64.b64encode(open('$ABS','rb').read()).decode())")
SHA=$(gh api "repos/$REPO/contents/$REL" -q '.sha')
echo "sha=$SHA size_b64=${#B64}"
# 看实际报错
gh api -X PUT "repos/$REPO/contents/$REL" -f message="feat: /api/cashback in alipay.js" -f branch=main -f content="$B64" -f encoding=base64 -f sha="$SHA" 2>&1 | head -8
echo "=== rc=${PIPESTATUS[0]} ==="
