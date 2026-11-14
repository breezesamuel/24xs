#!/usr/bin/env bash
# 摸清 CN 现有: 订阅到期提醒/邮件机制 + trial 用户在哪 + 怎么推升级 (复用, 不造轮子)
echo "=== 1. subwall 订阅账本 (CN file store, 找 trial 到期用户) ==="
ls -1 /var/lib/bingdashan-cn/subwall_*.json 2>/dev/null | head -20
echo "  数量: $(ls -1 /var/lib/bingdashan-cn/subwall_*.json 2>/dev/null | wc -l)"
echo ""
echo "=== 2. 逐个 subwall 账本: plan + 到期时间 (找 trial 即将到期/已到期) ==="
python -c "
import json, glob, datetime
files=glob.glob('/var/lib/bingdashan-cn/subwall_*.json')
now=datetime.datetime.now().timestamp()*1000
trial_now, soon, paid_now=[],[],[]
for f in files:
    ref=f.split('subwall_')[-1].replace('.json','')
    try: d=json.load(open(f))
    except: continue
    subs=d if isinstance(d,list) else d.get('subs',[])
    for s in subs:
        if not isinstance(s,dict): continue
        plan=s.get('plan'); exp=s.get('expires') or 0
        if s.get('status')!='active' and exp: pass
        days=(exp-now)/86400000
        if plan=='trial':
            (trial_now if days<=7 else soon).append((ref,plan,exp,days))
        elif plan in ('pro','pro3','proY','team') and s.get('paid_out'):
            paid_now.append((ref,plan,exp,days))
print('  trial 7天内到期:', len(trial_now))
for r,p,e,dd in trial_now: print('   ', r, p, '到期', dd, '天')
print('  已付费订阅在期:', len(paid_now))
for r,p,e,dd in paid_now[:10]: print('   ', r, p, '剩', dd, '天')
"
echo ""
echo "=== 3. CN 现有邮件机制 (到期提醒怎么发的) ==="
grep -rniE "续费|到期|renewal|remind|expiry|expir|7天提醒|邮件" /opt/bingdashan/infra/systemd 2>/dev/null | head
ls -1 /etc/systemd/system/bd-mail* /opt/bingdashan/infra/systemd/*mail* 2>/dev/null
echo ""
echo "=== 4. db.json trialLedger (8条) + 哪些 ref 有 trial ==="
python -c "
import json
d=json.load(open('/opt/bingdashan/data/db.json'))
tl=d.get('trialLedger',[])
print('  trialLedger 条数:', len(tl))
for t in tl[:10]:
    if isinstance(t,dict):
        print('   ', {k:t.get(k) for k in ('id','visitor','ref','plan','at','trialUsed','expiresAt') if t.get(k) is not None})
"
echo done
