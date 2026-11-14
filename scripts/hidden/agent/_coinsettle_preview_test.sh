#!/usr/bin/env bash
# /api/coinsettle?preview — 回显「结算会打到哪」(不需密钥)
echo "=== CN coinsettle preview ==="
curl -sk "https://tools-cn.highkingflower.com/api/coinsettle?preview=1" --max-time 25 | python -c "
import sys,json
d=json.load(sys.stdin)
print('  默认收款目标: '+str(d.get('default_dest')))
print('  付款链: '+str(d.get('payout_chain'))+'  live: '+str(d.get('live'))+'  key_file: '+str(d.get('key_file')))
print('  Base USDC 合约: '+str(d.get('usdc_base_contract')))
print('  可用收款目标 (enabled, 非合约):')
for x in d.get('valid_dests',[]):
    print('    - '+x['key']+'  ['+x['chain']+']  '+x['addr']+'  '+x['role'])
"
echo "=== 对照: 结算到默认 (不带 dest, 应走 base_receive) ==="
curl -sk "https://tools-cn.highkingflower.com/api/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST -d '{"ref":"demo_user_a","amount":100,"asset":"USDC","source":"earned"}' | python -c "import sys,json;e=json.load(sys.stdin).get('entry',{});print('  dest: '+str(e.get('dest'))+' -> '+str(e.get('dest_address')))"; 
echo "=== 清理本测试单 ==="
rm -f /var/lib/bingdashan-cn/coinsettle_CS_demo_user_a_*.json 2>/dev/null
echo done
