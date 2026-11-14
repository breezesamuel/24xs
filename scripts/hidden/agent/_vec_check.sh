#!/usr/bin/env bash
# 修 pubkey 提取: SPKI DER 里 uncompressed point 是 0x04 + 64B, 从尾部找 04 标记取后 64 字节
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const fs=require("fs"),crypto=require("crypto"),viem=require("viem");
function spkiTail(pub){return crypto.createPublicKey(pub).export({type:"spki",format:"der"});}
function uncompressedPoint(keyObj){
  const der=spkiTail(keyObj);
  // 从尾部找 0x04, 其后 64 字节 = x||y (secp256k1 uncompressed)
  let i=der.length-1;
  for(;i>=0;i--){ if(der[i]===0x04){ break; } }
  // 确保 04 后正好 64 字节到末尾
  const start=i+1;
  if(der.length-start!==64){ throw new Error("uncompressed point 偏移异常, tailLen="+(der.length-start)); }
  return der.slice(start);
}
function evmAddr(keyObj){ return "0x"+Buffer.from(viem.keccak256(uncompressedPoint(keyObj))).slice(12).toString("hex"); }
// 已知向量: D=01 -> 0x7E5F4552091A69125d5D3Cc7471390B2C0A0d15A
function keyFromD(hexD){
  const kp=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"});
  const b=Buffer.from(kp.privateKey.export({type:"pkcs8",format:"der"}));
  let di=-1; for(let i=b.length-50;i>=0;i--){ if(b[i]===4&&b[i+1]===32){ di=i+2; break; } }
  if(di<0||b.length-di!==32)throw new Error("D 段定位失败");
  const out=Buffer.from(b); out.set(Buffer.from(hexD,"hex"),di);
  return crypto.createPrivateKey({key:out,format:"der",type:"pkcs8"});
}
const k1=keyFromD("01".padStart(64,"0"));
const a1=evmAddr(k1);
console.log("  [向量] priv=01 派生: "+a1);
console.log("  [向量] 应为        0x7E5F4552091A69125d5D3Cc7471390B2C0A0d15A");
console.log("  [向量] 匹配: "+(a1.toLowerCase()==="0x7e5f4552091a69125d5d3cc7471390b2c0a0d15a"));
' 2>&1 | head -6
