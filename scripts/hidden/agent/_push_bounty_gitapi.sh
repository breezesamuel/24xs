#!/usr/bin/env bash
# 推 bounty.js (新文件) + alipay.js (bounty 路由, 大文件 --input 法) 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }

# 1. bounty.js (新文件)
BY_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/bounty.js")
BY_B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/bounty.js','rb').read()).decode())")
if gh api -X PUT "repos/$REPO/contents/$BY_REL" -f message="feat: bounty (劳动换币) channel - task catalog + server-side proof verification" -f branch=main -f content="$BY_B64" -f encoding=base64 >/dev/null 2>&1; then
  echo "[git] bounty.js 已推"
else
  echo "[git] bounty.js 推送失败"
fi

# 2. alipay.js (已存在, 需 sha; 含 bounty 路由)
ALI_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
ALI_ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
SHA=$(gh api "repos/$REPO/contents/$ALI_REL" -q '.sha' 2>/dev/null)
TMP="$TEMP/_ali_bounty.json"
python - "$ALI_ABS" "$SHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_ali_bounty.json'
body = {"message":"feat: wire /api/bounty route in alipay.js","branch":"main",
        "content":base64.b64encode(open(abs,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
print("alipay body ready, len=", len(body["content"]))
PY
if gh api -X PUT "repos/$REPO/contents/$ALI_REL" --input "$TMP" >/dev/null 2>&1; then
  echo "[git] alipay.js (bounty 路由) 已推"
else
  echo "[git] alipay.js 推送失败"
fi
rm -f "$TMP" 2>/dev/null
# 3. 验证
echo "=== 验证 remote ==="
gh api "repos/$REPO/contents/$BY_REL" -q '.content' 2>/dev/null > "$TEMP/_byv.txt"
python -c "import base64,os;raw=base64.b64decode(open(os.environ.get('TEMP','/tmp')+'/_byv.txt').read()).decode('utf-8','replace');print('  bounty.js remote:', 'taskCatalog' in raw and 'verifyClaim' in raw)" 2>/dev/null
gh api "repos/$REPO/contents/$ALI_REL" -q '.content' 2>/dev/null > "$TEMP/_aliv.txt"
python -c "import base64,os;raw=base64.b64decode(open(os.environ.get('TEMP','/tmp')+'/_aliv.txt').read()).decode('utf-8','replace');print('  alipay.js remote: /api/bounty=', '/api/bounty' in raw, '| /api/cashback=', '/api/cashback' in raw, '| /api/writerewards=', '/api/writerewards' in raw)" 2>/dev/null
rm -f "$TEMP/_byv.txt" "$TEMP/_aliv.txt" 2>/dev/null
echo "=== done ==="
