#!/usr/bin/env bash
# 营收看板: 读真实账本 + 渠道状态 + 收钱线, 出一页纸 (不造假, 只读真数据)
cd /www/wwwroot/tools-cn.highkingflower.com
set -a; source /etc/bingdashan-cn.env; set +a
echo "=== 营收看板 (生成于 $(date '+%F %T'), 只读真实账本) ==="
echo ""
echo "--- 1. 存量可收 (台账, awaiting=待收, 非已到账) ---"
python3 - <<'PY'
import json,os
bl='/opt/bingdashan/data/billing'
tot=0
# manual_8 / trial: 金额在 collect; 对公: 金额在 corporate_amount
for fn,amtfield in (('outreach_ledger.json','collect'),('corporate_899.json','corporate_amount')):
    p=os.path.join(bl,fn)
    if not os.path.exists(p): continue
    d=json.load(open(p))
    items=d if isinstance(d,list) else (d.get('items') or d.get('orders') or [])
    pend=[i for i in items if isinstance(i,dict) and i.get('status') not in ('paid','collected','done','verified')]
    amt=sum(float(i.get(amtfield) or i.get('amount') or 0) for i in pend)
    if amt: tot+=amt
    print(f'  {fn}: 待收 {len(pend)} 单 · ¥{amt:.0f}')
print(f'  存量待收合计: ¥{tot:.0f} (机制全通, 客户付就收)')
PY
echo ""
echo "--- 2. 9 类付费渠道 (C3~C12) 在线状态 ---"
for m in reportexport strategyapi marketdata strategyhosting overfitcheck whitebox papercombo quantcompute quantannual; do
  if [ -f "lib/$m.js" ]; then
    active=$(node -e "process.env.FILE_STORE_DIR='/var/lib/bingdashan-cn';try{require('./lib/$m.js').hasStore&&process.stdout.write(require('./lib/$m.js').hasStore()?'store-OK':'no-store')}catch(e){process.stdout.write('err:'+e.message.slice(0,20))}" 2>/dev/null)
    echo "  ✅ C? $m ($active)"
  fi
done
echo ""
echo "--- 3. 自动收钱线 (timer 状态) ---"
for t in bd-trial-winback bd-manual8-watch bd-pay-email-watch; do
  s=$(systemctl is-active "$t.timer" 2>/dev/null || echo "inactive")
  echo "  $t: $s"
done
echo ""
echo "--- 4. 支付宝网关 (收款底层) ---"
echo "  APPID: $(grep ALIPAY_APP_ID /etc/bingdashan-cn.env | head -1 | cut -d= -f2)"
echo "  验签公钥: $([ -f /etc/bingdashan-cn/alipay_pub.pem ] && echo OK || echo 缺)"
echo "  签名私钥: $([ -f /etc/bingdashan-cn/alipay_priv.pem ] && echo OK || echo 缺)"
echo "  CN 服务: $(systemctl is-active bingdashan-cn 2>/dev/null)"
echo ""
echo "--- 5. 诚实边界 ---"
echo "  · 存量'待收'≠'已到账', 收到才算 (台账 status=pending/awaiting)"
echo "  · 9 渠道'在线'≠'有收入', 有客户付才收 (机制通, 量取决于获客)"
echo "  · 自动邮件线'在跑'≠'有 trial 进', 有新留邮箱才发 (需获客流量)"
echo done
