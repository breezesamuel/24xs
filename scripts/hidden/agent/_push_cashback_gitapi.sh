#!/usr/bin/env bash
# 推 cashback.js + alipay.js (本轮改动) 到 remote main (gh api contents, 绕 git https 断网)
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }

# 1. cashback.js (新文件, 含 CJK 路径)
REL_CBK=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/cashback.js")
B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/cashback.js','rb').read()).decode())")
if gh api -X PUT "repos/$REPO/contents/$REL_CBK" -f message="feat: cashback (购物返现) channel - CN file-store fallback" -f branch=main -f content="$B64" -f encoding=base64 >/dev/null 2>&1; then
  echo "[git] cashback.js 已推 remote main"
else
  echo "[git] cashback.js 推送失败"
fi

# 2. alipay.js (改了 /api/cashback 路由 + record 调用, 也含 CJK 路径)
REL_ALI=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
B64a=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js','rb').read()).decode())")
if gh api -X PUT "repos/$REPO/contents/$REL_ALI" -f message="feat: wire /api/cashback route + record-on-payment in alipay.js" -f branch=main -f content="$B64a" -f encoding=base64 >/dev/null 2>&1; then
  echo "[git] alipay.js 已推 remote main"
else
  echo "[git] alipay.js 推送失败"
fi

# 3. 验证 remote 已含 cashback
echo "=== 验证 remote ==="
echo "remote cashback.js loopStats/record:"
gh api "repos/$REPO/contents/$REL_CBK" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('  cashback record 出现:', raw.count('async function record'), '| hasStore fileStore:', ('fileStore()' in raw))" 2>/dev/null || echo "  (取 remote 失败)"
echo "=== done ==="
