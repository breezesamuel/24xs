# Build Merkle tree over all 1M asset proofs
import hashlib, json
from pathlib import Path

p = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl")
OUT = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified")
OUT.mkdir(exist_ok=True)

# Read all proofs in order
proofs = []
with open(p, "r", encoding="utf-8") as f:
    for line in f:
        a = json.loads(line)
        proofs.append(a["proof"])

print("Read", len(proofs))

# Build tree bottom-up
def hash_pair(a, b):
    return hashlib.sha256((a + b).encode()).hexdigest()

level = proofs
trees = [level]
while len(level) > 1:
    next_level = []
    for i in range(0, len(level), 2):
        if i + 1 < len(level):
            next_level.append(hash_pair(level[i], level[i+1]))
        else:
            next_level.append(level[i])  # odd: promote
    trees.append(next_level)
    level = next_level

root = level[0]
print("Merkle root:", root)

# Save tree levels (only root + ability to generate proofs on demand)
# Instead of storing full tree, save root and provide function to compute proof path
# For storage efficiency, save root and let verifier recompute from registry
tree_data = {
    "root": root,
    "total": len(proofs),
    "levels": len(trees),
    "algorithm": "sha256_pair",
    "note": "To verify asset at index i, recompute path from leaf to root using registry order"
}
with open(OUT / "merkle_tree.json", "w", encoding="utf-8") as f:
    json.dump(tree_data, f, ensure_ascii=False, indent=2)

print("Saved merkle_tree.json")
