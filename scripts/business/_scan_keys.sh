#!/usr/bin/env bash
set -e
ENVF="F:/2026/24xs/scripts/business/upstash.env"
set -a; source "$ENVF"; set +a
API="$KV_REST_API_URL"; TOK="$KV_REST_API_TOKEN"
H=(-H "Authorization: Bearer $TOK" -H "Content-Type: application/json")
echo "=== 全部键 SCAN (看真实键名结构) ==="
OUTDIR="F:/2026/24xs/scripts/business/_data"
mkdir -p "$OUTDIR" 2>/dev/null || mkdir -p "/f/2026/24xs/scripts/business/_data"
SCANF="/f/2026/24xs/scripts/business/_data/_scan.json"
curl -sk -X POST "${H[@]}" -d '{"match":"*","count":1000,"cursor":""}' "$API/scan" 2>/dev/null > "$SCANF"
python - "$SCANF" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
ks=d.get('keys',[])
print("总键数:", len(ks))
from collections import Counter
pref=Counter()
for k in ks:
    # 取前缀 (第一个 _ 前的部分)
    p=k.split('_')[0] if k else '?'
    pref[p]+=1
print("前缀分布:", dict(pref))
print("--- 全部键名 ---")
for k in sorted(ks):
    print("  ", k)
PY
