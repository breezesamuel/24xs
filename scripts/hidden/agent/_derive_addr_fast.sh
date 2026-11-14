#!/usr/bin/env bash
# 仅派生地址 (不查余额, 快)
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const fs=require("fs"),crypto=require("crypto"),viem=require("viem");
const raw=fs.readFileSync("/etc/coinsettle/payout_key","utf8").trim();
let D=(raw.startsWith("0x")?raw:"0x"+raw.replace(/[^0-9a-fA-F]/g,"")).toLowerCase();
if(D.length!==66)throw new Error("D len="+D.length);
const tmpl=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"}).privateKey.export({type:"pkcs8",format:"der"});
const pk8=Buffer.from(tmpl);let idx=-1;for(let i=pk8.length-40;i>=0;i--){if(pk8[i]===0x04&&pk8[i+1]===0x20){idx=i;break;}}
if(idx<0)throw new Error("no 0420 marker");
const out=Buffer.from(pk8);out.set(D.slice(2).match(/.{1,2}/g).map(b=>parseInt(b,16)),idx+2);
const ko=crypto.createPrivateKey({key:out,format:"der",type:"pkcs8"});
const pu=crypto.createPublicKey(ko).export({type:"spki",format:"der"});
const tail=pu.slice(pu.length-65);
if(tail[0]!==4)throw new Error("not uncompressed");
console.log("PAYOUT_ADDR=0x"+Buffer.from(viem.keccak256(tail.slice(1))).slice(12).toString("hex"));
console.log("D_fingerprint="+D.slice(2,10)+"..."+D.slice(-4));
' 2>&1 | head -4
