#!/usr/bin/env bash
# 推 alipay.js (coinsettle + coinbase 钱包) + vercel.json (coinsettle rewrite) 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro"

# alipay.js (已存在, 需 sha; 大文件用 --input)
A_REL=$(enc "$ABS/api/alipay.js")
SHA=$(gh api "repos/$REPO/contents/$A_REL" -q '.sha' 2>/dev/null)
python - "$ABS/api/alipay.js" "$SHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_coinsettle.json'
body = {"message":"feat: 币结算 -> owner coinbase 钱包 (0xe35b...093c); /api/coinsettle 合规红线(仅 source=earned, 拒无主/airdrop)",
        "branch":"main","content":base64.b64encode(open(abs,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
if gh api -X PUT "repos/$REPO/contents/$A_REL" --input "$TEMP/_coinsettle.json" >/dev/null 2>&1; then
  echo "[git] alipay.js (coinsettle+coinbase) 已推"
else
  echo "[git] alipay.js 失败"
fi
rm -f "$TEMP/_coinsettle.json" 2>/dev/null

# vercel.json
V_REL=$(enc "$ABS/vercel.json")
VSHA=$(gh api "repos/$REPO/contents/$V_REL" -q '.sha' 2>/dev/null)
python - "$ABS/vercel.json" "$VSHA" <<'PY'
import sys, json, base64, os
abs, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_vjson.json'
body = {"message":"feat: vercel.json 加 /api/coinsettle 重写路由","branch":"main",
        "content":base64.b64encode(open(abs,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
if gh api -X PUT "repos/$REPO/contents/$V_REL" --input "$TEMP/_vjson.json" >/dev/null 2>&1; then
  echo "[git] vercel.json (coinsettle) 已推"
else
  echo "[git] vercel.json 失败"
fi
rm -f "$TEMP/_vjson.json" 2>/dev/null

# 验证 remote
echo "=== 验证 remote ==="
gh api "repos/$REPO/contents/$A_REL" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('  alipay.js remote:', all(x in raw for x in ['owner_coinbase','0xe35b920Ba38bc83fb19D0b77871545C2F986093c','source','coinsettle']))" 2>/dev/null
echo "=== done ==="
