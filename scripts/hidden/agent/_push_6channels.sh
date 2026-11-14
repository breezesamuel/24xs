#!/usr/bin/env bash
# 推 charity.js + bandwidth.js (新文件) + alipay.js (6 路由, 大文件 --input) + channels.html 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }

# 1. 新文件: charity.js + bandwidth.js (无 sha)
for f in "lib/charity.js" "lib/bandwidth.js"; do
  FULL="02_交付物/channels/gumroad-product-1/tool-station-server-pro/$f"
  REL=$(enc "$FULL")
  B64=$(python -c "import base64;print(base64.b64encode(open('$FULL','rb').read()).decode())")
  if gh api -X PUT "repos/$REPO/contents/$REL" -f message="feat: $f 渠道 (赚钱回路)" -f branch=main -f content="$B64" -f encoding=base64 >/dev/null 2>&1; then
    echo "[git] $f 已推"
  else
    echo "[git] $f 失败"
  fi
done

# 2. alipay.js (已存在, 需 sha; 大文件 --input)
ALI_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
ALI_ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
SHA=$(gh api "repos/$REPO/contents/$ALI_REL" -q '.sha' 2>/dev/null)
python - "$ALI_ABS" "$SHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_ali6.json'
body = {"message":"feat: alipay.js 加 /api/{charity,bandwidth} 路由 (6 渠道)","branch":"main",
        "content":base64.b64encode(open(abs,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
if gh api -X PUT "repos/$REPO/contents/$ALI_REL" --input "$TEMP/_ali6.json" >/dev/null 2>&1; then
  echo "[git] alipay.js (6 路由) 已推"
else
  echo "[git] alipay.js 失败"
fi

# 3. channels.html (已存在, 需 sha; 加 2 卡片)
CH_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/channels.html")
CH_ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/channels.html"
CHSHA=$(gh api "repos/$REPO/contents/$CH_REL" -q '.sha' 2>/dev/null)
python - "$CH_ABS" "$CHSHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_ch6.json'
body = {"message":"feat: channels.html 加 公益/带宽 卡片 (6 渠道引流页)","branch":"main",
        "content":base64.b64encode(open(abs,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
if gh api -X PUT "repos/$REPO/contents/$CH_REL" --input "$TEMP/_ch6.json" >/dev/null 2>&1; then
  echo "[git] channels.html (6 卡片) 已推"
else
  echo "[git] channels.html 失败"
fi
rm -f "$TEMP/_ali6.json" "$TEMP/_ch6.json" 2>/dev/null
echo "=== 验证 remote ==="
echo "  alipay.js 6 路由:"
gh api "repos/$REPO/contents/$ALI_REL" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('   ', all(x in raw for x in ['/api/bounty','/api/cashback','/api/writerewards','/api/charity','/api/bandwidth']))" 2>/dev/null
echo "=== done ==="
