#!/usr/bin/env bash
# 给 8 单 manual 生成 alipay 网关支付链接 (付款→自动到账, 不再 manual 标记)
# 映射: billing plan -> subwall pay plan + 金额 (从 /api/pay 的 PLANS/subwall 真实值)
B="https://tools-cn.highkingflower.com"
python -c "
B='https://tools-cn.highkingflower.com'
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
manual=[o for o in d.get('orders',[]) if isinstance(o,dict) and o.get('status')=='pending' and o.get('channel')=='manual']
# billing plan code -> (subwall pay plan, 真实金额, 说明)
MAP={'y':('proY',500,'专业·年度 366天'),'v':('team',299,'团队·年度 366天'),'q':('pro3',150,'专业·季度 93天'),
     'p':('pro',60,'专业·月度 31天'),'m':('pro',60,'月度会员'),'t':('trial',1,'7天体验')}
# 注: manual 单里的金额是当时登记值, 但 alipay 收款以 subwall 真实价为准(防伪造). 用真实价生成链接.
lines=['rank\torder_id\tplan\tbilled_amt\tpay_plan\treal_amt\tref\tvisitor\talipay_link']
# ref = visitor 里的 vid (用于收款后激活到对的人)
import urllib.parse
for i,o in enumerate(sorted(manual,key=lambda x:-(float(x.get('amount') or 0))),1):
    p=o.get('plan'); amt=o.get('amount')
    pay_plan, real_amt, desc = MAP.get(p,('pro',60,'月度'))
    # ref: 从 visitor 取 vid (ip:101_228_2_131:mvgeerdl -> mvgeerdl)
    vid=str(o.get('visitor') or '').split(':')[-1] or ('order_'+o.get('id'))
    link=f'{B}/api/pay?plan={pay_plan}&slug=tool&ref={urllib.parse.quote(vid)}'
    lines.append(f'{i}\t{o.get(\"id\")}\t{p}\t{amt}\t{pay_plan}\t{real_amt}\t{vid}\t{o.get(\"visitor\")}\t{link}')
open('/opt/bingdashan/data/billing/manual_8_alipay_links.tsv','w').write('\n'.join(lines)+'\n')
print('已写 /opt/bingdashan/data/billing/manual_8_alipay_links.tsv (%d 条)'%len(manual))
print()
print('=== 8 单 alipay 支付链接 (付款→自动激活对应订阅, 收款以真实价) ===')
for l in lines:
    c=l.split('\t')
    print(f'  #{c[0]} {c[1]} billing={c[2]}(¥{c[3]}) -> pay_plan={c[4]}(¥{c[5]})')
    print(f'      ref={c[6]} ({c[7]})')
    print(f'      {c[8]}')
    print()
"
echo "done"
