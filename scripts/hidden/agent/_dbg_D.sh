#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
WORK=$(mktemp -d /tmp/_dbg.XXXX)
openssl ecparam -name secp256k1 -genkey -noout -out "$WORK/key.pem" 2>/dev/null
openssl ec -in "$WORK/key.pem" -text -noout 2>/dev/null > "$WORK/_text.txt"
TXT="$WORK/_text.txt" node <<'NODE'
const fs=require("fs");
const txt=fs.readFileSync(process.env.TXT,"utf8");
const lines=txt.split(/\r?\n/).map(l=>l.replace(/^[ \t]+/,"").replace(/\s+$/,""));
function afterWord(word){
  const i=lines.findIndex(l=>l.trim().toLowerCase()===word);
  if(i<0)return "";
  let acc="";
  for(let j=i+1;j<lines.length;j++){
    const h=lines[j].replace(/:/g,"");
    if(/^[0-9a-fA-F]+$/.test(h)&&h.length>0){acc+=h;} else break;
  }
  return acc;
}
const D=afterWord("priv:");
console.log("D (64 hex): "+D);
console.log("D BigInt: "+BigInt("0x"+D));
const N=BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A033BFD75C2F");
console.log("N:         "+N);
console.log("D < N ? "+(BigInt("0x"+D)<N));
// openssl -text 的 priv: 段有时包含 curve 参数, 真正私钥可能 < 32B 或后跟 00 补齐
// 看原始字节
NODE
rm -rf "$WORK"
