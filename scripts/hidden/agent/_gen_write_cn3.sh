#!/usr/bin/env bash
# 在 CN 生成全新有效 secp256k1 付款钱包 -> 写 /etc/coinsettle/payout_key (0x+D, 600) -> viem 派生 40-hex 地址回显
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const fs=require("fs"),crypto=require("crypto"),viem=require("viem");
function point(ko){const der=ko.export({type:"spki",format:"der"});
  for(let i=der.length-65;i>=0;i--){ if(der[i]===4 && der.length-i===65){ return der.slice(i+1,i+65); } }
  throw new Error("找不到 04 未压缩点");
}
// 从 PKCS8 DER 提取 D (32B): 定位 02 01 01 (version) 后最近的 04 20 <D32>
function dFromPkcs8(derBuf){
  const b=Buffer.from(derBuf);
  for(let i=b.length-70;i>=0;i--){ if(b[i]===2&&b[i+1]===1&&b[i+2]===1){
     for(let j=i+3;j<b.length-32;j++){ if(b[j]===4&&b[j+1]===32){ return b.slice(j+2,j+34).toString("hex"); } }
     break; } }
  return null;
}
const kp=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"});
const pk8=kp.privateKey.export({type:"pkcs8",format:"der"});
const D=dFromPkcs8(pk8);
if(!D)throw new Error("D 提取失败");
const addr="0x"+viem.keccak256(Buffer.from(point(kp.publicKey))).slice(26);
if(addr.length!==42)throw new Error("地址长度异常: "+addr.length);
fs.writeFileSync("/etc/coinsettle/payout_key","0x"+D);
try{fs.chmodSync("/etc/coinsettle/payout_key",0o600);}catch(e){}
console.log("PAYOUT_ADDR="+addr);
console.log("PAYOUT_D_fingerprint=0x"+D.slice(0,8)+"..."+D.slice(-4));
console.log("WROTE /etc/coinsettle/payout_key (0x+D, 600, 文件 "+fs.statSync("/etc/coinsettle/payout_key").size+" 字节)");
' 2>&1 | head -6
