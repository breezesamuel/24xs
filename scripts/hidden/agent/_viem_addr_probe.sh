#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
const raw=require("fs").readFileSync("/etc/coinsettle/payout_key","utf8").trim();
const pk=raw.startsWith("0x")?raw:"0x"+raw;
const w=viem.createWalletClient({account:pk,transport:viem.http("https://mainnet.base.org")});
console.log("typeof w.account: "+typeof w.account);
if(typeof w.account==="object"){
  console.log("  w.account.address: "+w.account.address);
  console.log("  w.account.type: "+w.account.type);
} else {
  console.log("  w.account (str): "+String(w.account).slice(0,12));
}
// 试 viem.toAccount
if(viem.toAccount){
  const a=viem.toAccount(w.account);
  console.log("  toAccount(w.account).address: "+a.address);
}
// 试 viem.getContract 或别的
// 直接用 viem 地址计算: 需要公钥. 试 viem.publicKeyToAccount?
console.log("publicKeyToAccount: "+(typeof viem.publicKeyToAccount));
console.log("privateKeyToAccount: "+(typeof viem.privateKeyToAccount));
' 2>&1 | head -10
