#!/usr/bin/env bash
# 用 --input (JSON 文件) 推 alipay.js (绕开 "Argument list too long")
cd /f/2026/24xs
REPO=breezesamuel/24xs
enc(){ python -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
REL=$(enc "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
ABS="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js"
SHA=$(gh api "repos/$REPO/contents/$REL" -q '.sha')
echo "sha=$SHA"
# 构造 JSON body: {message, branch, content, encoding, sha}
python - "$ABS" "$SHA" <<'PY'
import sys, json, base64
abs, sha = sys.argv[1], sys.argv[2]
content = base64.b64encode(open(abs,'rb').read()).decode()
body = {"message":"feat: wire /api/cashback route + record-on-payment in alipay.js",
        "branch":"main","content":content,"encoding":"base64","sha":sha}
json.dump(body, open('/tmp/_ali_body.json','w'))
print(f"body ready: content_b64_len={len(content)}, sha={sha[:12]}")
PY
gh api -X PUT "repos/$REPO/contents/$REL" --input /tmp/_ali_body.json -q '.content.sha' 2>&1 | head -3
echo "=== 验证 remote 已含 /api/cashback ==="
gh api "repos/$REPO/contents/$REL" -q '.content' 2>/dev/null > /tmp/_ali_b64.txt
python -c "import base64;raw=base64.b64decode(open('/tmp/_ali_b64.txt').read()).decode('utf-8','replace');print('  remote /api/cashback:', '/api/cashback' in raw, '| cashback.js:', 'cashback.js' in raw)" 2>/dev/null
echo "=== done ==="
