#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
WORK=$(mktemp -d /tmp/_dbg.XXXX)
openssl ecparam -name secp256k1 -genkey -noout -out "$WORK/key.pem" 2>/dev/null
openssl ec -in "$WORK/key.pem" -text -noout 2>/dev/null > "$WORK/_text.txt"
TXT="$WORK/_text.txt" node <<'NODE'
const fs=require("fs"),viem=require("viem");
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
const PUB=afterWord("pub:");
console.log("priv: 行存在: "+(lines.findIndex(l=>l.trim().toLowerCase()==="priv:")>=0));
console.log("D 长度: "+D.length+"  D 前 20: "+D.slice(0,20));
console.log("PUB 长度: "+PUB.length+"  PUB 前 10: "+PUB.slice(0,10));
// D 应 64 hex (32B); PUB 应 130 hex (04+64B)
console.log("D==64: "+(D.length===64)+"  PUB==130: "+(PUB.length===130));
// 派生地址测试
let ptHex=PUB; if(ptHex.startsWith("04")&&ptHex.length===130)ptHex=ptHex.slice(2);
if(ptHex.length===128){
  const addr="0x"+viem.keccak256(Buffer.from(ptHex,"hex")).slice(26);
  console.log("派生地址: "+addr+"  len "+addr.length);
} else {
  console.log("ptHex 长度异常: "+ptHex.length);
}
NODE
rm -rf "$WORK"
