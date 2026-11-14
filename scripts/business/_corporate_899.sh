#!/usr/bin/env bash
# 给 2 单 ¥899 生成对公收款单 (大额打款: 对公账号+订单号+核销指引), 复用 CN manual-verify + fulfillment
echo "=== 对公/收款账号配置 (收款进哪个对公) ==="
grep -hE "^(ALIPAY_ACCOUNT|PAYMENT|BANK|CORP|RECEIPT)" /etc/bingdashan-cn.env 2>/dev/null | sed -E 's/(=.{6}).*/\1.../' | head
# 找对公账号 (CN 收款统一进支付宝对公, 银行账号不向买家展示)
grep -hE "ALIPAY_ACCOUNT|对公|bank" /etc/bingdashan-cn.env 2>/dev/null | head -3
echo ""
python3 - <<'PY'
import json, datetime
db=json.load(open('/opt/bingdashan/data/db.json'))
orders={o['id']:o for o in db.get('orders',[]) if o.get('id') in ('mvgevdw6xm1av','mvi21kh7wvntq')}
B='https://tools-cn.highkingflower.com'
out=[]
for oid,o in orders.items():
    vid=str(o.get('visitor') or '').split(':')[-1]
    # 对公收款单: 大额 ¥899 (¥899 年付, 比 alipay 真实价 ¥500 高 ¥399, 走对公才能全收)
    out.append({
      'order_id':oid,'ref':vid,'visitor':o.get('visitor'),'plan':o.get('plan'),
      'corporate_amount':899,  # 对公按原始意向价收 (¥899 年付, 不走 alipay 套餐价限制)
      'corporate_account_note':'收款进丙大山支付宝对公账号 (银行账号以发给客户的正式对公信息为准, 不在此展示)',
      'remit_memo':f'丙大山年付-{oid}-{vid}',  # 打款备注, 核销靠这个对上号
      'verify_flow':'客户对公打款 ¥899 (备注打 remitt_memo) -> 运营在 /opt/bingdashan/web/manual-verify.html 上传打款凭证 -> /v1/pay/manual-verify 核销 -> fulfillment.advance({paid:true}) 幂等入账+激活订阅',
      'alipay_fallback':f'{B}/api/pay?plan=proY&slug=tool&ref={vid} (若客户想走支付宝, 实收¥500)',
      'status':'awaiting_remit'
    })
open('/opt/bingdashan/data/billing/corporate_899.json','w').write(json.dumps(out,ensure_ascii=False,indent=2))
print('=== 2 单 ¥899 对公收款单 (全收 ¥899, 比 alipay ¥500 多 ¥399) ===')
for i,r in enumerate(out,1):
    print(f'  {i}. {r["ref"]} ({r["visitor"]}) 单号 {r["order_id"]}')
    print(f'     打款 ¥{r["corporate_amount"]} (备注: {r["remit_memo"]})')
    print(f'     核销: {r["verify_flow"][:60]}...')
    print(f'     支付宝备选: {r["alipay_fallback"]}')
    print()
print('对公实收潜力: ¥%d (比 alipay ¥1000 多收 ¥798, 因为对公按 ¥899 原始价)'%(899*2))
print('台账已写: /opt/bingdashan/data/billing/corporate_899.json')
PY
echo "=== 确认 2 单还是 pending (没被提前勾) ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/billing/corporate_899.json'))
print('  对公单状态:', [r['status'] for r in d])
"
echo done
