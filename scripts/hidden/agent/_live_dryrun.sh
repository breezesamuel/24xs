#!/usr/bin/env bash
# live-dry-run: key 已在 /etc/coinsettle/payout_key, live 关着 -> 只读探查付款钱包在 Base 的余额 + 派生地址
# 用之前生成时算好的地址 0x0913... (若 dry-run 能派生出来更好, 否则用存储 D 回算)
echo "=== (a) 用之前那张 pending 结算单跑 confirm (key 在, live=false -> dry-run + 探查) ==="
# 先造一张 pending 结算单 (earned, 到 base_receive), 再 confirm
SID=$(curl -sk "https://tools-cn.highkingflower.com/api/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"demo_user_a","amount":100,"asset":"USDC","source":"earned","dest":"base_receive"}' | python -c "import sys,json;print(json.load(sys.stdin).get('entry',{}).get('id',''))" 2>/dev/null)
echo "  结算单: $SID"
if [ -n "$SID" ]; then
  echo "=== (b) live-dry-run 探查付款钱包 Base 余额 (不转) ==="
  curl -sk "https://tools-cn.highkingflower.com/api/coinsettle?confirm=$SID" --max-time 25 -X POST -d '{}' | python -c "
import sys,json
d=json.load(sys.stdin)
p=d.get('probe',{})
print('  dry_run:', d.get('dry_run'))
print('  key_configured:', p.get('key_configured'))
print('  payout_wallet:', p.get('payout_wallet','(未派生)'))
print('  usdc_balance:', p.get('usdc_balance','(未查到/0)'))
print('  native_balance_wei:', p.get('native_balance_wei','(未查到/0)'))
if p.get('probe_note'): print('  probe_note:', p.get('probe_note'))
"
fi
echo "=== (c) 红线仍守: 无密钥场景不受影响; 清理本测试单 ==="
rm -f /var/lib/bingdashan-cn/coinsettle_${SID}.json 2>/dev/null
echo done
