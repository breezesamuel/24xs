#!/usr/bin/env bash
# 测 /api/recovery 扁平 body + 合规红线
B="https://tools-cn.highkingflower.com/api/recovery"
echo "=== 合规红线 (扁平 body) ==="
echo "  (a) 未授权 (扫他人无主 -> 必须拒 not_authorized):"
curl -sk "$B?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"SOMEONE","amount":5000,"asset":"USDT","source":"dead_wallet"}' | head -c 140; echo
echo "  (b) 无来源:"
curl -sk "$B?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"ME","amount":10,"asset":"USDC","authorized":"true"}' | head -c 120; echo
echo "  (c) 金额非法 (0):"
curl -sk "$B?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"ME","amount":0,"asset":"USDC","source":"x","authorized":"true"}' | head -c 100; echo
echo "  (d) 合法: 本人 + 授权 + 来源:"
curl -sk "$B?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"RECOVF","amount":200,"asset":"USDC","source":"my_old_exchange","authorized":"true"}' | head -c 180; echo
echo "=== 幂等 (重复 -> duplicate) ==="
curl -sk "$B?action=record" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"RECOVF","amount":200,"asset":"USDC","source":"my_old_exchange","authorized":"true"}' | head -c 80; echo " (应 duplicate)"
echo "=== summary ==="
curl -sk "$B?ref=RECOVF" --max-time 20 | head -c 220; echo
echo "=== 清理 ==="
rm -f /var/lib/bingdashan-cn/recovery/rc:RECOVF.json /var/lib/bingdashan-cn/recovery/rc:DBG2.json 2>/dev/null
echo done
