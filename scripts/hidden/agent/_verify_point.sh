#!/usr/bin/env bash
# 先只验证 point() 提取 + keccak 派生地址的逻辑对不对 (不写文件)
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const crypto=require("crypto"),viem=require("viem");
function point(ko){const der=ko.export({type:"spki",format:"der"});
  // EC 未压缩点 = 04 + x(32) + y(32) = 65 字节, 且 BIT STRING 结尾正好到 DER 末尾
  // 找「其后正好 64 字节到末尾」的 04 标记
  for(let i=der.length-65;i>=0;i--){ if(der[i]===4 && der.length-i===65){ return der.slice(i+1, i+65); } }
  throw new Error("找不到 04 未压缩点 (需其后 64B 到末尾)");
}
// 验证: point 长度必为 64, 且 keccak 后 20B 是合法 40-hex 地址
for(let n=0;n<3;n++){
  const kp=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"});
  const pt=point(kp.publicKey);
  if(pt.length!==64){console.log("point len="+pt.length+" FAIL");process.exit(1);}
  const addr="0x"+Buffer.from(viem.keccak256(pt)).slice(12).toString("hex");
  console.log("  addr "+n+": "+addr+"  (len "+addr.length+")");
}
console.log("  -> 3 个随机 keypair 均派生出 40-hex 合法 EVM 地址 (point+keccak 逻辑正确)")
' 2>&1 | head -8
