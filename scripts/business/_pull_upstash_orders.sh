#!/usr/bin/env bash
# A: 拉 Vercel Upstash 里的全部 pending 订单 (9 单待付) + 出个性化挽回话术
# 依赖: F:/2026/第三轮/scripts/business/upstash.env (含 KV_REST_API_URL + KV_REST_API_TOKEN)
set -e
ENVF="F:/2026/第三轮/scripts/business/upstash.env"
if [ ! -f "$ENVF" ]; then
  echo "⛔ 缺 upstash.env。请在 F:/2026/第三轮/scripts/business/upstash.env 写两行:"
  echo "   KV_REST_API_URL=https://xxx.upstash.io"
  echo "   KV_REST_API_TOKEN=xxx"
  echo "   (Vercel 项目 bingdashan-pain-tools -> Settings -> Environment Variables 里找)"
  exit 1
fi
set -a; source "$ENVF"; set +a
[ -z "$KV_REST_API_URL" ] && { echo "⛔ KV_REST_API_URL 空"; exit 1; }
[ -z "$KV_REST_API_TOKEN" ] && { echo "⛔ KV_REST_API_TOKEN 空"; exit 1; }
echo "=== 连通 Upstash ($KV_REST_API_URL) ==="

# Upstash REST: /keys?match=bds_order_* 列键, /get/<key> 取值, /scan
echo "--- 1. 扫 bds_order_* 键 ---"
KEYS=$(curl -sk -X POST "$KV_REST_API_URL/keys?match=bds_order_*&count=200" \
  -H "Authorization: Bearer $KV_REST_API_TOKEN" 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);print(' '.join(d.get('keys',[])))" 2>/dev/null || echo "")
ORDER_KEYS=($KEYS)
echo "  找到 ${#ORDER_KEYS[@]} 个 bds_order 键"

echo "--- 2. 逐单拉取 + 解析 pending/paid ---"
> /tmp/all_orders.jsonl
for k in "${ORDER_KEYS[@]}"; do
  curl -sk "$KV_REST_API_URL/get/$k" -H "Authorization: Bearer $KV_REST_API_TOKEN" 2>/dev/null \
    | python -c "import sys,json
raw=sys.stdin.read().strip()
try: j=json.loads(raw)
except: sys.exit(0)
r=j.get('result')
if r is None: sys.exit(0)
try: rec=json.loads(r)
except: rec={}
import json as J
print(J.dumps({'key':'$k',**rec},ensure_ascii=False))" >> /tmp/all_orders.jsonl 2>/dev/null || true
done
echo "  拉到 $(wc -l < /tmp/all_orders.jsonl) 条订单记录"

echo "--- 3. 汇总: pending / paid / 各状态 ---"
python - <<'PY'
import json, collections
pend, paid, other = [], [], []
status_cnt = collections.Counter()
with open('/tmp/all_orders.jsonl') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try: o=json.loads(line)
        except: continue
        st=(o.get('status') or 'unknown').lower()
        status_cnt[st]+=1
        (pend if st=='pending' else paid if st=='paid' else other).append(o)
print("  状态分布:", dict(status_cnt))
print()
print("=== 待付订单 (pending) 明细 + 个性化话术 ===")
for i,o in enumerate(sorted(pend, key=lambda x:x.get('created_at') or x.get('at') or 0), 1):
    ref=o.get('ref') or o.get('user') or '(无ref)'
    amt=o.get('amount') or o.get('total') or '?'
    plan=o.get('plan') or o.get('slug') or '?'
    created=o.get('created_at') or o.get('at') or '?'
    print(f"  #{i} ref={ref} | {plan} | ¥{amt} | 创建于 {created}")
print()
print("=== 已付订单 (paid) 明细 (对照参考) ===")
for o in paid[:15]:
    print(f"  ref={o.get('ref') or o.get('user')} | {o.get('plan') or o.get('slug')} | ¥{o.get('amount') or o.get('total')}")
PY
echo ""
echo "=== 下一步: 把上面 pending 明细给我, 我出 3 套个性化挽回话术 (短信/微信/邮件) + 紧急度排序 + 预期收入 ==="
echo done
