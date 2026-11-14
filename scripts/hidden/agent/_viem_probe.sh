#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
const keys=["privateKeyToAccount","toAccount","createWalletClient","parseAbiItem","createChain","createPublicClient","http","getAddress","publicKeyToAccount","privateKeyToAccountV2"];
keys.forEach(k=>console.log("  "+k+": "+(typeof viem[k])));
console.log("  version:", viem.version || "(n/a)");
'
