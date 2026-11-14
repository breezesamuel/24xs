#!/usr/bin/env bash
# @noble/curves: 由 D 正确派生 secp256k1 公钥 -> keccak -> EVM 地址 (应 = 0x0913...)
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const D0=require("fs").readFileSync("/etc/coinsettle/payout_key","utf8").trim().replace(/^0x/,"");
const noble=require("@noble/curves/secp256k1");
const D=Buffer.from(D0,"hex");
// noble v2: secp256k1.getPublicKey(priv, false) -> 压缩/未压缩
let pub;
try{ pub=noble.secp256k1.getPublicKey(D,false); }catch(e){ pub=noble.getPublicKey(D,false); }
// 未压缩: 04 + x(32) + y(32) -> 取 64 字节 (x||y)
const pt=Buffer.from(pub.slice(1)); // 去掉 04 前缀
// keccak256: 用 viem.keccak256
const viem=require("viem");
const addr="0x"+viem.keccak256(pt).slice(26);
console.log("noble 派生地址: "+addr);
console.log("匹配 openssl 生成的 0x09132f96...: "+(addr.toLowerCase().indexOf("0x0913")===0));
console.log("地址 42hex: "+(addr.length===42));
' 2>&1 | head -6
