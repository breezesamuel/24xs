#!/usr/bin/env bash
# 推 recovery.js (新文件) + alipay.js (recovery 路由) 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }

# 1. recovery.js (新文件)
RC_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/recovery.js")
RC_B64=$(python -c "import base64;print(base64.b64encode(open('02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/recovery.js','rb').read()).decode())")
if gh api -X PUT "repos/$REPO/contents/$RC_REL" -f message="feat: recovery (找回被遗忘资产) channel - 合法找回本人/已授权资产" -f branch=main -f content="$RC_B64" -f encoding=base64 >/dev/null 2>&1; then
  echo "[git] recovery.js 已推"
else
  echo "[git] recovery.js 失败"
fi

# 2. alipay.js (已存在, 需 sha; 大文件 --input)
ALI_REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
ALI_ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
SHA=$(gh api "repos/$REPO/contents/$ALI_REL" -q '.sha' 2>/dev/null)
python - "$ALI_ABS" "$SHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_alirc.json'
body = {"message":"feat: alipay.js 加 /api/recovery 路由 (7 渠道)","branch":"main",
        "content":base64.b64encode(open(abs,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
if gh api -X PUT "repos/$REPO/contents/$ALI_REL" --input "$TEMP/_alirc.json" >/dev/null 2>&1; then
  echo "[git] alipay.js (recovery 路由) 已推"
else
  echo "[git] alipay.js 失败"
fi
rm -f "$TEMP/_alirc.json" 2>/dev/null
# 3. 验证
echo "=== 验证 remote ==="
gh api "repos/$REPO/contents/$RC_REL" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('  recovery.js remote:', 'not_authorized' in raw and 'authorized' in raw)" 2>/dev/null
gh api "repos/$REPO/contents/$ALI_REL" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('  alipay.js 7 路由:', all(x in raw for x in ['/api/bounty','/api/cashback','/api/writerewards','/api/charity','/api/bandwidth','/api/recovery']))" 2>/dev/null
echo "=== done ==="
