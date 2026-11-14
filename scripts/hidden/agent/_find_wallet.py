#!/usr/bin/env python3
"""搜 opencode.db 里 用户是否给过 虚拟币钱包地址 (EVM 0x / Solana base58 / 钱包指令)"""
import sqlite3, re, json, os

DB = os.path.expandvars(r"%USERPROFILE%\.local\share\opencode\opencode.db")
c = sqlite3.connect(DB)
cur = c.cursor()

evm = re.compile(r'0x[0-9a-fA-F]{40}')
sol = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
kw = re.compile(r'钱包|收款地址|payout|结算地址|到账|USDC 给|USDC 到|wallet address')

# 已知 WALLETS 表里的地址 (排除掉, 那些是代码里的, 不是 owner 给的)
KNOWN = set([
  '0xa75Cc8545B169F0BeF2f29c9CCF86bc686D039E8',
  '0x52513A733D4b52282F2b4f5A91D965D38b64f3BB',
  '0x2C5dF5f91642B1214c28E51C67aEf1c61CbE1824',
  '0x047b2A7fc72862a0e3E772eb53b19d35929BEd46',
  '0xDe37cDc93fC425e14EBdB827086E2144b31E855a',
  '0x5D36F4c480F900F0E7Ad0DC4fA0402554b972bF8',
  '4moYJshT1bW71iESvwJHMynA5NFV534PJzFiKraydV6Z',
])

# 先列 role 字段
print("=== message 表结构 ===")
for r in cur.execute("PRAGMA table_info(message)"):
    print(" ", r)

# data 是 JSON; 找 role (只看 user 消息, 省时间)
evm_hits, sol_hits, kw_hits = [], [], []
user_count = 0
for sid, data in cur.execute("SELECT session_id, data FROM message"):
    try:
        d = json.loads(data)
    except Exception:
        continue
    if not isinstance(d, dict):
        continue
    if d.get("role") != "user":
        continue
    user_count += 1
    txt = d.get("text","") or ""
    for p in (d.get("parts") or []):
        if isinstance(p, dict) and p.get("type") == "text":
            txt += " " + str(p.get("text",""))
    if not txt:
        continue
    for m in evm.finditer(txt):
        a = m.group(0)
        if a not in KNOWN:
            evm_hits.append((sid[:8], role, a))
    for m in sol.finditer(txt):
        a = m.group(0)
        if a not in KNOWN and not re.match(r'^[0-9a-f]+$', a):  # 排除纯hex
            sol_hits.append((sid[:8], role, a))
    for m in kw.finditer(txt):
        kw_hits.append((sid[:8], role, txt[max(0,m.start()-30):m.end()+30].replace("\n"," ")))

print("scanned user msgs:", user_count)
print()
print("=== 未知 EVM 0x 地址 (非 WALLETS 表) ===", len(evm_hits))
seen=set()
for h in evm_hits:
    k=h[2]
    if k in seen: continue
    seen.add(k)
    print("  ", h)
print()
print("=== 未知 Solana base58 候选 (排除hex) ===", len(sol_hits))
seen=set()
for h in sol_hits[:30]:
    k=h[2]
    if k in seen: continue
    seen.add(k)
    print("  ", h)
print()
print("=== 含 钱包/收款/payout 关键词的片段 ===", len(kw_hits))
seen=set()
for h in kw_hits[:40]:
    k=(h[0],h[2][:40])
    if k in seen: continue
    seen.add(k)
    print("  ", h)
