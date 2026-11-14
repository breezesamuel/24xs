#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
WORK=$(mktemp -d /tmp/_d.XXXX)
openssl ecparam -name secp256k1 -genkey -noout -out "$WORK/key.pem" 2>/dev/null
openssl ec -in "$WORK/key.pem" -pubout -out "$WORK/pub.pem" 2>/dev/null
PUB="$WORK/pub.pem" node <<'NODE'
const fs=require("fs");
const b=Buffer.from(fs.readFileSync(process.env.PUB,"utf8").replace(/[^A-Za-z0-9+/=]/g,""),"base64");
console.log("SPKI DER len: "+b.length+"  (len-65 = "+(b.length-65)+")");
console.log("tail 80 hex: "+b.slice(b.length-80).toString("hex"));
const pos=[];for(let i=0;i<b.length;i++)if(b[i]===4)pos.push(i);
console.log("0x04 positions: "+JSON.stringify(pos));
NODE
rm -rf "$WORK"
