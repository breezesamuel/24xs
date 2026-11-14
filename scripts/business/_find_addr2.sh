#!/usr/bin/env bash
# 针对性查各 EVM 链: 余额 + 是否合约 (code != 0x) -> 定位在哪条链、是什么
ADDR="0x6350761dfb1d20c30ba7ae9cb16560fbe67ddc38"
declare -A RPCS=(
  [base]="https://mainnet.base.org"
  [arbitrum]="https://arb1.arbitrum.io/rpc"
  [polygon]="https://polygon-rpc.com"
  [optimism]="https://mainnet.optimism.io"
  [bsc]="https://bsc-dataseed.binance.org"
  [avalanche]="https://api.avax.network/ext/bc/C/rpc"
)
echo "=== 各 EVM 链: 余额 + 是否合约 (code 长度) ==="
for chain in base arbitrum polygon optimism bsc avalanche; do
  rpc="${RPCS[$chain]}"
  bal=$(curl -sk --max-time 10 -X POST -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBalance\",\"params\":[\"$ADDR\",\"latest\"]}" "$rpc" 2>/dev/null | python -c "import sys,json;print(json.load(sys.stdin).get('result','?'))" 2>/dev/null)
  code=$(curl -sk --max-time 10 -X POST -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getCode\",\"params\":[\"$ADDR\",\"latest\"]}" "$rpc" 2>/dev/null | python -c "import sys,json;print(len(json.load(sys.stdin).get('result','0x'))-2)" 2>/dev/null)
  txnc=$(curl -sk --max-time 10 -X POST -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionCount\",\"params\":[\"$ADDR\",\"latest\"]}" "$rpc" 2>/dev/null | python -c "import sys,json;print(int(json.load(sys.stdin).get('result','0x0'),16))" 2>/dev/null)
  echo "  [$chain] 余额(18位精度hex)=$bal | 合约代码字节数=$code | 交易数(nonce)=$txnc"
done
echo ""
echo "=== 若某链余额>0 且是合约 -> 查其代币符号 (name/symbol, 读 0x06fd.. 标准) ==="
echo "(上面哪条链 code>0 且余额>0, 就重点看那条)"
echo done
