#!/usr/bin/env bash
# 推 channels.html (#8 币结算卡片) 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/channels.html"
REL=$(python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$ABS")
SHA=$(gh api "repos/$REPO/contents/$REL" -q '.sha' 2>/dev/null)
python - "$ABS" "$SHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_ch.html.json'
body = {"message":"feat: channels.html #8 币结算->owner coinbase 钱包卡片","branch":"main",
        "content":base64.b64encode(open(abs,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
if gh api -X PUT "repos/$REPO/contents/$REL" --input "$TEMP/_ch.html.json" >/dev/null 2>&1; then
  echo "[git] channels.html (#8) 已推"
else
  echo "[git] channels.html 失败"
fi
rm -f "$TEMP/_ch.html.json" 2>/dev/null
# 验证
gh api "repos/$REPO/contents/$REL" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('  remote #8 卡片:', '币结算到我的钱包' in raw and 'coinsettle' in raw)" 2>/dev/null
