from pathlib import Path
import json

checks = {
    "Registry (1M+)": Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl"),
    "Merkle Tree": Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/merkle_tree.json"),
    "Search Index": Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_search.db"),
    "Ingest State": Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/ingest_state.json"),
    "Proof Doc": Path(r"F:/2026/24xs/经济价值证明_24h.md"),
    "Store": Path(r"F:/2026/24xs/10_官网/store.html"),
    "API assets": Path(r"F:/2026/24xs/10_官网/functions/api/assets.js"),
    "API search": Path(r"F:/2026/24xs/10_官网/functions/api/search.js"),
    "API verify": Path(r"F:/2026/24xs/10_官网/functions/api/verify.js"),
    "API purchase": Path(r"F:/2026/24xs/10_官网/functions/api/purchase.js"),
    "API deliver": Path(r"F:/2026/24xs/10_官网/functions/api/deliver.js"),
    "API webhook": Path(r"F:/2026/24xs/10_官网/functions/api/webhook_moltspay.js"),
}

for name, p in checks.items():
    exists = p.exists()
    size = p.stat().st_size if exists else 0
    if exists:
        print("OK", name, f"({size/1024/1024:.1f} MB)")
    else:
        print("MISSING", name)

# Count
p = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl")
c = 0
with open(p,"rb") as f:
    for _ in f: c += 1
print("\nRegistry total:", c)

# Merkle
m = json.loads(Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/merkle_tree.json").read_text(encoding="utf-8"))
print("Merkle root:", m["root"][:16] + "...")
print("Scheduled tasks: 24xs_Asset_Ingestion (03:00), 24xs_Asset_Rebuild (03:30)")
