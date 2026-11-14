#!/usr/bin/env bash
# 推 C4/C5/C6 文件到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
BASE="02_交付物/channels/gumroad-product-1/tool-station-server-pro"
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
push_new(){
  local f="$1" msg="$2" ABS
  ABS="F:/2026/24xs/$BASE/$f"
  local REL enc RELb B64
  REL="$BASE/$f"; enc=$(enc "$REL")
  B64=$(python -c "import base64;print(base64.b64encode(open('$ABS','rb').read()).decode())")
  if gh api -X PUT "repos/$REPO/contents/$enc" -f message="$msg" -f branch=main -f content="$B64" -f encoding=base64 >/dev/null 2>&1; then
    echo "[git] $f 已推(新)"
  else
    local SHA=$(gh api "repos/$REPO/contents/$enc" -q '.sha' 2>/dev/null)
    python - "$ABS" "$SHA" "$f" <<PY
import sys, json, base64, os
f, sha, rel = sys.argv[1], sys.argv[2], sys.argv[3]
tmp = os.environ.get('TEMP','/tmp') + '/_push.json'
body = {"message":"feat: C4/C5/C6 更新 "+rel,"branch":"main","content":base64.b64encode(open(f,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
    gh api -X PUT "repos/$REPO/contents/$enc" --input "$TEMP/_push.json" >/dev/null 2>&1 && echo "[git] $f 已推(更新)" || echo "[git] $f 失败"
    rm -f "$TEMP/_push.json" 2>/dev/null
  fi
}
push_new "api/alipay.js" "feat: /api/revenue 读真台账+渠道账本 (营收看板数据源)"
push_new "vercel.json" "feat: /api/revenue vercel rewrite"
push_new "revenue.html" "feat: 营收看板网页版 /revenue.html (30s 自动刷新, 只读真数据)"
echo "=== 验证 remote ==="
for f in lib/strategyapi.js lib/marketdata.js lib/strategyhosting.js; do
  enc1=$(enc "$BASE/$f")
  gh api "repos/$REPO/contents/$enc1" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('  $f:', ('need_payment' in raw or 'quota' in raw or 'host_weeks' in raw))" 2>/dev/null
done
echo "=== done ==="
