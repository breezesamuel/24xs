#!/usr/bin/env python3
"""把 owner coinbase 钱包加进 alipay.js WALLETS 表 + 加币结算路由"""
import io, re
p = "api/alipay.js"
s = open(p, encoding="utf-8").read()

# 1) WALLETS 表: 在 solana_bounty 后加 owner_coinbase
anchor = "  solana_bounty:{chain:'Solana',asset:'SOL/usdc',address:'4moYJshT1bW71iESvwJHMynA5NFV534PJzFiKraydV6Z',role:'bounty 收款'}"
add_block = (
    "  solana_bounty:{chain:'Solana',asset:'SOL/usdc',address:'4moYJshT1bW71iESvwJHMynA5NFV534PJzFiKraydV6Z',role:'bounty 收款'},\n"
    "  // owner 指定 (2026-11-11): 币结算收款钱包 = Coinbase 自托管 (EVM, 40-hex 合法)\n"
    "  // 仅用于用户自己挣的币 (写作/返现/劳动/带宽渠道结算) -> 打款到此钱包\n"
    "  // 合规红线: 绝不接扫全网无主资金/airdrop 据为己有 -> 抽佣收进此钱包\n"
    "  owner_coinbase:{chain:'EVM',asset:'USDC/ETH/USDT',address:'0xe35b920Ba38bc83fb19D0b77871545C2F986093c',role:'owner coinbase 收款(币结算)',enabled:true}\n"
    " };"
)
if anchor in s:
    s = s.replace(anchor, add_block, 1)
    print("[wallet] owner_coinbase 加入 WALLETS 表")
else:
    print("[wallet] ANCHOR not found (可能已加过)")
    if "owner_coinbase" in s:
        print("[wallet] owner_coinbase 已存在")

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("[done] alipay.js 已写回")
