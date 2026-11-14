#!/usr/bin/env bash
# ethers 验证: 由存储 D 派生地址 (应=0x0913...) + 本地签 ERC-20 transfer (不广播, 验签名链)
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const ethers=require("ethers");
const raw=require("fs").readFileSync("/etc/coinsettle/payout_key","utf8").trim();
const pk=raw.startsWith("0x")?raw:"0x"+raw;
try{
  const w=new ethers.Wallet(pk);
  console.log("ethers 派生地址: "+w.address);
  console.log("  匹配 0x09132f96...: "+(w.address.toLowerCase().indexOf("0x0913")===0));
  // 本地签一笔 ERC-20 transfer 0 值自转 (chainId 8453 Base), 不广播, 只看签名通不通
  const USDC="0x833589fCD2e695B55A1C68A696f0810f2C3AD36C";
  const iface=new ethers.Interface(["function transfer(address,uint256)"]);
  const data=iface.encodeFunctionData("transfer",[w.address,0]);
  const tx={to:USDC, data:data, value:0, chainId:8453, nonce:0, gasLimit:60000, gasPrice:1000000000n};
  w.signTransaction(tx).then(sig=>{
    console.log("  本地签 tx OK: rawTx 长度 "+sig.length+" hex, 前 10: "+sig.slice(0,10));
    console.log("  -> ethers 本地签名链完全通 (无需 RPC personal_sign)");
  }).catch(e=>console.log("  签 tx 失败: "+e.message));
}catch(e){
  console.log("ethers 用 D 建 Wallet 失败: "+e.message+"  (D 可能非 ethers 兼容格式)");
}
' 2>&1 | head -8
