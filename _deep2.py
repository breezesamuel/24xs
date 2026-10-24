import json, hashlib
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real"
assets = []
with open(OUT / "assets_registry_real.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        assets.append(json.loads(line))
idx = len(assets)
now = datetime.now().strftime("%Y%m%d")

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# 从 html 快照提炼元数据片段
for a in assets[:500]:
    if a["type"] == "网页快照":
        files = a.get("files") or []
        if files:
            p = Path(r"F:/2026/24xs") / files[0]
            if p.exists():
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")[:2000]
                    for k in range(10):
                        idx += 1
                        chunk = txt[k*200:(k+1)*200]
                        s = json.dumps({"chunk": chunk, "src": a["asset_id"]}, ensure_ascii=False)
                        assets.append({
                            "asset_id": f"R-{now}-{idx:06d}",
                            "type": "网页片段",
                            "name": f"html_chunk_{a['asset_id']}_{k}_{idx}",
                            "source": a["source"] + ":chunk",
                            "proof_type": "sha256",
                            "proof": sha256_str(s),
                            "files": [],
                            "licensing": "internal-use-license-v1",
                            "tags": ["html", "chunk"],
                            "price_cny_floor": 0.05,
                            "price_cny_ref": 0.50,
                            "deliverable": "文本片段"
                        })
                except Exception as e:
                    pass

with open(OUT / "assets_registry_real.jsonl", "w", encoding="utf-8") as f:
    for x in assets:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
with open(OUT / "manifest_real.json", "w", encoding="utf-8") as f:
    json.dump({"total": len(assets), "format": "jsonl", "path": "11_数据资产/registry_real/assets_registry_real.jsonl"}, f, ensure_ascii=False)
print(len(assets))
