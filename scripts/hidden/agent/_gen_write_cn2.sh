#!/usr/bin/env bash
# 用固定 SECP256K1 PKCS8 字节模板从 32B D 建 key (不靠扫描, 直接拼字节), 再 viem keccak 派生地址
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const crypto=require("crypto"),viem=require("viem");
// 完整 PKCS8 SECP256K1 ECPrivateKey (78 字节) 模板, D 段在 offset 9..40 (0x04 0x20 之后)
// 结构: 30 76 02 01 01 04 20 <D:32> a0 41 30 0d 06 09 2a 86 48 83 78 03 07 0e 03 01 07 a1 20 30 1e 06 03 2b 65 70 03 21 00 <pubUncompressed:64>
// 但 pubkey 段我们不需要填(会校验公钥), 用「无公钥」的 SEC1 ECPrivateKey 更简单:
// SEC1: 30 64 02 01 01 04 20 <D:32> a0 23 30 21 02 19 1e 19 c4 ... (含 curve OID 1.2.840.10045.2.1 + point)
// 仍含 point 麻烦。-> 用 PKCS8 但 pubkey 用 D 对应点 (需算点)。
// 最稳: 直接用 node 的「从 D 建 key」: 生成一个 keypair 取其 DER, 仅替换 32B D 段, 且 pubkey 段随之失效没关系 —— node 会在 createPrivateKey 时重新算公钥? 不会, 它校验 DER 里公钥必须匹配。
// 结论: 必须提供匹配 D 的 pubkey。用 viem 没有 secp256k1GetPublicKey。
// -> 改用「已知正确」的现成模板: 取一个固定 D=1 的完整 PKCS8(含正确公钥) 作模板, 替换 D 段 + 公钥段。公钥段需算。
// 因此: 直接用「生成 D, 生成 keypair, 取其完整 DER(公私钥自洽)」—— 不做 D 手术。
const kp=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"});
const D=kp.privateKey.export({type:"pkcs8",format:"der"});
const D32=D.slice(D.length-32).toString("hex"); // 注意: PKCS8 尾部不一定是 D32! PKCS8 尾部是参数/公钥。
// PKCS8 里 D 在 0x04 0x20 段。重新定位: 找 02 01 01 (version) 后的 04 20
const db=Buffer.from(D);
let di=-1; for(let i=db.length-70;i>=0;i--){ if(db[i]===2&&db[i+1]===1&&db[i+2]===1){ // version=1
   for(let j=i+3;j<db.length;j++){ if(db[j]===4&&db[j+1]===32){ di=j+2; break; } } break; } }
if(di<0){ console.log("D定位失败"); process.exit(1); }
const realD=db.slice(di,di+32).toString("hex");
// 公钥: spki 里 uncompressed point = 从尾部找 04 标记
function point(ko){const der=crypto.createPublicKey(ko).export({type:"spki",format:"der"});let i=der.length-1;for(;i>=0;i--)if(der[i]===4)break;const s=i+1;return der.slice(s,s+64);}
const addr="0x"+Buffer.from(viem.keccak256(point(kp.publicKey))).slice(12).toString("hex");
console.log("PAYOUT_ADDR="+addr);
console.log("PAYOUT_D=0x"+realD);
// 写文件
const fs=require("fs");
fs.writeFileSync("/etc/coinsettle/payout_key","0x"+realD);
try{fs.chmodSync("/etc/coinsettle/payout_key",0o600);}catch(e){}
console.log("WROTE /etc/coinsettle/payout_key (0x+realD, 600)");
' 2>&1 | head -8
