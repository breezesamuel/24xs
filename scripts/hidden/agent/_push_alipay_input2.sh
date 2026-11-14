#!/usr/bin/env bash
# 推 alipay.js 到 remote (contents API + --input JSON 文件, 绕 62KB 命令行 arg 限制)
cd /f/2026/24xs
REPO=breezesamuel/24xs
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
ABS_ENC=$(python -c "import urllib.parse;print(urllib.parse.quote('$ABS'))")
TMP="$TEMP/_ali_push.json"
# 取现有 sha
SHA=$(gh api "repos/$REPO/contents/$ABS_ENC" -q '.sha' 2>/dev/null); echo "现有 sha=${SHA:0:12}"
# 构造 JSON body (Windows temp, python 写)
python - "$ABS" "$SHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_ali_push.json'
body = {"message":"feat: wire /api/{cashback,writerewards} routes in alipay.js",
        "branch":"main","content":base64.b64encode(open(abs,'rb').read()).decode(),
        "encoding":"base64"}
if sha: body["sha"] = sha
json.dump(body, open(tmp,'w'))
print("body ready, content_len=", len(body["content"]))
PY
if [ -n "$SHA" ]; then
  gh api -X PUT "repos/$REPO/contents/$ABS_ENC" --input "$TMP" 2>&1 | head -3
else
  gh api -X PUT "repos/$REPO/contents/$ABS_ENC" --input "$TMP" 2>&1 | head -3
fi
echo "=== 验证 remote ==="
gh api "repos/$REPO/contents/$ABS_ENC" -q '.content' 2>/dev/null > "$TEMP/_ali_verify.txt"
python -c "import base64,os;raw=base64.b64decode(open(os.environ.get('TEMP','/tmp')+'/_ali_verify.txt').read()).decode('utf-8','replace');print('  /api/cashback:', '/api/cashback' in raw, '| /api/writerewards:', '/api/writerewards' in raw)" 2>/dev/null
rm -f "$TMP" "$TEMP/_ali_verify.txt" 2>/dev/null
echo "=== done ==="
