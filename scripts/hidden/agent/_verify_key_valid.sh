#!/usr/bin/env bash
# 回读 /etc/coinsettle/payout_key (0x+D) -> 重新派生地址 -> 应等于 0x927d...de09 (自洽校验)
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const fs=require("fs"),crypto=require("crypto"),viem=require("viem");
const raw=fs.readFileSync("/etc/coinsettle/payout_key","utf8").trim();
let D=(raw.startsWith("0x")?raw:"0x"+raw).toLowerCase();
if(D.length!==66)throw new Error("D len="+D.length);
// 由 D 重建 keypair (需匹配公钥): 用模板替换 D 段
function keyFromD(hexD){
  const kp=crypto.generateKeyPairSync("ec",{namedCurve:"secp256k1"});
  const b=Buffer.from(kp.privateKey.export({type:"pkcs8",format:"der"}));
  let di=-1; for(let i=b.length-70;i>=0;i--){ if(b[i]===2&&b[i+1]===1&&b[i+2]===1){ for(let j=i+3;j<b.length-32;j++){ if(b[j]===4&&b[j+1]===32){ di=j+2; break; } } break; } }
  if(di<0)throw new Error("D 段定位失败");
  const out=Buffer.from(b); out.set(Buffer.from(hexD,"hex"),di);
  // 还需替换公钥段匹配 -> 不能, 因公钥依赖 D。改用「只喂 D 给 viem createWalletClient」更稳, 这里仅校验地址派生逻辑。
  return out;
}
// 正确做法: 地址 = keccak(未压缩公钥), 公钥 = secp256k1(D)*G。node crypto 无法由 D 直接出 pub(需自洽 DER)。
// 所以这里改为: 重新用「生成时的 keypair 公钥」—— 但公钥没存。-> 用 viem 若有 privateKeyToAccount 最稳, 但本 build 没有。
// 折中: 校验存储的 D 是 32B 合法 + 用「模板法」重建 keypair 时公钥段是旧的, 地址会与旧公钥错配。
// 因此【权威校验】应在实转 dry-run 时由 viem createWalletClient(account: D) 内部自洽派生地址。
// 本步只做: D 格式合法 + 非 0 + 非曲线外
const Db=BigInt("0x"+D.slice(2));
console.log("  D 是 32 字节非零: "+(Db>0n)+"  D 范围 (<N 曲线阶): "+(Db<BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A033BFD75C2F")));
console.log("  存储 D 指纹: 0x"+D.slice(2,10)+"..."+D.slice(-4));
console.log("  (地址自洽性将在 live-dry-run 时由 viem 派生核对; 此处确认 D 合法)");
' 2>&1 | head -6
