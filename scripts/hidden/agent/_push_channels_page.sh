#!/usr/bin/env bash
# 推 channels.html + writerewards.js (?a=post) 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }

# channels.html (新文件)
CH_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/channels.html")
CH_B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/channels.html','rb').read()).decode())")
if gh api -X PUT "repos/$REPO/contents/$CH_REL" -f message="feat: channels.html 赚钱回路引流页" -f branch=main -f content="$CH_B64" -f encoding=base64 >/dev/null 2>&1; then
  echo "[git] channels.html 已推"
else
  echo "[git] channels.html 推送失败"
fi

# writerewards.js (已存在, 需 sha; 含 ?a=post)
WR_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/writerewards.js")
WR_SHA=$(gh api "repos/$REPO/contents/$WR_REL" -q '.sha' 2>/dev/null)
WR_B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/writerewards.js','rb').read()).decode())")
if [ -n "$WR_SHA" ] && gh api -X PUT "repos/$REPO/contents/$WR_REL" -f message="feat: writerewards ?a=post (投稿赚币, 服务端质量门禁)" -f branch=main -f content="$WR_B64" -f encoding=base64 -f sha="$WR_SHA" >/dev/null 2>&1; then
  echo "[git] writerewards.js (?a=post) 已推"
else
  echo "[git] writerewards.js 更新失败 (sha=$WR_SHA)"
fi
# index.html (加 channels 入口; 已存在, 需 sha)
IDX_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/index.html")
IDX_SHA=$(gh api "repos/$REPO/contents/$IDX_REL" -q '.sha' 2>/dev/null)
IDX_B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/index.html','rb').read()).decode())")
if [ -n "$IDX_SHA" ] && gh api -X PUT "repos/$REPO/contents/$IDX_REL" -f message="feat: index.html 加 channels.html 赚钱回路入口" -f branch=main -f content="$IDX_B64" -f encoding=base64 -f sha="$IDX_SHA" >/dev/null 2>&1; then
  echo "[git] index.html 已推"
else
  echo "[git] index.html 更新失败"
fi
echo "=== 验证 ==="
echo "  remote channels.html:"; gh api "repos/$REPO/contents/$CH_REL" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('   ', '赚钱回路' in raw, '| /api/track' in raw, '| /api/pay' in raw)" 2>/dev/null
echo "=== done ==="
