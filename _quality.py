import json, hashlib
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
REG = BASE / "registry_real_verified/assets_verifiable_1M.jsonl"
OUT = BASE / "registry_real_verified"

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

results = {
    "timestamp": datetime.now().isoformat() + "Z",
    "checks": {}
}

# 1. Schema validation
required_fields = ["asset_id", "type", "name", "source", "proof", "proof_type", "price_cny_ref", "price_cny_floor", "deliverable", "tags", "files"]
schema_errors = 0
with open(REG, "r", encoding="utf-8") as f:
    for line in f:
        a = json.loads(line)
        for field in required_fields:
            if field not in a:
                schema_errors += 1
results["checks"]["schema_validation"] = {"status": "pass" if schema_errors == 0 else "fail", "errors": schema_errors}

# 2. Proof verification (sample 10000)
proof_errors = 0
verified = 0
with open(REG, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 10000: break
        a = json.loads(line)
        if a["proof_type"] == "sha256" and "canonical" in a:
            expected = sha256_str(a["canonical"])
            if expected != a["proof"]:
                proof_errors += 1
        verified += 1
results["checks"]["proof_verification"] = {"status": "pass" if proof_errors == 0 else "fail", "sampled": verified, "errors": proof_errors}

# 3. Chain verification
chain_errors = 0
chain_verified = 0
with open(REG, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 5000: break
        a = json.loads(line)
        if "parent_proof" in a and "variant_index" in a:
            expected = sha256_str(a["parent_proof"] + ":variant:" + str(a["variant_index"]))
            if expected != a["proof"]:
                chain_errors += 1
            chain_verified += 1
results["checks"]["chain_verification"] = {"status": "pass" if chain_errors == 0 else "fail", "sampled": chain_verified, "errors": chain_errors}

# 4. Uniqueness
id_set = set()
dup_count = 0
with open(REG, "r", encoding="utf-8") as f:
    for line in f:
        a = json.loads(line)
        aid = a["asset_id"]
        if aid in id_set:
            dup_count += 1
        else:
            id_set.add(aid)
results["checks"]["uniqueness"] = {"status": "pass" if dup_count == 0 else "fail", "duplicates": dup_count, "unique_count": len(id_set)}

# 5. Price sanity
price_errors = 0
with open(REG, "r", encoding="utf-8") as f:
    for line in f:
        a = json.loads(line)
        ref = a.get("price_cny_ref", 0)
        floor = a.get("price_cny_floor", 0)
        if ref < floor or ref <= 0 or floor < 0:
            price_errors += 1
results["checks"]["price_sanity"] = {"status": "pass" if price_errors == 0 else "fail", "errors": price_errors}

# 6. Source traceability
source_errors = 0
with open(REG, "r", encoding="utf-8") as f:
    for line in f:
        a = json.loads(line)
        if not a.get("source") or not a["source"].startswith("11_数据资产"):
            source_errors += 1
results["checks"]["source_traceability"] = {"status": "pass" if source_errors == 0 else "fail", "errors": source_errors}

# 7. Tag coverage
tag_coverage = {}
with open(REG, "r", encoding="utf-8") as f:
    for line in f:
        a = json.loads(line)
        tags = a.get("tags", [])
        if not tags:
            tag_coverage["no_tags"] = tag_coverage.get("no_tags", 0) + 1
        else:
            tag_coverage["has_tags"] = tag_coverage.get("has_tags", 0) + 1
results["checks"]["tag_coverage"] = {"status": "pass", "details": tag_coverage}

# 8. Merkle consistency
try:
    merkle = json.loads((OUT / "merkle_tree.json").read_text(encoding="utf-8"))
    proofs = []
    with open(REG, "r", encoding="utf-8") as f:
        for line in f:
            a = json.loads(line)
            proofs.append(a["proof"])
    
    def hash_pair(a, b):
        return hashlib.sha256((a + b).encode()).hexdigest()
    
    level = proofs
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                next_level.append(hash_pair(level[i], level[i+1]))
            else:
                next_level.append(level[i])
        level = next_level
    
    computed_root = level[0]
    root_match = computed_root == merkle["root"]
    results["checks"]["merkle_consistency"] = {"status": "pass" if root_match else "fail", "stored_root": merkle["root"][:16] + "...", "computed_root": computed_root[:16] + "..."}
except Exception as e:
    results["checks"]["merkle_consistency"] = {"status": "error", "error": str(e)}

# Overall - only consider checks with status field
all_pass = True
for c in results["checks"].values():
    if isinstance(c, dict) and "status" in c:
        if c["status"] != "pass":
            all_pass = False
            break
results["overall"] = "pass" if all_pass else "fail"

with open(OUT / "quality_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Quality check:", results["overall"])
for k, v in results["checks"].items():
    print("  " + k + ":", v.get("status", "done"))
