#!/usr/bin/env bash
# 推 writerewards.js (新文件) + cashback.js (已推, 带 payout 更新) 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }

# writerewards.js (新文件, 无 sha)
RW_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/writerewards.js")
RW_B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/writerewards.js','rb').read()).decode())")
if gh api -X PUT "repos/$REPO/contents/$RW_REL" -f message="feat: writerewards (写作赚币) channel - anti-spam quality gate" -f branch=main -f content="$RW_B64" -f encoding=base64 >/dev/null 2>&1; then
  echo "[git] writerewards.js 已推"
else
  echo "[git] writerewards.js 推送失败"
fi

# cashback.js (已存在, 需 sha; 含本轮 payout 更新)
CBK_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/cashback.js")
CBK_SHA=$(gh api "repos/$REPO/contents/$CBK_REL" -q '.sha' 2>/dev/null)
CBK_B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/cashback.js','rb').read()).decode())")
if [ -n "$CBK_SHA" ] && gh api -X PUT "repos/$REPO/contents/$CBK_REL" -f message="feat: cashback payout (提现请求, 人工确认) + 文件回退 dget/dset 修复" -f branch=main -f content="$CBK_B64" -f encoding=base64 -f sha="$CBK_SHA" >/dev/null 2>&1; then
  echo "[git] cashback.js (payout) 已推"
else
  echo "[git] cashback.js 更新失败 (sha=$CBK_SHA)"
fi
echo "=== 验证 remote ==="
echo "  remote writerewards.js quality() 命中:"
gh api "repos/$REPO/contents/$RW_REL" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('   ', 'quality' in raw, '| record' in raw)" 2>/dev/null || echo "   (取失败)"
echo "=== done ==="
