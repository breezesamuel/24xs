from pathlib import Path
import json
p = Path(r"F:/2026/24xs/11_数据资产/registry/assets_registry.json")
if p.exists():
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
    print(len(d))
else:
    print(0)
