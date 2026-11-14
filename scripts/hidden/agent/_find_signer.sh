#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
echo "=== 本机可用签名库 (能正确派生地址 + 本地签名 secp256k1) ==="
for m in ethers "@ethersproject/wallet" "ethjs-wallet" "elliptic" "secp256k1" "@noble/curves" "web3"; do
  node -e "try{const m=require('$m');console.log('  $m: OK');}catch(e){console.log('  $m: 无');}" 2>/dev/null
done
echo "=== 有 secp256k1 原生吗 (node:crypto) ==="
node -e "const c=require('crypto');try{c.createECDH('secp256k1');console.log('  node:crypto secp256k1: OK');}catch(e){console.log('  node secp256k1: 无 '+e.message);}"
echo "=== 有 @noble/curves 吗 (纯 JS secp256k1, 可本地签名+派生地址) ==="
node -e "try{const s=require('@noble/curves/secp256k1');console.log('  @noble/curves: OK');}catch(e){console.log('  @noble/curves: 无');}"
