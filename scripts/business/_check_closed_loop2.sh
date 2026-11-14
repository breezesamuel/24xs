#!/usr/bin/env bash
# 深挖: 收款是否"真" — 商户密钥真读到? 订阅墙真开通过? ¥1 trial 是否真客户?
echo "=== 1. CN 支付宝密钥文件真实存在 + 可读 (file-based keys) ==="
for f in $(grep -oE "^ALIPAY_(APP_ID|MERCHANT_PRIVATE_KEY_FILE|ALIPAY_PUBLIC_KEY_FILE)=.*" /etc/bingdashan-cn.env 2>/dev/null | sed -E 's/^ALIPAY_[A-Z_]+=//; s/"//g' 2>/dev/null); do
  :
done
# 直接看 env 里的 _FILE 指向的文件是否存在
for key in ALIPAY_APP_ID ALIPAY_ACCOUNT; do
  echo "  ${key}=$(grep -E "^${key}=" /etc/bingdashan-cn.env | head -1 | cut -d= -f2-)"
done
for fkey in ALIPAY_MERCHANT_PRIVATE_KEY_FILE ALIPAY_ALIPAY_PUBLIC_KEY_FILE; do
  fp=$(grep -E "^${fkey}=" /etc/bingdashan-cn.env | head -1 | cut -d= -f2- | tr -d '"')
  if [ -f "$fp" ]; then echo "  ${fkey} -> $fp 存在 (size $(stat -c%s "$fp" 2>/dev/null))"; else echo "  ${fkey} -> $fp 不存在 ⚠️"; fi
done
echo ""
echo "=== 2. /api/config ready=True 但 env.app=None 的原因 (看 alipay.js 怎么判 ready) ==="
grep -nE "ready *:|app:!!|get\('ALIPAY_APP_ID'\)|getKey\(" /www/wwwroot/tools-cn.highkingflower.com/api/alipay.js 2>/dev/null | grep -i "ready\|config" | head -5
echo "--- 实测 config 完整返回 ---"
curl -sk "https://tools-cn.highkingflower.com/api/config" --max-time 20 | python -c "import sys,json;d=json.load(sys.stdin);print('  支付宝 ready:',d.get('ready'),'| app_id 有值:', bool(d.get('app_id')),'| account:',d.get('account'))"
echo ""
echo "=== 3. 订阅墙: 有没有任何 ref 真开通过付费订阅 (pro/pro3/proY/team) ? ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
# subwall 订阅通常存 db.subs / db.subwall / db.entitlement; 也看 db.json 里 plan 非 t 的 paid 单
orders=d.get('orders',[])
paid_nontrial=[o for o in orders if o.get('paid') is True and o.get('plan') not in ('t',None) and 'test' not in str(o.get('visitor') or '').lower()]
print('  非 trial 的 paid 订单 (真实订阅开通证据):', len(paid_nontrial))
for o in paid_nontrial[:10]:
    print('   ', o.get('id'),'| plan',o.get('plan'),'| ¥',o.get('amount'),'|',o.get('visitor'),'|',o.get('paid_at'))
# 看 db.json 是否有 activation 记录
for k in ('subs','subwall','subscriptions','entitlements','activated'):
    if k in d: print('  db.json[\"'+k+'\"]:', type(d[k]).__name__, len(d[k]) if hasattr(d[k],'__len__') else d[k])
"
echo ""
echo "=== 4. 那 3 个 ¥1 trial 是否真客户 (visitor IP 是公网非 127) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
for o in orders:
    if o.get('paid') is True:
        print('  ', o.get('id'),'| plan',o.get('plan'),'|',o.get('visitor'),'| paid_at',o.get('paid_at'),'| channel',o.get('channel'))
"
echo ""
echo "=== 5. 收款渠道真实到账金额总和 (所有网关: 支付宝+paypal+usd) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
tot=0; by_plan={}
for o in orders:
    if o.get('paid') is True:
        a=float(o.get('amount') or 0)
        tot+=a
        p=o.get('plan','?')
        by_plan[p]=by_plan.get(p,0)+a
print('  真实 paid 订单金额合计 (含 trial ¥1): ¥%.2f'%tot)
print('  按 plan:', by_plan)
print('  注: 若全是 trial(¥1), 则*真实订阅营收=0*, 商业闭环未真正跑通')
"
echo "done"
