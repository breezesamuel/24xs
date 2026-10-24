from pathlib import Path
import json

# 1. Registry count
p = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl")
c = 0
with open(p,"rb") as f:
    for _ in f: c += 1
print("Registry:", c, "assets")

# 2. Asset type breakdown (sample)
types = {}
with open(p,"r",encoding="utf-8") as f:
    for i,line in enumerate(f):
        if i >= 100000: break
        a = json.loads(line)
        t = a.get("type","unknown")
        types[t] = types.get(t,0)+1
print("Sample type distribution (first 100k):")
for k,v in sorted(types.items(), key=lambda x:-x[1])[:15]:
    print("  ", k, ":", v)

# 3. Merkle
m = json.loads(Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/merkle_tree.json").read_text(encoding="utf-8"))
print("Merkle root:", m["root"][:16] + "...", "(levels:", m["levels"], ")")

# 4. Search index size
si = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_search.db")
print("Search index:", si.stat().st_size/1024/1024, "MB")

# 5. Proof files
for pf in [r"F:/2026/24xs/经济价值证明_24h.md", r"F:/2026/24xs/99_产出/经济价值证明_24h.md", r"F:/2026/24xs/11_数据资产/ECONOMIC_PROOF_FINAL.md"]:
    print("Proof:", Path(pf).exists(), pf)
