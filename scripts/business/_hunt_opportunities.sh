#!/usr/bin/env bash
# 主动出击: 扫 CN 所有"有线索但没收钱"的存量 (leads/visitors/intel/marketEvidence/assist)
python3 - <<'PY'
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
print('=== 1. leads (3条, 之前说GitHub探测的开发者) 有没有可变现 ===')
for ld in d.get('leads',[]):
    if isinstance(ld,dict):
        print('  ', json.dumps({k:ld.get(k) for k in ('id','name','company','repo','industry','signal','stage','status','plan','email','price') if ld.get(k) is not None}, ensure_ascii=False)[:200])
print()
print('=== 2. visitors (152条) 里 高价值信号 (访问过付费页/工具页 但没付费) ===')
vis=d.get('visitors',[])
paidvis=set(str(o.get('visitor')) for o in d.get('orders',[]) if o.get('paid') is True)
hot=[]
for v in vis:
    if not isinstance(v,dict): continue
    ip=str(v.get('ip') or ''); pages=v.get('pages') or v.get('visited_pages') or []
    # 访问过订阅/定价/回测相关页 且 未付费
    if any(k in str(pages) for k in ('subwall','pricing','channels','engine','backtest')):
        if str(v.get('visitor') or v.get('ip')) not in paidvis and '127_0_0_1' not in ip:
            hot.append({k:v.get(k) for k in ('ip','visitor','pages','at','ref') if v.get(k) is not None})
print('  高价值访客(看过付费页未付费):', len(hot))
for h in hot[:8]: print('   ', json.dumps(h,ensure_ascii=False)[:150])
print()
print('=== 3. intel (40条) 里 市场机会 ===')
for it in d.get('intel',[])[:6]:
    if isinstance(it,dict):
        print('  ', json.dumps({k:it.get(k) for k in ('id','type','topic','opportunity','signal','action','value') if it.get(k) is not None}, ensure_ascii=False)[:180])
print()
print('=== 4. marketEvidence (223条) 里 竞品在卖什么 (可借鉴收费点) ===')
me=d.get('marketEvidence',[])
kinds={}
for m in me[:60]:
    if isinstance(m,dict):
        k=str(m.get('source') or m.get('type') or m.get('tool') or '?')[:20]
        kinds[k]=kinds.get(k,0)+1
print('  前60条来源分布:', kinds)
# 找提到"卖/价格/订阅/收费"的
moneyev=[m for m in me if isinstance(m,dict) and any(x in json.dumps(m,ensure_ascii=False) for x in ('price','pricing','订阅','收费','¥','$','revenue','MRR','付费'))]
print('  含价格/收费信号的证据:', len(moneyev))
for m in moneyev[:5]:
    print('   ', json.dumps({k:m.get(k) for k in ('source','tool','feature','price','model','insight') if m.get(k) is not None}, ensure_ascii=False)[:180])
print()
print('=== 5. 还没被任何付费渠道覆盖的"能力" (可拓新渠道) ===')
print('  已有 8+4 渠道: bounty/cashback/writerewards/charity/bandwidth/recovery/coinsettle + C3报告/C4回测API/C5行情/C6托管')
print('  可拓: 团队席位(team)/API白标/数据API包/过拟合检测/策略进化/实盘纸面交易')
PY
echo done
