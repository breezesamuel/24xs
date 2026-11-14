#!/usr/bin/env bash
# 验证 CN viem: createWalletClient({account: privateKeyHex}) 是否可行 + 能否派生地址
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
const raw=require("fs").readFileSync("/etc/coinsettle/payout_key","utf8").trim();
const pk=raw.startsWith("0x")?raw:"0x"+raw;
console.log("pk 前缀: "+pk.slice(0,6)+"...  长度: "+pk.length);
// viem createWalletClient 接受 account 为 privateKey (hex string) —— 试
try{
  const w=viem.createWalletClient({account:pk, transport:viem.http("https://mainnet.base.org")});
  console.log("createWalletClient({account: pk}) OK, client 有 writeContract: "+!!w.writeContract);
  // viem 的 wallet client 能取本地地址? 通过 request + 查余额可间接验证
} catch(e){ console.log("createWalletClient({account: pk}) 失败: "+e.message); }
// 试 viem 是否有其它派生地址 API
const fns=["toAccount","publicToAccount","privateToAccount","getAddress"];
fns.forEach(f=>console.log("  "+f+": "+typeof viem[f]));
' 2>&1 | head -10
