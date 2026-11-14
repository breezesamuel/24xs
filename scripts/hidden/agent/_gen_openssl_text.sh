#!/usr/bin/env bash
# openssl 生成 secp256k1 付款钱包: 用 `openssl ec -text` 直接出私钥/公钥 hex (权威, 绕开 DER 猜测)
cd /www/wwwroot/tools-cn.highkingflower.com
WORK=$(mktemp -d /tmp/_w.XXXX)
openssl ecparam -name secp256k1 -genkey -noout -out "$WORK/key.pem" 2>/dev/null
# openssl ec -text -noout 输出:
#   Private key:  <64 hex, 可能换行>
#   pub key: <04 x y 130 hex, 可能换行>
TXT=$(openssl ec -in "$WORK/key.pem" -text -noout 2>/dev/null)
echo "$TXT" > "$WORK/_text.txt"
# 派生地址 + 写文件 (node 解析 _text.txt)
TXT="$WORK/_text.txt" P8="$WORK/key.pem" node <<'NODE'
const fs=require("fs"),crypto=require("crypto"),viem=require("viem");
function grab(label){
  const lines=fs.readFileSync(process.env.TXT,"utf8").split(/\r?\n/).map(l=>l.trim());
  // 找 label 行, 取其后所有连续 hex-only 行拼起来
  let i=lines.findIndex(l=>l.startsWith(label+":")||l.startsWith(label+':'));
  if(i<0) return "";
  let acc=lines[i].replace(/^[^:]*:\s*/,"");
  for(let j=i+1;j<lines.length;j++){ if(/^[0-9a-fA-F]+$/.test(lines[j])){acc+=lines[j];} else break; }
  return acc;
}
// 私钥
let D=grab("Private key").replace(/[^0-9a-fA-F]/g,"");
if(D.length!==64){
  // 兼容: 有的 openssl 把私钥放在 PKCS8, 用 node 从 PEM 提
  const p8=crypto.createPrivateKey(fs.readFileSync(process.env.P8,"utf8"));
  const der=p8.export({type:"pkcs8",format:"der"});
  for(let i=0;i+3<=der.length;i++){ if(der[i]===2&&der[i+1]===1&&der[i+2]===1){const o=i+3;if(o+3<=der.length&&der[o]===4&&der[o+1]===32){D=der.slice(o+2,o+34).toString("hex");break;}} }
}
if(D.length!==64)throw new Error("私钥 D 提取失败 (text+pkcs8 都拿不到 32B)");
// 公钥
let PUB=grab("pub key").replace(/[^0-9a-fA-F]/g,"");
// pub key 行: 04 x y (130 hex) 或 04 + 分段
let pt;
if(PUB.startsWith("04")&&PUB.length>=130){ pt=Buffer.from(PUB.slice(2,130),"hex"); }
else { // 从 SPKI PEM 提 (openssl 也可 pubout)
  const spki=crypto.createPublicKey(crypto.createPrivateKey(fs.readFileSync(process.env.P8,"utf8")).publicKey||crypto.createPrivateKey(fs.readFileSync(process.env.P8,"utf8")));
}
if(!pt){ // 兜底: 用 node 由 D 算公钥? 不可行。用 openssl 出的 SPKI base64
  // 重新 pubout
}
// 简化: 直接用 SPKI (node 从 PKCS8 派公钥)
const pkobj=crypto.createPrivateKey(fs.readFileSync(process.env.P8,"utf8"));
const spki=pobj.spki?null:null;
NODE
rm -rf "$WORK"
