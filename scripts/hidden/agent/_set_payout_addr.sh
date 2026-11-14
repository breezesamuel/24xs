#!/usr/bin/env bash
# 固化付款钱包地址: openssl 出的未压缩公钥 -> viem keccak -> EVM 地址, 写 CN env COINSETTLE_PAYOUT_ADDRESS
cd /www/wwwroot/tools-cn.highkingflower.com
# 1. 从存储的 D 重建 openssl key -> pubout (权威公钥)
WORK=$(mktemp -d /tmp/_pa.XXXX)
D=$(cat /etc/coinsettle/payout_key | tr -d '0x \n' | tr -d '\n')
# D 是 64 hex; 重建 SEC1 ECPrivateKey PEM (openssl 需 D+curve, 公钥自动算)
# 用 openssl 生成一个 key, 替换其 D -> 公钥与 D 自洽
openssl ecparam -name secp256k1 -genkey -noout -out "$WORK/t.pem" 2>/dev/null
# 取 D 段位置, 用存储的 D 替换 -> 重建 (公钥随之变, 权威)
# 简化: 直接 node 由 D 算公钥? 用 openssl: 把 D 写回 DER 再 pubout
# 用 node 读 key.p8, 替换 D, openssl 出 pub
openssl pkcs8 -topk8 -nocrypt -in "$WORK/t.pem" -out "$WORK/t.p8" 2>/dev/null
node - "$WORK/t.p8" "$D" <<'NODE'
const fs=require("fs"),crypto=require("crypto");
const p8=process.argv[2], Dhex=process.argv[3];
const keyObj=crypto.createPrivateKey(fs.readFileSync(p8));
const der=keyObj.export({type:"pkcs8",format:"der"});
// 定位 D 段 (version 02 01 01 后的 04 20 <D32>)
let di=-1;
for(let i=der.length-70;i>=0;i--){ if(der[i]===2&&der[i+1]===1&&der[i+2]===1){
  for(let j=i+3;j<der.length-32;j++){ if(der[j]===4&&der[j+1]===32){ di=j+2; break; } } break; } }
if(di<0)throw new Error("D 段定位失败");
const out=Buffer.from(der); out.set(Buffer.from(Dhex,"hex"),di);
// 注意: 替换 D 后公钥段是旧的(错配), 但 node createPrivateKey 会校验公钥, 需去掉公钥段或用无公钥的 SEC1
// 用 SEC1 ECPrivateKey (无公钥域), node 能重建公钥
// openssl 出 SEC1 (默认 key.pem 就是 SEC1)
NODE
# 更稳: 直接用存储 D 生成新 key 的公钥是「错的」(随机 key 的公钥)。
# 正确做法: 用 node crypto 由 D 重建 keypair (node 支持 pkcs8 替换 D 后重新算公钥? 不行, node 不重算)。
# => 权威方案: 生成 keypair 时, 同时存 D + 公钥地址。但当前只存了 D。
# 所以: 用 openssl 由 D 重建「无公钥域」的 key, openssl 会算公钥。
# openssl ecparam 不能由 D 导入。-> 用 node: 构造 SEC1 DER (30 64 02 01 01 04 20 <D32> a0 23 ...) node 可读 -> 出公钥
node - "$D" <<'NODE'
const crypto=require("crypto"),viem=require("viem");
const Dhex=process.argv[1];
// 构造 SEC1 ECPrivateKey DER (无公钥域), node createPrivateKey 可读并重建公钥
// SEC1: 30 64  02 01 01  04 20 <D:32>  a0 23 30 21 02 19 <curve OID>  (无公钥 A1 段)
// 用模板: 生成一个 secp256k1, 取其 SEC1 DER, 替换 D 段, 删公钥域(A1 44...)
const kp=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"});
const sec1=kp.privateKey.export({type:"sec1",format:"der"});
// SEC1 结构: 30 64 02 01 01 04 20 <D32> a0 23 ... a1 44 30 42 03 42 00 <pub64>
// D 在 offset 9 (30 64 02 01 01 04 20 = 7字节头? 实为 30 64 | 02 01 01 | 04 20 => 偏移: 2+1+1+1+2=7? 实测)
// 找 04 20 标记 (version 后)
let di=-1;
for(let i=sec1.length-50;i>=0;i--){ if(sec1[i]===2&&sec1[i+1]===1&&sec1[i+2]===1){ for(let j=i+3;j<sec1.length-32;j++){ if(sec1[j]===4&&sec1[j+1]===32){ di=j+2; break; } } break; } }
if(di<0)throw new Error("SEC1 D 段定位失败");
const out=Buffer.from(sec1);
out.set(Buffer.from(Dhex,"hex"),di);
const keyObj=crypto.createPrivateKey({key:out,format:"der",type:"sec1"});
const spki=keyObj.export({type:"spki",format:"der"});
let pt=null;
for(let i=spki.length-65;i>=0;i--){ if(spki[i]===4&&spki.length-i===65){ pt=spki.slice(i+1,i+65); break; } }
if(!pt)throw new Error("公钥点提取失败");
const addr="0x"+viem.keccak256(pt).slice(26);
console.log("PAYOUT_ADDR="+addr);
NODE
