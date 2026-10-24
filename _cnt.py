import json
from pathlib import Path
p = Path(r"F:/2026/24xs/11_数据资产/registry/assets_registry.jsonl")
cnt = {}
with open(p, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 100000:
            break
        a = json.loads(line)
        t = a["type"]
        cnt[t] = cnt.get(t, 0) + 1
print(json.dumps(cnt, ensure_ascii=False))
