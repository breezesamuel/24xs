#!/usr/bin/env bash
# 确定性测试: LIVE=true + 钱包空 -> 必返 insufficient_usdc (不发 tx, 不动账), 验证 ethers 实转路径
B="https://tools-cn.highkingflower.com/api"
# 造 pending 单
SID=$(curl -sk "$B/coinsettle" --max-time 25 -H "Content-Type: application/json" -X POST -d '{"ref":"demo_user_a","amount":100,"asset":"USDC","source":"earned","dest":"base_receive"}' | python -c "import sys,json;print(json.load(sys.stdin).get('entry',{}).get('id',''))")
echo "结算单: $SID"
# 开 LIVE=true (root)
sed -i 's#^COINSETTLE_CONFIRM_LIVE=.*#COINSETTLE_CONFIRM_LIVE=true#' /etc/bingdashan-cn.env
systemctl restart bingdashan-cn; sleep 3
echo "=== LIVE=true + 请求 live=true (钱包空 -> 应 insufficient_usdc, 不发 tx) ==="
curl -sk "$B/coinsettle?confirm=$SID" --max-time 25 -X POST -d '{"live":"true"}' | python -c "
import sys,json
d=json.load(sys.stdin)
print('  ok:', d.get('ok'))
print('  error:', d.get('error','(无)'))
print('  from:', d.get('from','(未广播, 好)'))
print('  have:', d.get('have','?'), ' want:', d.get('want','?'))
print('  说明:', (d.get('note','') or '')[:70])
"
# 关 LIVE=false (回到安全态)
sed -i 's#^COINSETTLE_CONFIRM_LIVE=.*#COINSETTLE_CONFIRM_LIVE=false#' /etc/bingdashan-cn.env
systemctl restart bingdashan-cn; sleep 3
echo "=== 回到 LIVE=false (安全) ==="
grep -E '^COINSETTLE_CONFIRM_LIVE=' /etc/bingdashan-cn.env
echo "=== 结算单状态 (应保持 pending, 没误转) ==="
cat /var/lib/bingdashan-cn/coinsettle_$SID.json 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);print('  status:', d.get('status'))" 2>/dev/null
rm -f /var/lib/bingdashan-cn/coinsettle_$SID.json 2>/dev/null
echo done
