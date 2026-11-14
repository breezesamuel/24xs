#!/usr/bin/env python3
# 读真实台账 -> 生成 /revenue-collection.html (部署到 CN)
import json, os, sys

bl='/opt/bingdashan/data/billing'
def load(fn, key='items'):
    try:
        d=json.load(open(os.path.join(bl,fn)))
        return d if isinstance(d,list) else d.get(key,[])
    except Exception as e:
        print(f"load {fn} err:{e}",file=sys.stderr);return []

outreach_items=load('outreach_ledger.json','items')
corp_items=load('corporate_899.json','items') or load('corporate_899.json','orders')
PENDING={'paid','collected','done','verified'}

rows=[]
for i in outreach_items:
    rows.append({'kind':'manual' if i.get('kind')=='manual_8' else ('trial' if 'trial' in str(i.get('kind','')), 'other'),'oid':i.get('order_id',''),'ref':i.get('ref',''),'status':i.get('status','?'),'amount':i.get('collect',0),'link':i.get('pay_link',''),'note':str(i.get('note',''))})
for i in corp_items:
    rows.append({'kind':'corp','oid':i.get('order_id',''),'ref':i.get('ref',''),'status':i.get('status','?'),'amount':i.get('corporate_amount') or i.get('amount',0),'memo':i.get('remit_memo',''),'note':str(i.get('account_note','')),'verify_flow':i.get('verify_flow','')})

pending=[r for r in rows if r['status'] not in PENDING]
total=sum(r['amount'] for r in pending)
print(f"PENDING={len(pending)} TOTAL_YUAN={total}")
for r in pending[:5]: print(json.dumps(r,ensure_ascii=False)[:160])

# build html
h="""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>丙大山 · 批量收款消息</title>
<style>body{font-family:"Noto Sans SC",sans-serif;background:#0a0f1a;color:#e5e7eb;padding:20px}
h1{margin-bottom:6px}.sub{color:#9ca3af;font-size:.82rem;margin-bottom:20px}
.card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:16px;margin-bottom:16px}
.big{text-align:center;font-size:2.4rem;font-weight:700;color:#22c55e}.small{color:#9ca3af;font-size:.8rem}
table{width:100%;border-collapse:collapse}.th,.td{padding:9px 8px;text-align:left;border-bottom:1px solid #1f2937;font-size:.82rem}.th{color:#9ca3af;font-weight:600}
.btn{padding:6px 10px;border-radius:8px;font-size:.78rem;cursor:pointer;border:none;background:#22c55e;color:#0a0f1a;font-weight:600}.btn2{background:#1f2937;color:#e5e7eb}
.msg{background:#0d1420;border:1px solid #1f2937;border-radius:8px;padding:10px;font-size:.8rem;margin-top:6px;white-space:pre-wrap;word-break:break-all;display:none}
.copy-ok{color:#22c55e}.warn{color:#f59e0b}</style></head>
<body>
<h1>📋 丙大山 · 批量收款消息</h1>
<div class="sub">只读真实台账 <code>/opt/bingdashan/data/billing/</code>, 不造假。每行点「复制」得一条微信可直接粘贴的消息。</div>
<div class="card"><div class="big">¥%d</div><div class="small">存量待收合计 (%d 单, 客户付/打款才核销进账)</div><div class="small" style="margin-top:8px">⚠️ "待收≠已到账" —— 收到才算收入</div></div>
<div class="card"><h2>待收明细 (%d 单)</h2>
<table class="t"><thead><tr class="th"><th>ID</th><th>类型</th><th>金额</th><th>链接/备注</th><th>操作</th></tr></thead><tbody id="tb"></tbody></table></div>
<script>
var ROWS=%s;
var tb=document.getElementById('tb');
ROWS.forEach(function(r,i){
  var tr=document.createElement('tr');
  tr.innerHTML='<td>'+r.oid+'</td><td>'+(r.kind||'?')+'</td><td class="warn">¥'+r.amount+'</td><td style="font-size:.75rem;color:#9ca3af">'+(r.link||'').slice(0,40)+'.../'+(r.note||'').slice(0,40)+'</td><td><button class="btn btn2" id="b'+i+'">复制</button></td>';
  tb.appendChild(tr);
  document.getElementById('b'+i).onclick=function(){
    var msg;
    if(r.link){msg='【丙大山·支付提醒】\n您的订单 '+r.oid+' 已开通。\n付款链接：'+r.link+'\n注意：回测是历史数据，不代表未来收益；非投资建议，风险自负。'}
    else{msg='【丙大山·年费 '+r.amount+' 元 对公打款提醒】\n订单号：'+r.oid+'\n金额：¥'+r.amount+'\n汇款备注：'+(r.memo||'年费'+r.oid)+'\n收款账户：以正式对公函为准（见运营附件）。\n打款后请截图凭证发至客服，我们会核销激活。\n注意：对公打款需备注订单号便于核销。'}
    navigator.clipboard.writeText(msg).then(function(){document.getElementById('b'+i).textContent='✅ 已复制';document.getElementById('b'+i).classList.add('copy-ok');}).catch(function(){prompt('复制失败, 请手动拷贝：',msg);});
  };
});
</script>
<div class="sub" style="margin-top:24px">来源: <code>/opt/bingdashan/data/billing/outreach_ledger.json</code> + <code>corporate_899.json</code> · 生成的时间: %s</div>
</body></html>"""

now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
from datetime import datetime
html=h%(total, len(pending), len(pending), json.dumps(pending, ensure_ascii=False, indent=2), now)
dest='/www/wwwroot/tools-cn.highkingflower.com/revenue-collection.html'
open(dest,'w',encoding='utf-8').write(html)
print("WROTE:",dest,len(html),"bytes")
