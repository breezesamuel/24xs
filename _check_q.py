import json
from pathlib import Path
OUT = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified")
r = json.loads((OUT / "quality_report.json").read_text(encoding="utf-8"))
print("Overall:", r["overall"])
for k, v in r["checks"].items():
    print("  " + k + ":", v.get("status", v))
