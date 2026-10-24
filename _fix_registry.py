import json, hashlib
from pathlib import Path
from datetime import datetime

REG = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl")
OUT = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M_fixed.jsonl")

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

seen = set()
fixed = 0
total = 0

with open(REG, "r", encoding="utf-8") as fin, open(OUT, "w", encoding="utf-8") as fout:
    for line in fin:
        total += 1
        a = json.loads(line)
        
        # Fix source path
        src = a.get("source", "")
        if src.startswith("99_产出/"):
            a["source"] = "11_数据资产/" + src.replace("99_产出/", "")
        
        # Fix duplicate IDs - if V-20261006-000000 appears, make unique
        aid = a["asset_id"]
        if aid in seen:
            # regenerate with timestamp + counter
            base = aid.replace("V-", "")
            new_aid = f"V-{datetime.now().strftime('%Y%m%d')}-{total:06d}"
            a["asset_id"] = new_aid
            fixed += 1
        seen.add(a["asset_id"])
        
        fout.write(json.dumps(a, ensure_ascii=False) + "\n")

print(f"Total: {total}, Fixed duplicates: {fixed}, Unique IDs: {len(seen)}")

# Replace original
import shutil
shutil.move(OUT, REG)
print("Replaced original")
