#!/usr/bin/env bash
# 核对 CN 系统里这个地址是不是已知钱包 (env + 配置 + 付款密钥派生)
ADDR="0x6350761dfb1d20c30ba7ae9cb16560fbe67ddc38"
echo "=== 1. CN env / 配置里所有 0x 地址 (找这个) ==="
grep -rhoE "0x[0-9a-fA-F]{40}" /etc/bingdashan-cn.env /opt/bingdashan 2>/dev/null | grep -viE "node_modules|\.git" | sort -u > /tmp/_alladdr.txt
echo "  系统里出现的 0x 地址总数: $(wc -l < /tmp/_alladdr.txt)"
echo "  其中是否含目标地址:"
grep -i "$ADDR" /tmp/_alladdr.txt && echo "    ✅ 命中！这是系统已知地址" || echo "    ❌ 系统配置里没有这个地址"
echo ""
echo "=== 2. 列出系统里所有 0x 地址 (看它和哪些项目/钱包在一起) ==="
grep -rilE "0x[0-9a-fA-F]{40}" /etc/bingdashan-cn.env /opt/bingdashan/*.env /opt/bingdashan/.env /opt/bingdashan/infra 2>/dev/null | head -10
echo "  --- 具体键值 (env 里 0x 开头的, 只看键名) ---"
grep -oE "^[A-Z_]*0x[0-9a-fA-F]{40}" /etc/bingdashan-cn.env 2>/dev/null | sed -E 's/(0x[0-9a-fA-F]{6}).*/\1.../' | head -20
echo ""
echo "=== 3. 付款密钥派生的地址列表 (openssl 生成的, 逐个派生比对) ==="
# CN 有哪些 secp256k1 密钥文件
ls -1 /etc/coinsettle/*.pem /etc/coinsettle/*.key /etc/bingdashan-cn/*.pem /etc/bingdashan-cn/*.key 2>/dev/null
# 对每个密钥文件派生地址, 看哪个等于目标
node -e '
const fs=require("fs"),path=require("path"),crypto=require("crypto");
function derive(privKeyHex){
  try{
    // secp256k1: pubkey = G*d, address = keccak(pubkey 压缩点 x 后半) 取最后20字节
    const {createECDH}=crypto;
    // 简化: 用 node crypto 派生公钥 x 坐标
    const buf=Buffer.from(privKeyHex.replace(/^0x/,""),"hex");
    // 用 secp256k1 点乘 (node 无内置, 用 openssl 或 noble 不可用 -> 这里用 openssl 命令)
    return null;
  }catch(e){return null;}
}
// 用 openssl 派生每个密钥文件的地址
const dirs=[ "/etc/coinsettle","/etc/bingdashan-cn","/opt/bingdashan" ];
const files=[];
dirs.forEach(d=>{ try{ fs.readdirSync(d).filter(f=>/key|pem|secp|priv/i.test(f)).forEach(f=>files.push(path.join(d,f))); }catch(e){} });
files.forEach(f=>{
  try{
    const p=require("child_process").execSync("openssl ec -in "+JSON.stringify(f)+" -pubout 2>/dev/null | tail -n +2 | head -n -1 | base64 -d | xxd -p", {encoding:"utf8"}).trim();
    if(p){
      // keccak 需 noble, 这里只做地址末尾匹配: 公钥最后20字节
      const pubBytes=Buffer.from(p,"hex");
      // 非压缩点 65 字节: 04 + x(32) + y(32). 地址 = keccak(x||y).slice(12). 无 keccak 时, 用公钥 y 的后20字节做近似提示
      console.log("  密钥 "+f+" -> pubkey(最后8字节): "+pubBytes.toString("hex").slice(-16));
    }
  }catch(e){ console.log("  密钥 "+f+" -> (派生失败: "+e.message.slice(0,40)+")"); }
});
' 2>&1
echo done
