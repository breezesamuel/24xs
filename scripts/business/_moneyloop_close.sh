#!/usr/bin/env bash
# 收口: 确认 timer + 清理测试假邮箱 (避免发垃圾) + 备份留档
echo "=== 1. 三个赚钱 timer 状态 ==="
for t in bd-manual8-watch bd-trial-winback bd-pay-email-watch; do
  echo "  $t: $(systemctl is-active $t 2>/dev/null)"
done
echo ""
echo "=== 2. 清理测试假邮箱 (aodm_dbg@example.com 是占位测试, 撤掉以免发垃圾) ==="
python3 - <<'PY'
import json,glob
# 从 contact_email_map 移除测试邮箱
for f in glob.glob('/var/lib/bingdashan-cn/contact_email_map.json'):
    try:
        m=json.load(open(f))
        m={k:v for k,v in m.items() if 'aodm_dbg' not in str(v) and 'winback_test' not in str(v) and 'aodm_test' not in str(v)}
        json.dump(m,open(f,'w'))
        print('  已清理 contact_email_map, 现存:', m)
    except Exception as e: print('  skip', e)
PY
echo ""
echo "=== 3. 备份留档 (CN 端改的关键文件) ==="
BK=/opt/bingdashan/data/runtime/_moneyloop_backup_$(date +%Y%m%d)
mkdir -p "$BK"
cp /opt/bingdashan/scripts/ops/send_upgrade_mail.py "$BK/" 2>/dev/null
cp /opt/bingdashan/scripts/ops/trial_winback_scan.sh "$BK/" 2>/dev/null
cp /www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs "$BK/site_cn_server.mjs" 2>/dev/null
echo "  备份到: $BK ($(ls -1 "$BK" 2>/dev/null | wc -l) 文件)"
echo ""
echo "=== 4. 当前 5 个过期 trial 里, 有邮箱能自动发的有几个 ==="
cat /opt/bingdashan/data/runtime/trial_winback.json 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('  过期:', d.get('expired_total'), '| 可自动发邮件:', d.get('auto_mailed'), '| 待人工(无邮箱):', d.get('need_contact'))
print('  (无邮箱的需人工拿联系方式, 或让他们重新注册留邮箱)')
"
echo done
