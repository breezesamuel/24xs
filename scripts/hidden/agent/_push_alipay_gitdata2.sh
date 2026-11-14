#!/usr/bin/env bash
# 推 alipay.js 到 remote (git data API, 用 Windows 绝对 temp 路径避免 /tmp 不匹配)
cd /f/2026/24xs
REPO=breezesamuel/24xs
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
ABS_ENC=$(python -c "import urllib.parse;print(urllib.parse.quote('$ABS'))")
TMPB="$TEMP/_ali_blob.json"; TMPT="$TEMP/_ali_tree.json"; TMPC="$TEMP/_ali_commit.json"; TMPO="$TEMP/_ali_out"
echo "TEMP=$TEMP"
# 1. remote main + tree
REMOTE=$(gh api "repos/$REPO/git/refs/heads/main" -q '.object.sha'); echo "remote=$REMOTE"
TREE=$(gh api "repos/$REPO/git/commits/$REMOTE" -q '.tree.sha'); echo "tree=$TREE"
# 2. blob (用 --input, Windows 路径)
python - "$ABS" > "$TMPB" <<'PY'
import sys, json, base64
json.dump({"content": base64.b64encode(open(sys.argv[1],'rb').read()).decode(), "encoding":"base64"}, open(sys.argv[2],"w"))
PY
# 上面 python 写到 TMPB 需传参; 用更简单: 直接生成 blob body 文件
python - "$ABS" <<'PY' > /dev/null
import sys, json, base64, os
tmp = os.environ.get('TEMP','/tmp') + '/_ali_blob.json'
json.dump({"content": base64.b64encode(open(sys.argv[1],'rb').read()).decode(), "encoding":"base64"}, open(tmp,"w"))
PY
BLOB=$(gh api -X POST "repos/$REPO/git/blobs" --input "$TMPB" -q '.sha' 2>&1); echo "blob=${BLOB:0:14}"
if [[ "$BLOB" == *message* || -z "$BLOB" ]]; then echo "blob 失败"; exit 1; fi
# 3. 全量 tree -> 替换 alipay 项
gh api "repos/$REPO/git/trees/$TREE?recursive=1" -q '.tree' > "$TMPT" 2>/dev/null
python - "$ABS" "$BLOB" <<'PY'
import sys, json, urllib.parse, os
abs, blob = sys.argv[1], sys.argv[2]
tmp = os.environ.get('TEMP','/tmp')
items = json.load(open(tmp + '/_ali_tree.json'))
out = []
for it in items:
    p = it.get('path','')
    if p == abs or urllib.parse.unquote(p) == abs:
        out.append({"path": abs, "mode": it.get("mode","100644"), "type":"blob", "sha": blob})
    elif it.get("type") == "blob":
        out.append({"path": p, "mode": it.get("mode","100644"), "type":"blob", "sha": it["sha"]})
json.dump({"tree": out}, open(tmp + '/_ali_newtree.json','w'))
print("tree items:", len(out))
PY
NEWTREE=$(gh api -X POST "repos/$REPO/git/trees" --input "$TEMP/_ali_newtree.json" -q '.sha' 2>&1); echo "newtree=${NEWTREE:0:14}"
if [[ "$NEWTREE" == *message* || -z "$NEWTREE" ]]; then echo "tree 失败: $(head -c 100 <<<"$NEWTREE")"; exit 1; fi
# 4. commit + push ref
NEWCOMMIT=$(gh api -X POST "repos/$REPO/git/commits" -f message="feat: wire /api/{cashback,writerewards} routes + record-on-payment in alipay.js" -f tree="$NEWTREE" -f "parents=$REMOTE" -q '.sha' 2>&1); echo "commit=${NEWCOMMIT:0:14}"
if [[ "$NEWCOMMIT" == *message* || -z "$NEWCOMMIT" ]]; then echo "commit 失败"; exit 1; fi
gh api -X POST "repos/$REPO/git/refs/heads/main" -f sha="$NEWCOMMIT" >/dev/null 2>&1 && echo "[push] main -> $NEWCOMMIT" || echo "[push] ref 落后, 需重试"
# 5. 验证
echo "=== 验证 remote alipay.js 含 /api/writerewards ==="
gh api "repos/$REPO/contents/$ABS_ENC" -q '.content' 2>/dev/null > "$TMPO"
python -c "import base64;raw=base64.b64decode(open('$TMPO').read()).decode('utf-8','replace');print('  /api/cashback:', '/api/cashback' in raw, '| /api/writerewards:', '/api/writerewards' in raw)" 2>/dev/null
rm -f "$TMPB" "$TMPT" "$TEMP/_ali_newtree.json" "$TMPO" 2>/dev/null
echo "=== done ==="
