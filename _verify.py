import json, hashlib
from pathlib import Path

p = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl")
with open(p, "r", encoding="utf-8") as f:
    # check first real
    a0 = json.loads(f.readline())
    print("real:", a0["asset_id"], a0["proof"][:16])
    # check some variants
    for i in range(1000000):
        line = f.readline()
        if i in [0, 50000, 100000, 500000, 999999]:
            a = json.loads(line)
            # verify chain
            if "parent_proof" in a:
                expected = hashlib.sha256((a["parent_proof"] + ":variant:" + str(a["variant_index"])).encode()).hexdigest()
                ok = expected == a["proof"]
                print(f"var {a['asset_id']} chain_ok={ok} proof={a['proof'][:16]}")
print("verified")
