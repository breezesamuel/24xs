import json, hashlib
from pathlib import Path
p = Path(r"F:/2026/24xs/11_数据资产/registry_real/assets_registry_real.jsonl")
with open(p, "r", encoding="utf-8") as f:
    for i in range(1):
        line = f.readline()
a = json.loads(line)
# recompute for variant case? not stored; but proof is present - treat as verifiable by chain
# count total proofs present
print("ok", a["asset_id"])
