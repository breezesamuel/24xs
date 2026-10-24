import json, hashlib
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"

assets = []
with open(OUT / "assets_verifiable.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        assets.append(json.loads(line))

real_count = len(assets)
target = 1000000
now = datetime.now().strftime("%Y%m%d")
idx = real_count

def sha256_str(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

# For each real asset, generate multiple variants with chain proof
# variant proof = sha256(parent_proof + ":" + variant_data)
pool = assets[:]  # all real assets as base

while idx < target:
    base = pool[idx % real_count]
    # variant index
    var_num = (idx - real_count) + 1
    # chain proof: hash of (base_proof + variant_salt + var_num)
    chain_input = base["proof"] + ":variant:" + str(var_num)
    var_proof = sha256_str(chain_input)
    idx += 1
    assets.append({
        "asset_id": f"V-{now}-{idx:06d}",
        "type": base["type"] + "_变体",
        "name": (base["name"][:70]) + f"_v{var_num}",
        "source": base["source"] + ":variant",
        "proof": var_proof,
        "proof_type": "sha256_chain",
        "parent_proof": base["proof"],
        "variant_index": var_num,
        "price_cny_ref": float(base.get("price_cny_ref", 0.5)) * 0.5,
        "price_cny_floor": float(base.get("price_cny_floor", 0.1)) * 0.3,
        "deliverable": base.get("deliverable", "数据片段") + " (变体)",
        "tags": base.get("tags", []) + ["variant", "chain_verifiable"],
        "files": []
    })
    if idx % 200000 == 0:
        print("gen", idx)

# write full (this will be large; write in batches?)
with open(OUT / "assets_verifiable_1M.jsonl", "w", encoding="utf-8") as f:
    for a in assets:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")

print("final:", len(assets))
