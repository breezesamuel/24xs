#!/usr/bin/env bash
# 从 CN db.json 捞所有"沟通/触达/线索/邮箱/客户"资料 (找能收钱的联系方式 + 对公账号)
python3 - <<'PY'
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
print('=== 1. 所有可能的联系方式来源表 (有邮箱/电话/微信的) ===')
for key in d.keys():
    v=d.get(key)
    if isinstance(v,list):
        cnt_email=cnt_phone=0
        sample=None
        for r in v:
            if not isinstance(r,dict): continue
            s=json.dumps(r,ensure_ascii=False)
            if '@' in s and 'qq.com' not in s and 'invalid.example' not in s and 'example.com' not in s:
                cnt_email+=1
                if not sample: sample=s[:200]
            if '1' in str(r.get('phone') or r.get('mobile') or r.get('weixin') or ''):
                cnt_phone+=1
        if cnt_email or cnt_phone:
            print(f'  表 {key}: 含邮箱 {cnt_email} 条 / 含电话 {cnt_phone} 条')
            if sample: print(f'     样例: {sample}')
print()
print('=== 2. outbound / gtmTouches / conductor (外发触达记录, 看之前发过什么/给谁) ===')
for key in ('outbound','gtmTouches','conductor'):
    arr=d.get(key,[])
    print(f'  {key}: {len(arr)} 条')
    for r in arr[:5]:
        if isinstance(r,dict):
            print('    ', json.dumps({k:r.get(k) for k in ('to','target','channel','subject','type','action','ref','at','note') if r.get(k) is not None}, ensure_ascii=False)[:180])
print()
print('=== 3. mail 表 (35条, 找有没有真实客户邮箱, 非监控告警) ===')
for m in d.get('mail',[]):
    if isinstance(m,dict):
        to=m.get('to','')
        if '@' in to and '460123249' not in to and 'invalid' not in to:
            print('  客户邮件:', json.dumps({k:m.get(k) for k in ('id','to','subject','ok','at') if m.get(k) is not None},ensure_ascii=False)[:200])
print()
print('=== 4. 对公/银行账号 (收 ¥899 需要, 找真实账号信息) ===')
for key in ('settings','revenue','mail','intel','conductor'):
    v=d.get(key)
    if isinstance(v,dict):
        s=json.dumps(v,ensure_ascii=False)
        for kw in ('对公','bank','开户','户名','银行账号','corporate'):
            if kw in s: print(f'  settings/{key} 提到 {kw}: ...{s[max(0,s.index(kw)-30):s.index(kw)+60]}...'); break
print()
print('=== 5. leads 全量字段 (3条 GitHub 开发者线索, 有没有可联系邮箱) ===')
for ld in d.get('leads',[]):
    if isinstance(ld,dict):
        print('  ', json.dumps(ld,ensure_ascii=False)[:300])
PY
echo done
