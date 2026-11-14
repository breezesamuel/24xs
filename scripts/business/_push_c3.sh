#!/usr/bin/env bash
# 推 C3 新增文件 (reportexport.js 新 + channels.html C3卡片) 到 remote main
cd /f/2026/24xs
REPO=breezesamuel/24xs
BASE="02_交付物/channels/gumroad-product-1/tool-station-server-pro"
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
push_new(){ # 新文件/更新: PUT
  local f="$1" msg="$2" ABS
  ABS="F:/2026/24xs/$BASE/$f"
  local REL enc RELb B64
  REL="$BASE/$f"; enc=$(enc "$REL")
  B64=$(python -c "import base64;print(base64.b64encode(open('$ABS','rb').read()).decode())")
  if gh api -X PUT "repos/$REPO/contents/$enc" -f message="$msg" -f branch=main -f content="$B64" -f encoding=base64 >/dev/null 2>&1; then
    echo "[git] $f 已推(新)"
  else
    local SHA=$(gh api "repos/$REPO/contents/$enc" -q '.sha' 2>/dev/null)
    python - "$ABS" "$SHA" <<PY
import sys, json, base64, os
f, sha = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp') + '/_push.json'
body = {"message":"feat: C3 更新 $f","branch":"main","content":base64.b64encode(open(f,'rb').read()).decode(),"encoding":"base64"}
if sha: body["sha"]=sha
json.dump(body, open(tmp,'w'))
PY
    gh api -X PUT "repos/$REPO/contents/$enc" --input "$TEMP/_push.json" >/dev/null 2>&1 && echo "[git] $f 已推(更新)" || echo "[git] $f 失败"
    rm -f "$TEMP/_push.json" 2>/dev/null
  fi
}
push_new "lib/reportexport.js" "feat: C3 reportexport.js 付费导出报告渠道"
push_new "channels.html" "feat: C3 付费导出报告卡片 (#9)"
# 验证
echo "=== 验证 remote ==="
enc1=$(enc "$BASE/lib/reportexport.js")
gh api "repos/$REPO/contents/$enc1" -q '.content' 2>/dev/null | python -c "import sys,base64;raw=base64.b64decode(sys.stdin.read()).decode('utf-8','replace');print('  reportexport.js remote:', 'reportexport' in raw and 'complianceFooter' in raw and 'need_payment' in raw)" 2>/dev/null
echo "=== done ==="
