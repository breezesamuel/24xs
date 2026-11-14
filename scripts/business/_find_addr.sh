#!/usr/bin/env bash
# 在 CN 上查地址 0x6350761dfb1d20c30ba7ae9cb16560fbe67ddc38 属于哪条链/哪个项目
ADDR="0x6350761dfb1d20c30ba7ae9cb16560fbe67ddc38"
echo "=== 1. 各链 Blockscout: 该地址是否合约/代币/有余额 ==="
for chain in eth base polygon bsc arbitrum optimism; do
  base="https://$chain.blockscout.com"
  [ "$chain" = "bsc" ] && base="https://bsc.blockscout.com"
  [ "$chain" = "optimism" ] && base="https://optimism.blockscout.com"
  resp=$(curl -sk --max-time 12 "$base/api/v2/addresses/$ADDR" 2>/dev/null | head -c 400)
  echo "  [$chain] $resp"
done
echo ""
echo "=== 2. 币安/常见代币: 该地址是否某代币合约 (coingecko 查 token) ==="
curl -sk --max-time 12 "https://api.coingecko.com/api/v3/coins/eclipse/contracts" 2>/dev/null | head -c 200; echo
echo ""
echo "=== 3. 该地址在以太坊是否有 ETH 余额 + 交易数 (etherscan-free via rpc) ==="
# 用 public RPC 查余额 (balanceOf 不行, 查 ETH)
for rpc in "https://eth.llamarpc.com" "https://rpc.ankr.com/eth" "https://ethereum-rpc.publicnode.com"; do
  bal=$(curl -sk --max-time 12 -X POST -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBalance\",\"params\":[\"$ADDR\",\"latest\"]}" "$rpc" 2>/dev/null)
  echo "  [$rpc] eth_getBalance: $bal"
done
echo ""
echo "=== 4. 本地全盘搜 (CN 侧 /opt /www /root /var, 可能 CN 也跑过这地址) ==="
grep -rsl "$ADDR" /opt/bingdashan /www/wwwroot /root /var/lib/bingdashan-cn /etc 2>/dev/null | grep -viE "node_modules|\.git" | head -15
echo "  (大写匹配)"
grep -rsl "0X6350761DFB1D20C30BA7AE9CB16560FBE67DDC38" /opt/bingdashan /www/wwwroot /root /var/lib 2>/dev/null | head -5
echo done
