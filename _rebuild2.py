# expand rebuild to all real data
import json, hashlib, sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

assets = []
now = datetime.now().strftime("%Y%m%d")
idx = 0

# profiles
try:
    with open(BASE / "assets" / "企业档案.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    for i, obj in enumerate(profs):
        idx += 1
        core = {"name": obj.get("name"), "source": "11_数据资产/assets/企业档案.json", "data": obj}
        proof = sha256_str(canonical(core))
        assets.append({"asset_id": f"V-{now}-{idx:06d}", "type": "企业档案", "name": core["name"] or f"e{i}", "source": core["source"], "proof": proof, "canonical": canonical(core), "proof_type": "sha256", "price_cny_ref": 20.00, "price_cny_floor": 5.00, "deliverable": "JSON档案", "tags": ["entity"], "files": []})
except: pass

# html
for p in (BASE / "assets").glob("*.html"):
    try:
        idx += 1
        txt = p.read_text(encoding="utf-8", errors="ignore")
        core = {"name": p.stem, "source": str(p).replace("F:\\2026\\24xs\\",""), "data": txt[:50000]}
        proof = sha256_str(canonical(core))
        assets.append({"asset_id": f"V-{now}-{idx:06d}", "type": "网页快照", "name": p.stem, "source": core["source"], "proof": proof, "canonical": canonical(core), "proof_type": "sha256", "price_cny_ref": 10.00, "price_cny_floor": 2.00, "deliverable": "HTML快照", "tags": ["html"], "files": [core["source"]]})
    except: pass

with open(OUT / "assets_verifiable.jsonl", "w", encoding="utf-8") as f:
    for a in assets:
        # don't write huge canonical to save space? store truncated or just keep proof+core small; but keep canonical for verification
        rec = dict(a)
        # keep canonical (may be large but needed for verification)
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(len(assets))
