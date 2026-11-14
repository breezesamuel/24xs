#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
PEM=$(mktemp /tmp/_dbg_XXXX.pem)
openssl ecparam -name secp256k1 -genkey -noout -out "$PEM" 2>/dev/null
echo "=== openssl ec -text (pub key 段原文) ==="
openssl ec -in "$PEM" -text -noout 2>/dev/null | grep -iA3 "pub key"
echo "=== openssl ec -pubout (SubjectPublicKeyInfo PEM) ==="
openssl ec -in "$PEM" -pubout 2>/dev/null
echo "=== node: keyObj.publicKey 是什么 ==="
openssl pkcs8 -topk8 -nocrypt -in "$PEM" -out /tmp/_dbg.p8 2>/dev/null
node -e '
const crypto=require("crypto");
const ko=crypto.createPrivateKey(require("fs").readFileSync("/tmp/_dbg.p8"));
console.log("  keyObj.publicKey type: "+(ko.publicKey&&ko.publicKey.type));
console.log("  keyObj.publicKey 可 export: "+(ko.publicKey&&typeof ko.publicKey.export==="function"));
if(ko.publicKey){
  const der=ko.publicKey.export({type:"spki",format:"der"});
  console.log("  spki 长度: "+der.length+"  尾部 hex: "+der.slice(der.length-70).toString("hex"));
  // 找 04 未压缩点
  let found=-1;
  for(let i=der.length-65;i>=0;i--){ if(der[i]===4 && der.length-i===65){ found=i; break; } }
  console.log("  04 点位置: "+found+" (der.length-65="+(der.length-65)+")");
  if(found>=0){
    const pt=der.slice(found+1,found+65);
    const viem=require("viem");
    console.log("  派生地址: 0x"+viem.keccak256(pt).slice(26));
  }
}
' 2>&1 | head -12
rm -f "$PEM" /tmp/_dbg.p8
