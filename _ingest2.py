import json, hashlib, sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
REG = BASE / "registry_real_verified/assets_verifiable_1M.jsonl"
STATE = BASE / "registry_real_verified/ingest_state.json"

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"ccgp_notices_max_rowid": 0, "factory_probes_max_rowid": 0, "last_run": None}

def save_state(s):
    s["last_run"] = datetime.utcnow().isoformat() + "Z"
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

def append_asset(asset):
    with open(REG, "a", encoding="utf-8") as f:
        f.write(json.dumps(asset, ensure_ascii=False) + "\n")

state = load_state()
now = datetime.now().strftime("%Y%m%d")
added = 0

# Factory new probes
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    last = state.get("factory_probes_max_rowid", 0)
    cur.execute("SELECT rowid, * FROM geo_probes WHERE rowid > ?", (last,))
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(cols, r))
        core = {"source": "99_产出/_data/factory.sqlite3:geo_probes", "data": row}
        proof = sha256_str(canonical(core))
        rid = row.get("rowid", 0)
        append_asset({
            "asset_id": f"V-{now}-{rid:06d}",
            "type": "GEO探测",
            "name": f"GEO探测_{rid}",
            "source": core["source"],
            "proof": proof,
            "proof_type": "sha256",
            "price_cny_ref": 20.00,
            "price_cny_floor": 5.00,
            "deliverable": "结构化记录",
            "tags": ["geo", "verifiable", "auto_ingested"],
            "files": []
        })
        added += 1
        state["factory_probes_max_rowid"] = max(state.get("factory_probes_max_rowid", 0), rid)
    conn.close()
except Exception as e:
    print("factory err", e)

save_state(state)
print(f"Added {added} new real assets")
