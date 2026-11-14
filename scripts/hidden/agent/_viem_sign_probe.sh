#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
const raw=require("fs").readFileSync("/etc/coinsettle/payout_key","utf8").trim();
const pk=raw.startsWith("0x")?raw:"0x"+raw;
// viem 能否用这个 D 签名? (不实际广播, 只 sign)
const wallet=viem.createWalletClient({account:pk,transport:viem.http("https://mainnet.base.org")});
(async()=>{
  // 1) 尝试钱包的 getAddresses / sign 能力
  console.log("wallet.account keys: "+Object.keys(wallet.account||{}).join(","));
  // 2) 试 signMessage (不广播, 纯签名) 验证私钥可用
  try{
    const sig=await wallet.signMessage({account:wallet.account,message:{raw:"0x01"},chainId:8453n}).catch(e=>"ERR:"+e.message);
    console.log("signMessage: "+(typeof sig==="string"&&sig.startsWith("0x")?"OK (私钥可签名, 长度 "+sig.length+")":sig));
  }catch(e){ console.log("sign 失败: "+e.message); }
  // 3) 派生地址: 用 viem 的 getAddress? 需公钥。用 openssl 已算的 0x0913... 作权威。
  //    这里只确认「viem 认这个 D 为可签名私钥」
})().catch(e=>console.log("err: "+e.message));
' 2>&1 | head -8
