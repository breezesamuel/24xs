#!/usr/bin/env bash
# 探测 CN 可用的成熟 EVM 交易签名库 (能本地 sign RLP/EIP-155 + 正确派生地址), 避免手写 RLP
cd /www/wwwroot/tools-cn.highkingflower.com
echo "=== node_modules 里已有哪些 EVM 签名相关库 ==="
for m in ethers "@ethersproject/wallet" "@ethersproject/keccak256" "@ethersproject/rlp" "@ethersproject/transactions" "ethereumjs-tx" "@ethereumjs/tx" "ethers-v6"; do
  node -e "try{require('$m');console.log('  OK  $m');}catch(e){console.log('  无  $m');}" 2>/dev/null
done
echo "=== viem 自身是否有 signTransaction / 本地签能力 (再确认) ==="
node -e 'const v=require("viem");["signTransaction","localAccount","sign","account"].forEach(k=>console.log("  "+k+": "+typeof v[k]));' 2>&1 | head -6
echo "=== npm 能否离线装 ethers (看 node_modules 是否有缓存) ==="
ls node_modules | grep -iE "ethers|noble|secp" 2>/dev/null | head
echo "=== @noble/curves 确切版本 (确认有 sign) ==="
node -e 'try{const s=require("@noble/curves/secp256k1");console.log("  noble secp256k1: sign="+typeof (s.secp256k1||s).sign+", getPublicKey="+typeof (s.secp256k1||s).getPublicKey);console.log("  version:", require("@noble/curves/package.json").version);}catch(e){console.log("  noble err: "+e.message);}' 2>&1 | head -4
