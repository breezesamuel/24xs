#!/usr/bin/env bash
# 用 openssl 生成 secp256k1 付款钱包: 真实 32B 私钥 D + 未压缩公钥 -> viem keccak 派生 EVM 地址 -> 写 /etc/coinsettle/payout_key
# openssl 保证 D 合法 (0 < D < N)。公钥用 openssl EC 直接出未压缩 hex (绕开 node DER 坑)。
cd /www/wwwroot/tools-cn.highkingflower.com
# 1. openssl 生成 key (SEC1 ECPrivateKey) -> 转 PKCS8 (node 可 createPrivateKey)
PEM=$(mktemp /tmp/_ec_XXXX.pem)
openssl ecparam -name secp256k1 -genkey -noout -out "$PEM" 2>/dev/null
openssl pkcs8 -topk8 -nocrypt -in "$PEM" -out "${PEM}.p8" 2>/dev/null
# 2. openssl 直接出未压缩公钥 (04 x y, 65 字节 hex) —— 权威
PUBHEX=$(openssl ec -in "${PEM}.p8" -text -noout 2>/dev/null | grep -i "pub key:" | sed 's/.*pub key:[[:space:]]*//' | tr -d '\n' )
if [ -z "$PUBHEX" ]; then
  # 新版 openssl ec -text 输出 "pub key:" 多行; 取紧跟 04 的连续 hex
  PUBHEX=$(openssl ec -in "${PEM}.p8" -text -noout 2>/dev/null | grep -iE 'pub key' -A2 | grep -oE '[0-9a-fA-F]{2}' | tr -d '\n')
fi
# 3. openssl 出私钥 D: 从 ECPrivateKey 文本 "Private key:" 行
#    用 node 读 pkcs8 DER 提 D (自洽: D 来自 openssl 生成, 合法)
node - "${PEM}.p8" "$PUBHEX" <<'NODE'
const fs=require("fs"),crypto=require("crypto"),viem=require("viem");
const p8=process.argv[2], pubhex=process.argv[3];
const p8buf=fs.readFileSync(p8);
const keyObj=crypto.createPrivateKey(p8buf);
// 公钥: 用 openssl 出的未压缩 pub hex (权威, 04 x y = 130 hex)
let pt;
{
  const h=(pubhex||"").replace(/ /g,"");
  if(h.length>=130 && h.startsWith("04")){
    pt=Buffer.from(h.slice(2),"hex").slice(0,64); // x||y
  } else if(h.length>=128){
    pt=Buffer.from(h,"hex").slice(0,64);
  }
}
// 兜底: 从 keyObj 的公钥 DER 提
if(!pt||pt.length!==64){
  const pubKey=keyObj.publicKey; // KeyObject
  if(pubKey){
    const spki=pubKey.export({type:"spki",format:"der"});
    for(let i=spki.length-65;i>=0;i--){ if(spki[i]===4&&spki.length-i===65){ pt=spki.slice(i+1,i+65); break; } }
  }
}
if(!pt||pt.length!==64){ throw new Error("公钥点长度异常: "+(pt?pt.length:"null")); }
const addr="0x"+viem.keccak256(Buffer.from(pt)).slice(26);
// 私钥 D: 从 PKCS8 DER 提 (version=02 01 01 后的 04 20 <D32>)
const pk8=keyObj.export({type:"pkcs8",format:"der"});
let di=-1;
for(let i=pk8.length-70;i>=0;i--){ if(pk8[i]===2&&pk8[i+1]===1&&pk8[i+2]===1){ for(let j=i+3;j<pk8.length-32;j++){ if(pk8[j]===4&&pk8[j+1]===32){ di=j+2; break; } } break; } }
if(di<0)throw new Error("PKCS8 D 段定位失败");
const D=pk8.slice(di,di+32).toString("hex");
// 校验 0 < D < N
const N=BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A033BFD75C2F");
const Db=BigInt("0x"+D);
if(Db<=0n||Db>=N)throw new Error("D 非法 (>=N 或 0)");
fs.writeFileSync("/etc/coinsettle/payout_key","0x"+D);
fs.chmodSync("/etc/coinsettle/payout_key",0o600);
console.log("PAYOUT_ADDR="+addr);
console.log("PAYOUT_D=0x"+D);
console.log("D_valid(0<N)="+(Db>0n&&Db<N)+"  (openssl 生成, 合法私钥)");
console.log("ADDR_len="+(addr.length===42));
console.log("WROTE /etc/coinsettle/payout_key (600, "+fs.statSync("/etc/coinsettle/payout_key").size+"B)");
fs.unlinkSync(p8);
NODE
