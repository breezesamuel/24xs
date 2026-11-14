#!/usr/bin/env bash
# 实测: 订阅墙+收款是否真实现 (商户密钥配置 + 真实到账证据)
echo "=== 1. CN 商户密钥配置 (env 文件, 只看键名+是否非空, 不打印密钥值) ==="
ENVF=/etc/bingdashan-cn.env
if [ -f "$ENVF" ]; then
  grep -oE "^(ALIPAY_[A-Z_]+|STRIPE_[A-Z_]+|PAYPAL_[A-Z_]+|WECHAT_[A-Z_]+|SUPABASE_[A-Z_]+|KV_REST_[A-Z]+)=" "$ENVF" 2>/dev/null | sort -u | while read -r key; do
    varname="${key%=}"
    val=$(grep -E "^${varname}=" "$ENVF" 2>/dev/null | head -1 | cut -d= -f2-)
    if [ -z "$val" ]; then echo "  ${varname}: (空/未配)"; else echo "  ${varname}: 已配 (len=${#val})"; fi
  done
else
  echo "  无 $ENVF"
fi
echo ""
echo "=== 2. CN 站点实际读到的网关 ready 状态 (/api/config 的 ready 字段) ==="
curl -sk "https://tools-cn.highkingflower.com/api/config" --max-time 20 | python -c "
import sys,json
try:
  d=json.load(sys.stdin)
  print('  store:', d.get('store'))
  print('  ready (支付宝):', d.get('ready'))
  print('  env: app=%s priv=%s pub=%s'%(d.get('env',{}).get('app'), d.get('env',{}).get('priv'), d.get('env',{}).get('pub')))
  print('  wallets:', list((d.get('wallets') or {}).keys()))
except Exception as e:
  print('  parse err:', e)
" 2>/dev/null
echo ""
echo "=== 3. Vercel 生产网关 ready 状态 ==="
curl -sk "https://tools.highkingflower.com/api/config" --max-time 20 | python -c "
import sys,json
try:
  d=json.load(sys.stdin)
  print('  store:', d.get('store'))
  print('  ready (支付宝):', d.get('ready'))
  print('  env: app=%s priv=%s pub=%s'%(d.get('env',{}).get('app'), d.get('env',{}).get('priv'), d.get('env',{}).get('pub')))
except Exception as e:
  print('  parse err:', e)
" 2>/dev/null
echo ""
echo "=== 4. 真实到账证据: reconcile_latest.json 的 money (CN 生产账本) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/runtime/reconcile_latest.json'))
m=d.get('money',{})
print('  generatedAt:', d.get('generatedAt'))
print('  money.available:', m.get('available'))
print('  revenue(真实到账):', m.get('revenue'), '· gross:', m.get('grossRevenue'), '· net:', m.get('net'))
print('  testRevenue(自测):', m.get('testRevenue'), '· testCount:', m.get('testCount'))
print('  pending(挂账):', m.get('pending'), '· count:', m.get('pendingCount'))
print('  refunded:', m.get('refunded'), '· writtenOff:', m.get('writtenOff'))
print('  foreign(外币):', m.get('foreign'), '· foreignTotal:', m.get('foreignTotal'))
" 2>/dev/null
echo ""
echo "=== 5. 真实付费订单 (db.json 里 status=paid 的非自测单) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
orders=d.get('orders',[])
paid=[o for o in orders if o.get('paid') is True]
real=[o for o in paid if not ('test' in str(o.get('visitor') or '').lower() or '127_0_0_1' in str(o.get('visitor') or ''))]
print('  paid 订单:', len(paid), '· 其中非自测:', len(real))
for o in real[:10]:
    print('   ', o.get('id'), '| plan', o.get('plan'), '| ¥', o.get('amount'), o.get('currency','CNY'), '|', o.get('visitor'))
" 2>/dev/null
echo ""
echo "=== 6. 订阅墙 activate 的真实调用证据 (有没有 ref 被开通过订阅) ==="
grep -c "activate" /opt/bingdashan/data/db.json 2>/dev/null
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
subs=d.get('subs') or d.get('subwall') or []
print('  db.json 顶层有 subs/subwall 键:', [k for k in d.keys() if 'sub' in k.lower() or 'wall' in k.lower()])
# 找 entitlement/activation 记录
for k in d.keys():
    v=d.get(k)
    if isinstance(v,list) and v and isinstance(v[0],dict) and any('plan' in str(x.get('','')) for x in v[:3] if isinstance(x,dict)):
        print('  可能订阅表:', k, len(v))
" 2>/dev/null
echo "done"
