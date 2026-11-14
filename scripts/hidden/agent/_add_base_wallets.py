#!/usr/bin/env python3
"""把 owner 2026-11-12 给的 Base 体系钱包加进 WALLETS 表"""
p = "api/alipay.js"
s = open(p, encoding="utf-8").read()

anchor = "   owner_coinbase:{chain:'EVM',asset:'USDC/ETH/USDT',address:'0xe35b920Ba38bc83fb19D0b77871545C2F986093c',role:'owner coinbase 收款(币结算)',enabled:true}"
# 2 空格缩进 (文件实际用 2 空格)
anchor2 = "  owner_coinbase:{chain:'EVM',asset:'USDC/ETH/USDT',address:'0xe35b920Ba38bc83fb19D0b77871545C2F986093c',role:'owner coinbase 收款(币结算)',enabled:true}"

new_entries = (
    "\n"
    "  // owner 指定 (2026-11-12): Base 体系 收款/归集钱包 (USDC on Base, eip155:8453)\n"
    "  // USDC 合约 = 0x833589fCD2e695B55A1C68A696f0810f2C3AD36C (Base 官方)\n"
    "  // 注意: owner 曾给的 0x8335...bdA02913 是错的多位(33位), 不用\n"
    "  base_receive:{chain:'Base',asset:'USDC',address:'0x74a9f91763c28571af7a52987f425f62825cf5d8',role:'owner 收款钱包(Base USDC)',enabled:true},\n"
    "  agentpay_treasury:{chain:'Base',asset:'USDC',address:'0x367F1b3D8Ca90D1e087481a9A40d585Bf3451a03',role:'AgentPay treasury(Base USDC)',enabled:true},\n"
    "  base_usdc_contract:{chain:'Base',asset:'USDC',address:'0x833589fCD2e695B55A1C68A696f0810f2C3AD36C',role:'USDC 合约(Base)',is_contract:true}"
)

if anchor2 in s:
    s = s.replace(anchor2, anchor2 + new_entries, 1)
    print("[wallet] 加入 base_receive / agentpay_treasury / base_usdc_contract")
elif anchor in s:
    s = s.replace(anchor, anchor + new_entries, 1)
    print("[wallet] 加入 (3空格缩进)")
else:
    # 兜底: 在 ' };' 前插
    idx = s.find(" };\nfunction ladderPct")
    if idx < 0:
        print("[wallet] ANCHOR 未找到, 且兜定位失败; 无改动")
        raise SystemExit(1)
    # 在 owner_coinbase 行尾(不带分号)后插入 -> 找到该行并替换
    import re
    m = re.search(r"(  owner_coinbase:.*?enabled:true)\}", s)
    if m:
        s = s[:m.end(1)] + "," + new_entries + " }" + s[m.end()+1:]
        print("[wallet] 兜底正则插入成功")
    else:
        print("[wallet] 兜底正则未中; 无改动")
        raise SystemExit(1)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("[done] alipay.js 写回")
# 校验
chk = open(p, encoding="utf-8").read()
print("[check] base_receive in:", "base_receive" in chk, "| agentpay_treasury in:", "agentpay_treasury" in chk, "| contract in:", "base_usdc_contract" in chk)
