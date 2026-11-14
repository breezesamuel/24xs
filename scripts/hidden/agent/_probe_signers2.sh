#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
echo "=== 逐个 require (干净版) ==="
for m in ethers "@ethersproject/wallet" "@noble/curves" "@noble/hashes" "viem"; do
  node -e "try{require('$m');console.log('OK   $m');}catch(e){console.log('MISS $m');}" 2>/dev/null
done
echo "=== node_modules 实际目录 ==="
ls node_modules 2>/dev/null | grep -iE "ethers|noble|viem|secp" | head
echo "=== 能否 npm 装 ethers (有网?) ==="
npm install ethers@6 --no-save --loglevel=error 2>&1 | tail -4
