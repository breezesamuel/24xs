#!/usr/bin/env bash
# 由 D 派生 EVM 地址 (node crypto 建 secp256k1 key -> uncompressed pub -> viem keccak256)
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const fs=require("fs"), crypto=require("crypto"), viem=require("viem");
const raw=fs.readFileSync("/etc/coinsettle/payout_key","utf8").trim();
let D=(raw.startsWith("0x")?raw:"0x"+raw.replace(/[^0-9a-fA-F]/g,"")).toLowerCase();
if(D.length!==66){ throw new Error("D 长度="+D.length+" (需 0x+32 字节=66)"); }
// 生成一个随机 secp256k1 PKCS8 DER 做模板, 替换其中的 D (倒数 32 字节的 EC 参数固定)
const tmpl=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"}).privateKey.export({type:"pkcs8",format:"der"});
const pk8=Buffer.from(tmpl);
// PKCS8 EC: ... [04 20 <D32>] ...  找 0x04 0x20 标记, 替换其后 32 字节
let idx=-1;
for(let i=pk8.length-40;i>=0;i++){ if(pk8[i]===0x04 && pk8[i+1]===0x20){ idx=i; break; } }
if(idx<0) throw new Error("模板没找到 04 20 标记");
pk8.copy ? null : null;
const out=Buffer.from(pk8);
out.set(D.slice(2).match(/.{1,2}/g).map(b=>parseInt(b,16)), idx+2);
const keyObj=crypto.createPrivateKey({key:out, format:"der", type:"pkcs8"});
const pubUn=crypto.createPublicKey(keyObj).export({type:"spki",format:"der"});
const tail=pubUn.slice(pubUn.length-65);
if(tail[0]!==0x04) throw new Error("pub 非未压缩");
const pubBytes=tail.slice(1);
const addr="0x"+Buffer.from(viem.keccak256(pubBytes)).slice(12).toString("hex");
console.log("  付款钱包 EVM 地址: "+addr);
(async()=>{
  const pub=viem.createPublicClient({transport:viem.http("https://mainnet.base.org")});
  const bal=await pub.getBalance({address:addr}).catch(()=>null);
  const USDC="0x833589fCD2e695B55A1C68A696f0810f2C3AD36C";
  const erc=viem.parseAbiItem("function balanceOf(address a) view returns (uint256)");
  const u=await pub.readContract({address:USDC,abi:[erc],fn:"balanceOf",args:[addr]}).catch(()=>null);
  console.log("  Base ETH(gas): "+(bal!=null?(Number(bal)/1e18).toFixed(6)+" ETH":"?")+"  USDC: "+(u!=null?(Number(u)/1e6).toFixed(4)+" USDC":"0/无"));
  console.log("  -> 新钱包应为 0, 需先充 Base USDC >=100 + 一点 ETH gas 才能实转");
})().catch(e=>console.log("  余额查询: "+e.message));
' 2>&1 | head -8
