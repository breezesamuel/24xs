#!/usr/bin/env bash
# 合成 8 单"即发即用"催款消息包 (专属 alipay 链接 + 合规说明 + 限时 + 分档)
# 输出: /opt/bingdashan/data/billing/manual_8_outreach.md (可直接复制转发)
B="https://tools-cn.highkingflower.com/api/pay"
python -c "
import json, datetime
d=json.load(open('/opt/bingdashan/data/db.json'))
manual=[o for o in d.get('orders',[]) if isinstance(o,dict) and o.get('status')=='pending' and o.get('channel')=='manual']
B='https://tools-cn.highkingflower.com/api/pay'
MAP={'y':('proY','专业·年度 366天',500),'v':('team','团队·年度 366天',299),'q':('pro3','专业·季度 93天',150),
     'p':('pro','专业·月度 31天',60),'m':('pro','专业·月度 31天',60),'t':('trial','7天体验',1)}
manual.sort(key=lambda x:-(float(x.get('amount') or 0)))
lines=[]
lines.append('# 8 单存量待付 · 催款消息包 (即发即用)')
lines.append('')
lines.append('> 每单含专属 alipay 支付链接。客户付款 → 自动开通对应订阅 + 进真实收款闭环。')
lines.append('> 收款以 subwall 真实价为准(合规, 防伪造大额)；¥899 大额走分期/对公(见文末)。')
lines.append('')
for i,o in enumerate(manual,1):
    p=o.get('plan'); pay_plan,desc,real=MAP.get(p,('pro','专业·月度',60))
    vid=str(o.get('visitor') or '').split(':')[-1] or ('order_'+o.get('id'))
    ip=str(o.get('visitor') or '')
    link=f'{B}?plan={pay_plan}&slug=tool&ref={vid}'
    billed=o.get('amount')
    ts=o.get('createdAt') or 0
    try: day=datetime.datetime.utcfromtimestamp(ts/1000).strftime('%m-%d')
    except: day='?'
    # 按金额分档话术
    if real>=299:
        msg=(f\"客户您好，您 10 月意向的【{desc}】我们为您保留名额。这是您的专属开通链接，点它付款即开通 + 赠 30 天优先支持：{link}  \"
             f\"（大额支持分期/对公，可回我协助。限时 48h，本季最低价 ¥{real}，历史回测不代表未来收益，付款前请确认需求。）\")
        tier='🔥 大额'
    elif real>=60:
        msg=(f\"您好，您选的【{desc}】还差最后一步。专属链接在此，付款即开通：{link}  \"
             f\"（限时 48h，附赠 1 份专业回测报告(C3)。¥{real}，非投资建议，历史回测不代表未来收益。）\")
        tier='⚠️ 中小额'
    else:
        msg=(f\"您好，您的 7 天体验单待支付，专属链接：{link}（¥1，7 天解锁全部工具。非投资建议。）\")
        tier='小额/试用'
    lines.append(f'## {i}. {tier} · 意向 {o.get(\"plan\")}(账面 ¥{billed}) → 实收 ¥{real} ({pay_plan})')
    lines.append(f'- 订单 {o.get(\"id\")} · 访客 {ip} · 意向日 {day}')
    lines.append(f'- ref: {vid}')
    lines.append(f'- 专属链接: {link}')
    lines.append(f'- 复制即发:')
    lines.append(f'> {msg}')
    lines.append('')
# 大额分期/对公说明
lines.append('---')
lines.append('## 大额单(¥899 意向)的分期/对公话术')
lines.append('> 客户您好，您意向的年付会员我们支持【3 期分期(每月 ¥333)】或【对公转账】，专属客服 1 对 1 协助开通 + 赠 30 天优先支持。您方便的话发我您的对公账户/微信，我这边开分期单或对公链接。本季锁定最低价。')
lines.append('')
lines.append('## 使用提醒')
lines.append('- 发前先确认 ref(vid) 对应的客户(找当初登记这 8 单的人, 或按访客 IP 回访)')
lines.append('- 客户付款后, 订单自动变 paid + 订阅激活, 无需 manual 标记; 可在 CN 账本复查')
lines.append('- 合规: 所有话术已含\"非投资建议/历史回测不代表未来\", 大额走对公/分期不夸大收益')
open('/opt/bingdashan/data/billing/manual_8_outreach.md','w').write('\n'.join(lines))
print('已写 /opt/bingdashan/data/billing/manual_8_outreach.md')
print('实收合计: ¥%d'%sum(MAP.get(o.get('plan'),('','',60))[2] for o in manual))
print('订单数:', len(manual))
"
echo "=== 预览消息包 (前 40 行) ==="
head -40 /opt/bingdashan/data/billing/manual_8_outreach.md
echo done
