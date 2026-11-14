#!/usr/bin/env bash
# 用 git data API (blob+tree+commit) 推 alipay.js (绕 contents API 的 62KB/JSON 问题)
cd /f/2026/24xs
REPO=breezesamuel/24xs
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
REL_ENC=$(python -c "import urllib.parse;print(urllib.parse.quote('$ABS'))")

# 1. 取 remote main 当前 commit + tree
REMOTE=$(gh api "repos/$REPO/git/refs/heads/main" -q '.object.sha')
TREE=$(gh api "repos/$REPO/git/commits/$REMOTE" -q '.tree.sha')
echo "remote main=$REMOTE tree=$TREE"

# 2. 上传 alipay.js 为 blob (base64, 用 --input 文件避免 arg 过长)
python - "$ABS" <<'PY'
import sys, json, base64
body = {"content": base64.b64encode(open(sys.argv[1],'rb').read()).decode(), "encoding":"base64"}
json.dump(body, open('/tmp/_blob_body.json','w'))
PY
BLOB=$(gh api -X POST "repos/$REPO/git/blobs" --input /tmp/_blob_body.json -q '.sha' 2>&1)
echo "new blob: $BLOB"
if [[ "$BLOB" == *message* || -z "$BLOB" ]]; then echo "blob 上传失败, 放弃"; exit 1; fi

# 3. 取全量 tree, 替换 alipay.js 项 (用 python 构造, 处理 CJK)
gh api "repos/$REPO/git/trees/$TREE?recursive=1" -q '.tree' > /tmp/_tree_items.json 2>/dev/null
python - "$ABS" "$BLOB" <<'PY' > /tmp/_newtree.json
import sys, json, urllib.parse
abs, blob = sys.argv[1], sys.argv[2]
items = json.load(open('/tmp/_tree_items.json'))
out = []
for it in items:
    p = it.get('path','')
    if p == abs or urllib.parse.unquote(p) == abs:
        out.append({"path": abs, "mode": it.get("mode","100644"), "type":"blob", "sha": blob})
    elif it.get("type") == "blob":
        out.append({"path": p, "mode": it.get("mode","100644"), "type":"blob", "sha": it["sha"]})
    # subtree 跳过 (只重建顶层, 但 GitHub tree API 需完整; 这里只改 alipay 项, 其余原样)
json.dump({"tree": out}, open('/tmp/_newtree.json','w'))
PY
NEWTREE=$(gh api -X POST "repos/$REPO/git/trees" --input /tmp/_newtree.json -q '.sha' 2>&1)
echo "new tree: $NEWTREE"
if [[ "$NEWTREE" == *message* || -z "$NEWTREE" ]]; then echo "tree 构造失败"; exit 1; fi

# 4. 造 commit (parent=remote main) + 推 main
NEWCOMMIT=$(gh api -X POST "repos/$REPO/git/commits" -f message="feat: wire /api/cashback route + record-on-payment in alipay.js" -f tree="$NEWTREE" -f "parents=$REMOTE" -q '.sha' 2>&1)
echo "new commit: $NEWCOMMIT"
if [[ "$NEWCOMMIT" == *message* || -z "$NEWCOMMIT" ]]; then echo "commit 失败"; exit 1; fi
gh api -X POST "repos/$REPO/git/refs/heads/main" -f sha="$NEWCOMMIT" >/dev/null 2>&1 \
  && echo "[push] main -> $NEWCOMMIT" || echo "[push] ref 更新失败 (可能落后)"

# 5. 验证
echo "=== 验证 remote alipay.js 含 /api/cashback ==="
gh api "repos/$REPO/contents/$REL_ENC" -q '.content' 2>/dev/null > /tmp/_ali_b64.txt
python -c "import base64;raw=base64.b64decode(open('/tmp/_ali_b64.txt').read()).decode('utf-8','replace');print('  /api/cashback:', '/api/cashback' in raw, '| cashback.js:', 'cashback.js' in raw)" 2>/dev/null
echo "=== done ==="
