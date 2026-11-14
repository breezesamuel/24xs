#!/usr/bin/env bash
# 测 /api/coinsettle: 币结算 -> owner coinbase (合规红线: 仅 source=earned)
B="https://tools-cn.highkingflower.com/api/coinsettle"
echo "=== (a) 合法: 自己挣的币 (source=earned) -> owner coinbase ==="
curl -sk "$B" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"EARNER1","amount":150,"asset":"USDC","source":"earned","dest":"owner_coinbase"}' | head -c 240; echo
echo "=== (b) 红线: 无主资金 (source=unowned -> 必拒) ==="
curl -sk "$B" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"SCANNER","amount":5000,"asset":"USDT","source":"unowned","dest":"owner_coinbase"}' | head -c 160; echo
echo "=== (b2) 红线: airdrop 据为己有 (source=airdrop -> 必拒) ==="
curl -sk "$B" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"FAUCET","amount":800,"asset":"USDC","source":"airdrop","dest":"owner_coinbase"}' | head -c 160; echo
echo "=== (c) 缺 source (-> missing_source 拒) ==="
curl -sk "$B" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"EARNER1","amount":10,"asset":"USDC","dest":"owner_coinbase"}' | head -c 150; echo
echo "=== (d) 未知目标钱包 ==="
curl -sk "$B" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d '{"ref":"EARNER1","amount":10,"asset":"USDC","source":"earned","dest":"nope"}' | head -c 150; echo
echo "=== 清理测试账本 ==="
rm -f /var/lib/bingdashan-cn/coinsettle:*.json 2>/dev/null
echo done
