#!/usr/bin/env bash
# 生成"给登记人的一页纸执行清单" (最值钱的先收, 复制即用)
python3 - <<'PY'
import json
led=json.load(open('/opt/bingdashan/data/billing/outreach_ledger.json'))
items=[i for i in led['items'] if i['status']=='pending_outreach']
big=sorted([i for i in items if i['collect']>=299],key=lambda x:-x['collect'])
mid=sorted([i for i in items if 60<=i['collect']<299],key=lambda x:-x['collect'])
small=[i for i in items if i['collect']<60]
lines=[]
lines.append('# 存量收钱 · 一页纸执行清单 (复制即用)')
lines.append('')
lines.append('> 实收口径(合规真实价): 大额 ¥899 意向实收 ¥500(走分期/对公可补), 其余按 subwall 真实价。')
lines.append('> 客户点链接付款 → 支付宝自动到账 → 自动开通订阅, 无需人工核账。')
lines.append('> 收一笔, outreach_reconcile.sh 会自动勾掉台账里那笔。')
lines.append('')
lines.append('## 🔥 第一批先收 (最值钱, 大额 ¥500×2 + ¥299)')
lines.append('')
for i in big:
    lines.append(f'### {i["ref"]} ({i["visitor"]}) — 意向 {i["intent"]} 实收 ¥{i["collect"]}')
    lines.append(f'- 升级链接(直接发客户, 点它付款自动到账): {i["pay_link"]}')
    lines.append(f'- 复制即发话术:')
    if i['collect']>=500:
        lines.append(f'> 您好，您意向的【年付专业会员】为您保留名额。大额支持分期/对公(3期每月¥333), 专属客服1对1 + 赠30天优先支持。支付链接: {i["pay_link"]} (点它付款自动开通, 不用等人工)。历史回测不代表未来收益, 非投资建议, 付款前请确认需求。')
    else:
        lines.append(f'> 您好，您选的会员还差最后一步。支付链接: {i["pay_link"]} (付款自动开通, 限时9折+赠1份专业回测报告)。')
    lines.append('')
lines.append('## 第二批 (中小额, 批量发)')
for i in mid:
    lines.append(f'- {i["ref"]} ({i.get("visitor","")}): {i["pay_link"]}')
lines.append('')
lines.append('## 小额 + trial (¥1~60, 顺手发)')
for i in small:
    lines.append(f'- {i["ref"]}: {i["pay_link"]}')
lines.append('')
lines.append('## 收款对账 (自动)')
lines.append('- 客户付款后 db.json 自动变 paid, 跑 `bash /opt/bingdashan/scripts/ops/outreach_reconcile.sh` 自动勾台账')
lines.append('- 到账监测 `bd-manual8-watch` 每30分钟扫一次, 到账自动告警')
open('/opt/bingdashan/data/billing/ONE_PAGE.md','w').write('\n'.join(lines))
print('已写 /opt/bingdashan/data/billing/ONE_PAGE.md')
print('第一批大额 3 单实收 ¥%d (500+500+299)'%(sum(i['collect'] for i in big)))
print('全部待触达 实收合计 ¥%d'%sum(i['collect'] for i in items))
PY
echo "=== 预览一页纸 ==="
head -30 /opt/bingdashan/data/billing/ONE_PAGE.md
echo done
