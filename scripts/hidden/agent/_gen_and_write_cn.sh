#!/usr/bin/env bash
# 在 CN 用 node crypto 生成【全新有效】secp256k1 付款钱包 -> 写 /etc/coinsettle/payout_key (存 0x+D) -> viem 派生地址回显
# 验证: 用已知测试向量 (私钥 0x0000...01 的以太坊地址 = 0x7E5F455... ) 校准 keccak/pubkey 逻辑
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const fs=require("fs"),crypto=require("crypto"),viem=require("viem");
function pubUncompressedFromKey(keyObj){return crypto.createPublicKey(keyObj).export({type:"spki",format:"der"}).slice(-65);}
function evmAddr(keyObj){const tail=pubUncompressedFromKey(keyObj);return "0x"+Buffer.from(viem.keccak256(tail.slice(1))).slice(12).toString("hex");}
// 校验: 用「已知向量」私钥 01 的公钥->地址, 应与链上 0x7E5F4552091A69125d5D3Cc7471390B2C0A0d15A (priv=1, uncompressed) 一致
function keyFromD(hexD){
  // 从 32B D 建有效 PKCS8: 用模板替换 D 段 (模板里 ECPrivateKey 的 D 段)
  const tmpl=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"}).privateKey.export({type:"pkcs8",format:"der"});
  // PKCS8(0x30 0x76): EC key 内 0x30 0x21 (ECPrivateKey) -> 0x04 <32B D> 在 ECPrivateKey 后 11 字节
  // 定位: 找 0x02 0x01 0x01 (version=1) 后的 0x04 0x20
  const b=Buffer.from(tmpl);
  const v=b.indexOf("02 01 01".replace(/ /g,"").length?Buffer.from([2,1,1]):Buffer.from([2,1,1]));
  let di=-1; for(let i=b.length-50;i>=0;i--){ if(b[i]===4&&b[i+1]===32){ di=i+2; break; } } // 0x04 0x20 后 32B
  if(di<0)throw new Error("找不到 D 段");
  const out=Buffer.from(b); out.set(Buffer.from(hexD,"hex"),di);
  return crypto.createPrivateKey({key:out,format:"der",type:"pkcs8"});
}
// 已知向量: D=01...01 -> 地址
const k1=keyFromD("01".padStart(64,"0"));
console.log("  [向量] priv=01 派生地址: "+evmAddr(k1));
console.log("  [向量] 应为           0x7E5F4552091A69125d5D3Cc7471390B2C0A0d15A");
// 生成新付款钱包
const kp=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"});
const der=kp.privateKey.export({type:"pkcs8",format:"der"});
const Dnew=der.slice(der.length-32).toString("hex");
const newKey=keyFromD(Dnew);
const newAddr=evmAddr(newKey);
fs.writeFileSync("/etc/coinsettle/payout_key","0x"+Dnew);
try{fs.chmodSync("/etc/coinsettle/payout_key",0o600);}catch(e){}
console.log("  新付款钱包地址: "+newAddr);
console.log("  已写 /etc/coinsettle/payout_key (0x+D, 600)");
' 2>&1 | head -10
