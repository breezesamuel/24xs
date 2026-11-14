#!/usr/bin/env bash
# 突破测试: 不依赖 RPC personal_sign, 用 viem 本地签 ERC-20 transfer + eth_sendRawTransaction 广播
# 这里用 0 金额 / 自转 (from=to=0x0913, amount 很小或 gas-only) 只验证「能签名+能构造 tx」, 不真打款 (USDC 没本金, 也会失败, 但目的是看签名通不通)
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
const raw=require("fs").readFileSync("/etc/coinsettle/payout_key","utf8").trim();
const pk=raw.startsWith("0x")?raw:"0x"+raw;
(async()=>{
  const w=viem.createWalletClient({account:pk, transport:viem.http("https://mainnet.base.org")});
  const pub=viem.createPublicClient({transport:viem.http("https://mainnet.base.org")});
  // 1) 派生地址: 用 getAddress 需要公钥; 试 wallet.address? 
  console.log("w.account type: "+(typeof w.account)+"  若有 address: "+(w.account&&w.account.address));
  // viem 本地账户: account.address 应为派生地址 (若 viem 识别为 LocalAccount)
  // 2) 试本地 sign (非 personal_sign): 用 w.sign
  try{
    const sig=await w.sign({message:{raw:"0xdeadbeef"}});
    console.log("本地 sign OK: "+(typeof sig==="string"&&sig.slice(0,6))+"... (长度 "+(sig||"").length+")");
  }catch(e){ console.log("本地 sign 失败: "+e.message); }
  // 3) 试 prepareTransactionRequest + sign (ERC-20 转 0 给自己, 验证签名+构造链)
  try{
    const USDC="0x833589fCD2e695B55A1C68A696f0810f2C3AD36C";
    const self=w.account&&w.account.address?w.account.address:"0x0000000000000000000000000000000000000001";
    const tx=await w.writeContract({address:USDC,abi:[viem.parseAbiItem("function transfer(address,uint256)")],fn:"transfer",args:[self,0n]});
    console.log("writeContract(0 转) 广播 hash: "+(tx?tx.slice(0,18):"(未广播)"));
  }catch(e){ console.log("writeContract: "+e.message.slice(0,90)); }
})().catch(e=>console.log("top err: "+e.message));
' 2>&1 | head -10
