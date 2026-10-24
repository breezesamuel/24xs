import json
from pathlib import Path

REG = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl")
OUT = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M_fixed2.jsonl")

fixed = 0
with open(REG, "r", encoding="utf-8") as fin, open(OUT, "w", encoding="utf-8") as fout:
    for line in fin:
        a = json.loads(line)
        src = a.get("source", "")
        if src == "crossref:ccgp_buyer_to_profile":
            a["source"] = "11_数据资产/crossref:ccgp_buyer_to_profile"
            fixed += 1
        fout.write(json.dumps(a, ensure_ascii=False) + "\n")

print(f"Fixed {fixed} crossref sources")
import shutil
shutil.move(OUT, REG)
print("Replaced")
