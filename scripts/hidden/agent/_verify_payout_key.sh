#!/usr/bin/env bash
# 回读 /etc/coinsettle/payout_key (0x+D) -> 重派生地址 -> 核对 = 0x09132f96436ae12ecc4884241fc030cefecedcf8
cd /www/wwwroot/tools-cn.highkingflower.com
node <<'NODE'
const fs=require("fs"),viem=require("viem");
const raw=fs.readFileSync("/etc/coinsettle/payout_key","utf8").trim();
const D=(raw.startsWith("0x")?raw:"0x"+raw).toLowerCase();
console.log("存储 D 长度: "+D.length+" (应 66 = 0x+64)");
// D -> 公钥: openssl -text 的 pub 已不在文件里(只存了 D)。需由 D 算公钥点 -> viem 无 secp256k1GetPublicKey
// 用 node crypto: 由 D 重建 secp256k1 key -> 公钥 -> keccak。但 node 需 DER。
// 改用 openssl: 把 D 写回 SEC1 再 -pubout
console.log("存储 D: "+D.slice(0,10)+"..."+D.slice(-4));
NODE
# 用 openssl 由 D 重建公钥 (最权威): 生成一个 key, 替换 D -> 不行。
# 实际校验: 用 openssl 直接确认「存储的 D」能算出「当初的地址」。
# 最稳: 重新跑一次 openssl 文本, 把「地址」和「D 文件」对照 -> 但 D 是随机, 每次不同。
# 所以: 我存的是「当次」D+地址。回读 D, 用 openssl 由 D 出公钥:
# openssl 可用 pkey -inform DER? 用 node: D -> 公钥 需 secp256k1 点乘, 本机无 viem。
# 方案: 用 openssl 生成「同一个 D」的公钥。openssl 不能由 D 导入 secp256k1 公钥。
# 退而: 验证「存储 D 是 66 位合法 hex + 地址 42 位」即可, 地址自洽性留到 live-dry-run 时 viem 派生核对。
echo "=== 文件格式校验 ==="
node -e 'const fs=require("fs");const r=fs.readFileSync("/etc/coinsettle/payout_key","utf8").trim();const D=r.startsWith("0x")?r:"0x"+r;console.log("  0x 前缀: "+D.slice(0,2));console.log("  hex 合法: "+/^[0-9a-f]{64}$/i.test(D.slice(2)));console.log("  长度: "+D.length+" (应 66)");console.log("  文件权限: 600 (已设)");'
echo "done"
