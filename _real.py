from pathlib import Path
p = Path(r"F:/2026/24xs/11_数据资产/registry/assets_registry.jsonl")
real = 0
gen = 0
with open(p, "r", encoding="utf-8") as f:
    for line in f:
        if '"asset_id"' in line:
            try:
                s = line.split('"asset_id"')[1]
                aid = s.split('"')[1]
            except:
                aid = ""
        else:
            aid = ""
        if aid.startswith("X-"):
            gen += 1
        else:
            real += 1
print(real, gen, real+gen)
