#!/usr/bin/env python3
"""本地生成 secp256k1 新付款钱包: 写 0x+D 到本地文件 (不打印私钥明文)。地址由 CN viem 派生并回显。"""
import os, subprocess, base64

# 用 node crypto 生成 secp256k1, 只输出 D (私钥标量 32B hex)
js = r"""
const c=require('crypto');
const {privateKey}=c.generateKeyPairSync('ec',{namedCurve:'secp256k1'});
const der=privateKey.export({type:'pkcs8',format:'der'});
const d=der.slice(der.length-32).toString('hex');
process.stdout.write('D='+d);
"""
out = subprocess.run(["node","-e",js], capture_output=True, text=True)
D = out.stdout.split("D=")[1].strip().lower()
assert len(D)==64, f"D len={len(D)}"

keyfile = "F:/2026/24xs/scripts/hidden/agent/_payout_key_new"
with open(keyfile,"w",encoding="utf-8") as f:
    f.write("0x"+D)
os.chmod(keyfile, 0o600)
print("[gen] secp256k1 新付款钱包已生成")
print("[gen] 私钥文件(本地):", keyfile, "  D指纹:", D[:8]+"..."+D[-4:])
print("[next] scp 到 CN /etc/coinsettle/payout_key, 用 viem 派生地址")
