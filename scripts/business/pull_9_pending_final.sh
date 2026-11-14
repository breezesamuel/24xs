#!/usr/bin/env bash
# A 一步到位: 读 upstash.env -> 验连通 -> 拉全量 bds_order_* + orders_by_ref_* -> 出 pending 明细 + 话术 + 收入估算
# 依赖: F:/2026/第三轮/scripts/business/upstash.env
set -e
ENVF="F:/2026/24xs/scripts/business/upstash.env"
[ -f "$ENVF" ] || { echo "⛔ 缺 upstash.env (F:/2026/24xs/scripts/business/upstash.env)"; exit 1; }
set -a; source "$ENVF"; set +a
[ -z "$KV_REST_API_URL" ] && { echo "⛔ KV_REST_API_URL 空"; exit 1; }
[ -z "$KV_REST_API_TOKEN" ] && { echo "⛔ KV_REST_API_TOKEN 空"; exit 1; }
API="$KV_REST_API_URL"; TOK="$KV_REST_API_TOKEN"
H=(-H "Authorization: Bearer $TOK" -H "Content-Type: application/json")

echo "=== 0. 验连通 ==="
PING=$(curl -sk "${H[@]}" "$API/ping" 2>/dev/null || echo "{}")
echo "  ping: $(echo "$PING" | head -c 60)"
curl -sk "${H[@]}" "$API/ping" >/dev/null 2>&1 || { echo "  ⛔ 连不上 Upstash (检查 URL/token/网络)"; exit 1; }

echo "=== 1. 列 bds_order_* 键 ==="
# Upstash KEYS 端点: GET /keys?match=... (返回 {keys:[...]}) ; 备选 SCAN
KEYS_JSON=$(curl -sk "${H[@]}" "$API/keys?match=bds_order_*&count=500" 2>/dev/null || echo '{"keys":[]}')
echo "  $(echo "$KEYS_JSON" | python -c "import sys,json;print('keys:',len(json.load(sys.stdin).get('keys',[])))" 2>/dev/null)"

echo "=== 2. 逐单拉取 bds_order_* ==="
> /tmp/ao.jsonl
echo "$KEYS_JSON" | python -c "import sys,json;[print(k) for k in json.load(sys.stdin).get('keys',[])]" 2>/dev/null \
| while read -r k; do
    [ -z "$k" ] && continue
    VAL=$(curl -sk "${H[@]}" "$API/get/$(python -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$k")" 2>/dev/null || echo "")
    echo "$VAL" | python -c "
import sys,json
raw=sys.stdin.read().strip()
if not raw: sys.exit(0)
try: j=json.loads(raw)
except: sys.exit(0)
r=j.get('result')
if r is None: sys.exit(0)
try: rec=json.loads(r)
except: rec={'raw':r}
rec['__key']='$k'
print(json.dumps(rec,ensure_ascii=False))" >> /tmp/ao.jsonl 2>/dev/null || true
  done
echo "  拉到 $(wc -l < /tmp/ao.jsonl) 条 bds_order 记录"

echo "=== 3. 也扫 orders_by_ref_* (交叉核对 ref 清单) ==="
REFKEYS=$(curl -sk "${H[@]}" "$API/keys?match=orders_by_ref_*&count=500" 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);print('\n'.join(d.get('keys',[])))" 2>/dev/null || echo "")
echo "  有 $(echo "$REFKEYS" | grep -c . || echo 0) 个 orders_by_ref 索引"

echo "=== 4. 汇总 + 话术 + 收入估算 ==="
python - <<'PY'
import json, collections, time, re
recs=[]
try:
    for line in open('/tmp/ao.jsonl'):
        line=line.strip()
        if not line: continue
        try: recs.append(json.loads(line))
        except: pass
except: pass

def g(o,*ks):
    for k in ks:
        if isinstance(o,dict) and o.get(k) not in (None,''): return o[k]
    return None

# 状态归一
def st(o):
    s=str(g(o,'status','trade_status','state','pay_status') or '').upper()
    if s in ('SUCCESS','TRADE_SUCCESS','TRADE_FINISHED','PAID','SETTLED','FINISHED'): return 'paid'
    if s in ('WAIT_BUYER_PAY','WAITING','PENDING','UNPAID','WAIT'): return 'pending'
    if s in ('CLOSED','CANCEL','REFUND'): return 'closed'
    return s or 'unknown'

pend, paid, closed = [], [], []
for o in recs:
    s=st(o)
    (paid if s=='paid' else pend if s=='pending' else closed).append(o)
from collections import Counter
print("  状态分布:", dict(Counter(st(o) for o in recs)))
print()
print("=== 待付 (pending) 明细 ===")
now=time.time()
def age(o):
    t=g(o,'created_at','at','created','time')
    try: return now - float(t)
    except: return None
pend.sort(key=lambda o:(age(o) or 0), reverse=True)
total_est=0.0
for i,o in enumerate(pend,1):
    ref=str(g(o,'ref','user','invited_by') or '(无ref)')[:40]
    amt=g(o,'amount','total','price','cny') or '?'
    plan=str(g(o,'plan','slug','product') or '?')
    otp=str(g(o,'out_trade_no','id','order_id') or '?')
    a=age(o); ageh = f"{a/3600:.1f}h" if a is not None else '?'
    urg = '🔥<1h' if (a is not None and a<3600) else '⚠️<24h' if (a is not None and a<86400) else '一般'
    try: amt_f=float(amt)
    except: amt_f=0
    total_est+=amt_f
    print(f"  #{i} ref={ref} | {plan} | ¥{amt} | 单号 {otp[:24]} | 创建 {ageh} 前 | {urg}")
print()
print("=== 已付 (paid, 对照) ===")
for o in paid[:10]:
    print(f"  ref={str(g(o,'ref','user') or '?')[:32]} | {g(o,'plan','slug') or '?'} | ¥{g(o,'amount','total') or '?'}")
print()
print("=== 收入估算 (按 40% 挽回率) ===")
print(f"  待付 {len(pend)} 单 · 名义合计 ¥{total_est:.2f} · 预期挽回 (40%) ≈ ¥{total_est*0.4:.2f}")
print()
print("=== 个性化挽回话术 (按卡点匹配, 直接可用) ===")
def script_for(o):
    ref=str(g(o,'ref','user') or '')
    plan=str(g(o,'plan','slug') or '')
    a=age(o)
    # 按 ref 类型 + 时间 + 计划 匹配
    if a is not None and a<3600:
        tone="刚下的单, 最紧急"
    elif a is not None and a<86400:
        tone="24h内, 高优先"
    else:
        tone="较早, 温和跟进"
    if 'trial' in plan or 'channels' in plan:
        msg=f"【丙大山】您的 {plan} 订单({tone})还差一步。现在完成支付, 7 天解锁全部工具, 首周立减 ¥0.5。👉 [支付链接]"
    else:
        msg=f"【丙大山】您选的 {plan} 还没付 ({tone})。为您保留名额 24h, 现在完成享新人立减。👉 [支付链接]"
    return f"[ref={ref}] {msg}"
for i,o in enumerate(pend,1):
    print(f"  {i}. {script_for(o)}")
PY
echo ""
echo "=== 5. 输出可发送表格 (TSV) ==="
python - <<'PY'
import json,time
recs=[]
try:
    for line in open('/tmp/ao.jsonl'):
        line=line.strip()
        if not line: continue
        try: recs.append(json.loads(line))
        except: pass
except: pass
def g(o,*ks):
    for k in ks:
        if isinstance(o,dict) and o.get(k) not in (None,''): return o[k]
    return None
def st(o):
    s=str(g(o,'status','trade_status','state') or '').upper()
    return 'pending' if s in ('WAIT_BUYER_PAY','WAITING','PENDING','UNPAID','WAIT') else s.lower()
pend=[o for o in recs if st(o)=='pending']
with open('/tmp/pending_9.tsv','w') as f:
    f.write("rank\tref\tplan\tamount\tout_trade_no\tcreated_at\turgency\n")
    now=time.time()
    def age(o):
        t=g(o,'created_at','at','created')
        try: return now-float(t)
        except: return 1e9
    for i,o in enumerate(sorted(pend,key=age),1):
        a=age(o); urg='URGENT_1h' if a<3600 else 'URGENT_24h' if a<86400 else 'normal'
        f.write(f"{i}\t{g(o,'ref','user') or ''}\t{g(o,'plan','slug') or ''}\t{g(o,'amount','total') or ''}\t{g(o,'out_trade_no','id') or ''}\t{g(o,'created_at','at') or ''}\t{urg}\n")
    print(f"  已写 /tmp/pending_9.tsv ({len(pend)} 行)")
PY
echo "done"
