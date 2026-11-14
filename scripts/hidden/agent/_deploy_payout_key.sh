#!/usr/bin/env bash
# 把本地生成的付款私钥落到 CN /etc/coinsettle/payout_key (600), 并用 viem 派生 EVM 地址回显
KEY=/etc/coinsettle/payout_key
echo "=== 落地密钥文件 (CN) ==="
# 通过 stdin 管道写入 (不经过 CN 命令行明文; 本地 scp 已加密传输)
chmod 600 "$KEY" 2>/dev/null || true
echo "  文件大小: $(stat -c%s "$KEY" 2>/dev/null || echo 'not yet') bytes"
echo "=== viem 派生付款钱包地址 + 在 Base 上的余额 (只读, 不转) ==="
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const fs=require("fs");
const viem=require("viem");
const raw=fs.readFileSync("/etc/coinsettle/payout_key","utf8").trim();
const pk=raw.startsWith("0x")?raw:"0x"+raw.replace(/[^0-9a-fA-F]/g,"");
// 兼容: 若文件是 PEM/PKCS8, 取 D; 这里是 0x+D (32B secp256k1)
let acct;
try{ acct=viem.privateKeyToAccount(pk); }
catch(e){
  // 若是 PEM, 尝试解析
  throw new Error("私钥格式不符 (需 0x+32字节 secp256k1 D), 错:"+e.message);
}
console.log("  付款钱包地址 (Base/所有 EVM 通用): "+acct.address);
// 只读查 Base native 余额 + USDC 余额
const chain=viem.createChain?viem.createChain({id:8453,ca:"https://mainnet.base.org",rpcs:[{http:["https://mainnet.base.org"]}],nativeCurrency:{name:"ETH",symbol:"ETH",decimals:18},contracts:{}}):{id:8453};
const pub=viem.createPublicClient({chain,transport:viem.http("https://mainnet.base.org")});
(async()=>{
  const bal=await pub.getBalance({address:acct.address}).catch(()=>null);
  console.log("  Base ETH (gas) 余额: "+(bal!=null?(Number(bal)/1e18).toFixed(6)+" ETH":"(查询失败)"));
  const USDC="0x833589fCD2e695B55A1C68A696f0810f2C3AD36C";
  const erc=viem.parseAbiItem("function balanceOf(address a) view returns (uint256)");
  const usdc=await pub.readContract({address:USDC,abi:[erc],fn:"balanceOf",args:[acct.address]}).catch(()=>null);
  console.log("  Base USDC 余额: "+(usdc!=null?(Number(usdc)/1e6).toFixed(4)+" USDC":"(查询失败/无)"));
})().catch(e=>console.log("  RPC 查询错: "+e.message));
' 2>&1 | head -8
