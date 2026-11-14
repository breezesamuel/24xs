#!/usr/bin/env bash
# 生成 2 单 ¥899 正式打款函 (含对公账号占位 + 金额 + 备注 + 72h 有效期 + 合规免责)
python3 - <<'PY'
import json, datetime
corp=json.load(open('/opt/bingdashan/data/billing/corporate_899.json'))
acct="<在此填真实对公账号: 户名/开户行/银行账号 (不向客户展示完整前请内部确认)>"
now=datetime.datetime.now()
exp=now.strftime("%m月%d日")+" "+now.strftime("%H:%M")
lines=[]
lines.append("# 丙大山工具站 · 年付会员 · 打款函")
lines.append("")
lines.append(f"> 生成时间: {now.strftime('%Y-%m-%d %H:%M')} · 72 小时内有效 · 收款后自动开通 366 天专业·年度会员")
lines.append("> ⚠️ 合规: 本函为商务收款凭证, 非投资建议。历史回测不代表未来收益, 服务以实际交付为准, 交易风险自负。")
lines.append("")
for i,c in enumerate(corp,1):
    lines.append(f"## 打款函 {i} · 会员: {c['ref']} ({c['visitor']})")
    lines.append(f"- 订单号: {c['order_id']}")
    lines.append(f"- 项目: 专业·年度会员 (366 天) · 计划 {c['plan']}")
    lines.append(f"- **打款金额: ¥{c['corporate_amount']} (年付, 全价; 比支付宝套餐价 ¥500 多 ¥399, 含全年优先支持 + 3 份 C3 专业报告)**")
    lines.append(f"- 对公账号: {acct}")
    lines.append(f"- **打款备注(必填, 用于自动对号核销): {c['remit_memo']}**")
    lines.append(f"- 有效期: 72 小时内打款 (逾期名额释放) · 打款后 24h 内到账核销")
    lines.append(f"- 核销: 打款截图发我们 -> 上传凭证核销 -> 自动开通 + 入账 (无需等待人工反复确认)")
    lines.append(f"- 支付宝备选: {c['alipay_fallback']} (走支付宝实收 ¥500, 不占对公全价)")
    lines.append("")
    lines.append(f"--- 复制即发 (给 {c['ref']}) ---")
    lines.append(f"> 您好，为您保留【专业·年度会员】名额。对公打款 ¥{c['corporate_amount']} (户名/开户行/账号: 见附件对公信息), 打款时请备注「{c['remit_memo']}」, 72h 内有效。打款后 24h 内自动开通 366 天 + 赠 3 份专业回测报告。含全年优先支持。历史回测不代表未来收益, 非投资建议, 风险自负。")
    lines.append("")
open('/opt/bingdashan/data/billing/corporate_899_letters.md','w').write('\n'.join(lines))
print('已写 /opt/bingdashan/data/billing/corporate_899_letters.md')
print('两单合计对公实收: ¥%d'%sum(c['corporate_amount'] for c in corp))
PY
echo "=== 预览打款函 (前 30 行) ==="
head -30 /opt/bingdashan/data/billing/corporate_899_letters.md
echo done
