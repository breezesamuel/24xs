#!/bin/bash
# 原子化: void db.json (master) + shard + 立即重启主服务, 防止写入覆盖
DB=/opt/bingdashan/data/db.json
OS=/opt/bingdashan/data/shards/orders.json
PS=/opt/bingdashan/data/shards/provisional.json

# 备份
cp "$DB" "$DB.bak.$(date +%s)" 2>/dev/null
cp "$OS" "$OS.bak.$(date +%s)" 2>/dev/null

# 1. void db.json (master, 审计/对账读这个)
python3 - "$DB" <<'PYEOF'
import json,sys,time
p=sys.argv[1]; d=json.load(open(p))
now=int(time.time()*1000); OID="mvklhggzx6pz0"; n=0
for it in d.get("orders",[]):
    if it.get("id")==OID:
        it["status"]="void_test"; it["paid"]=False
        it["voidReason"]="manual-provisional 无付款凭证 → 未核实, 诚实 void"; it["voidedAt"]=now; n+=1
json.dump(d,open(p,"w"),ensure_ascii=False); print("  db.json void 订单数:",n)
PYEOF
# 2. void provisional
python3 - "$PS" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1])); n=0
for it in d:
    if it.get("orderId")=="mvklhggzx6pz0": it["status"]="void"; n+=1
json.dump(d,open(sys.argv[1],"w"),ensure_ascii=False); print("  provisional 清理:",n)
PYEOF
# 3. 立即重启主服务 (让它从磁盘重载, 不再用内存旧值覆盖回去)
echo "=== 重启 bingdashan.service (主 server.js) ==="
systemctl restart bingdashan.service
sleep 5
echo "  active: $(systemctl is-active bingdashan.service)"
echo
echo "=== 重启后验证 db.json 是否保持 void ==="
python3 - "$DB" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]))
for it in d.get("orders",[]):
    if it.get("id")=="mvklhggzx6pz0":
        print("  db.json 现在: status=%s paid=%s voidReason=%s" % (it.get("status"),it.get("paid"),(it.get("voidReason") or "")[:40]))
PYEOF
echo
echo "=== 重跑审计门 + 对账门 ==="
cd /opt/bingdashan
python3 scripts/ops/ledger_audit.py 2>&1 | grep -iE "钱漏|门禁|通过|未通过|真漏网" | head -4
echo "  audit exit: ${PIPESTATUS[0]}"
/usr/local/bin/node scripts/ops/reconcile.js 2>&1 | grep -iE "每张已付|已付订单都开通|mvklhggzx6pz0" | head
echo "  reconcile exit: ${PIPESTATUS[0]}"
