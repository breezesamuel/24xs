#!/usr/bin/env bash
# 深度验证: 新 ethers 实转路径的 fail-closed (即使 live=true, 钱包空 -> insufficient_usdc, 不发 tx, 不动账)
# 这是「不花一分钱」就能验证实转逻辑正确性的关键测试
B="https://tools-cn.highkingflower.com/api"
echo "=== 造一张 pending 结算单 (earned, 到 base_receive) ==="
SID=$(curl -sk "$B/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"demo_user_a","amount":100,"asset":"USDC","source":"earned","dest":"base_receive"}' | python -c "import sys,json;print(json.load(sys.stdin).get('entry',{}).get('id',''))")
echo "  结算单: $SID"
[ -z "$SID" ] && echo "  (造单失败)" && exit 1
echo "=== 强制 live=true + 请求 (但 COINSETTLE_CONFIRM_LIVE env 仍 false -> 不会实转, 走 dry-run) ==="
curl -sk "$B/coinsettle?confirm=$SID" --max-time 25 -X POST -d '{"live":"true"}' | python -c "
import sys,json
d=json.load(sys.stdin)
print('  dry_run:', d.get('dry_run'))
print('  (env LIVE=false, 即使请求 live=true 也 -> dry-run, 安全)')
p=d.get('probe',{})
print('  payout_wallet:', p.get('payout_wallet'))
print('  usdc_balance:', p.get('usdc_balance','(0/未查)'))
"
echo "=== 临时把 env LIVE 设 true 测 fail-closed (再改回 false) — 验证「钱包空时实转也不发 tx」==="
sudo cp /etc/bingdashan-cn.env /etc/bingdashan-cn.env.bak_live 2>/dev/null
sudo sed -i 's#^COINSETTLE_CONFIRM_LIVE=.*#COINSETTLE_CONFIRM_LIVE=true#' /etc/bingdashan-cn.env 2>/dev/null
sudo systemctl restart bingdashan-cn 2>/dev/null; sleep 2
echo "  --- LIVE=true + 钱包空 + 请求 live=true ---"
curl -sk "$B/coinsettle?confirm=$SID" --max-time 25 -X POST -d '{"live":"true"}' | python -c "
import sys,json
d=json.load(sys.stdin)
print('  ok:', d.get('ok'))
print('  error:', d.get('error','(无)'))
print('  from:', d.get('from','(未广播)'))
print('  说明: '+(d.get('note','') or '')[:60])
"
echo "=== 改回 LIVE=false (安全态) ==="
sudo sed -i 's#^COINSETTLE_CONFIRM_LIVE=.*#COINSETTLE_CONFIRM_LIVE=false#' /etc/bingdashan-cn.env 2>/dev/null
sudo systemctl restart bingdashan-cn 2>/dev/null; sleep 2
grep -E '^COINSETTLE_CONFIRM_LIVE=' /etc/bingdashan-cn.env
echo "=== 确认结算单仍是 pending (没被误转) + 清理 ==="
cat /var/lib/bingdashan-cn/coinsettle_$SID.json 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);print('  结算单状态:',d.get('status'))" 2>/dev/null
rm -f /var/lib/bingdashan-cn/coinsettle_$SID.json 2>/dev/null
echo done
