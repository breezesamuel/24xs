#!/usr/bin/env python3
# 读真实台账, 生成「一键复制收款消息」HTML 交付物 (本地 F:\2026\第三轮\_批量收款消息.html)
import json, os, pathlib

bl = '/opt/bingdashan/data/billing'
outreach = json.load(open(os.path.join(bl,'outreach_ledger.json'))) if os.path.exists(os.path.join(bl,'outreach_ledger.json')) else []
corp = json.load(open(os.path.join(bl,'corporate_899.json'))) if os.path.exists(os.path.join(bl,'corporate_899.json')) else []
items = outreach if isinstance(outreach,list) else (outreach.get('items') or [])
corp_items = corp if isinstance(corp,list) else (corp.get('items') or corp.get('orders') or [])

rows_out = []
for i in items:
    rows_out.append({
        'kind': i.get('kind','?'),
        'order_id': i.get('order_id',''),
        'ref': i.get('ref',''),
        'status': i.get('status','?'),
        'billed': i.get('billed',0),
        'collect': i.get('collect',0),
        'plan': i.get('plan','?'),
        'pay_link': i.get('pay_link',''),
        'note': i.get('note',''),
    })

rows_corp = []
for i in corp_items:
    rows_corp.append({
        'order_id': i.get('order_id',''),
        'ref': i.get('ref',''),
        'amount': i.get('corporate_amount', i.get('amount',0)),
        'status': i.get('status','?'),
        'customer_name': i.get('customer_name',''),
        'remit_memo': i.get('remit_memo',''),
        'verify_flow': i.get('verify_flow',''),
        'account_note': i.get('corporate_account_note',''),
    })

pending_out = [r for r in rows_out if r['status'] not in ('paid','collected','done','verified')]
pending_corp = [r for r in rows_corp if r['status'] not in ('paid','collected','done','verified')]

total_yuan = sum(r['collect'] for r in pending_out) + sum(r['amount'] for r in pending_corp)
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>丙大山 · 批量收款消息</title>
<style>
body{{font-family:"Noto Sans SC",sans-serif;background:#0a0f1a;color:#e5e7eb;padding:24px}}
h1{{margin-bottom:8px}} .sub{{color:#9ca3af;font-size:.85rem;margin-bottom:20px}}
.card{{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:18px;margin-bottom:18px}}
h2{{font-size:1rem;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px 8px;text-align:left;border-bottom:1px solid #1f2937;font-size:.82rem}}
th{{color:#9ca3af}}
.btn{{padding:6px 12px;border-radius:8px;font-weight:600;font-size:.8rem;cursor:pointer;border:none;background:#22c55e;color:#0a0f1a}}
.btn2{{background:#1f2937;color:#e5e7eb}}
.msg-box{{background:#0d1420;border:1px solid #1f2937;border-radius:8px;padding:12px;font-size:.82rem;margin-top:8px;white-space:pre-wrap;word-break:break-all}}
.green{{color:#22c55e}} .warn{{color:#f59e0b}} .blue{{color:#3b82f6}}
.big{{font-size:2rem;font-weight:700;color:#22c55e}}
</style>
</head>
<body>
<h1>📋 丙大山 · 批量收款消息包</h1>
<div class="sub">只读真实台账 <code>/opt/bingdashan/data/billing/</code>, 不造假。每行点一次「复制」, 微信直接粘贴发送。</div>

<div class="card">
  <div class="big" style="text-align:center">¥{int(total_yuan)}</div>
  <div style="text-align:center;color:#9ca3af;font-size:.82rem">存量待收合计 (outreach {len(pending_out)}单 + 对公 {len(pending_corp)}单)</div>
  <div class="note" style="color:#9ca3af;font-size:.75rem;margin-top:10px">⚠️ "待收≠已到账", 客户付/打款才核销进账</div>
</div>

<div class="card">
  <h2>① 手动触达 / Trial 待收 ({len(pending_out)} 单)</h2>
  <table>
    <thead><tr><th>订单ID</th><th>ref</th><th>计划</th><th>应收(¥)</th><th>链接</th><th></th></tr></thead>
    <tbody>
{''.join(f"<tr><td>{r['order_id']}</td><td>{r['ref']}</td><td>{r['plan']}</td><td class='warn'>¥{int(r['collect'])}</td><td><span title='{r['pay_link']}' style='max-width:180px;overflow:hidden;display:inline-block'>{(r['pay_link'] or '?')[:50]}...</span></td><td><button class='btn btn2' onclick=\"copyMsg(this, `{r['order_id']}`, `{r['pay_link']}`)\">复制</button></td></tr>" for r in pending_out)}
    </tbody>
  </table>
</div>

<div class="card">
  <h2>② 对公打款待收 ({len(pending_corp)} 单)</h2>
  <table>
    <thead><tr><th>订单ID</th><th>金额(¥)</th><th>备注</th><th>核销流程</th><th></th></tr></thead>
    <tbody>
{''.join(f"<tr><td>{r['order_id']}</td><td class='warn'>¥{int(r['amount'])}</td><td>{r.get('remit_memo','')}</td><td style='font-size:.75rem;color:#9ca3af'>{(r.get('verify_flow') or '?')[:80]}</td><td><button class='btn btn2' onclick=\"copyCorpMsg(this, `{r['order_id']}`, {int(r['amount'])}, `{r.get('remit_memo','')}`)\">复制</button></td></tr>" for r in pending_corp)}
    </tbody>
  </table>
</div>

<script>
function copyMsg(btn, oid, link){
  const t = `【丙大山】您的订单 ${oid} 已开通，请扫码付款（¥${btn.title ? '' : '见下方'}）。\n支付链接：${link}\n注意：回测是历史数据，不代表未来收益，非投资建议。`;
  navigator.clipboard.writeText(t).then(()=>btn.textContent='✅ 已复制').catch(()=>alert('复制失败，请手动拷贝'));
}
function copyCorpMsg(btn, oid, amt, memo){
  const t = `【丙大山·年费 ¥${amt} 对公打款通知】\n订单号：${oid}\n金额：¥${amt}\n汇款备注：${memo || '年费'+oid}\n收款账户：以正式对公函为准（户名/开户行/账号见官方附件）。打款后请截图凭证，运营会审核激活。\n注意：对公打款需备注订单号，便于核销。`;
  navigator.clipboard.writeText(t).then(()=>btn.textContent='✅ 已复制').catch(()=>alert('复制失败，请手动拷贝'));
}
</script>
</body>
</html>
'''

dest = pathlib.Path("F:/2026/第三轮/_批量收款消息.html")
dest.write_text(html, encoding='utf-8')
print(f"已写 {dest} ({len(html)} bytes)")
print(f"pending outreach: {len(pending_out)}, pending corp: {len(pending_corp)}, total pending: ¥{total_yuan}")
