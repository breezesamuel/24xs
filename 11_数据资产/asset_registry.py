import json, hashlib, os, csv
from pathlib import Path
from datetime import datetime

BASE = Path(r'F:\2026\24xs\11_数据资产')
ASSETS_DIR = BASE / 'assets'
OUT = BASE / 'registry'
OUT.mkdir(exist_ok=True)

def sha256_file(p):
    h = hashlib.sha256()
    try:
        with open(p,'rb') as f:
            for chunk in iter(lambda:f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ''

def sha256_str(s):
    return hashlib.sha256(s.encode('utf-8', errors='ignore')).hexdigest()

# 企业档案
assets = []
try:
    with open(ASSETS_DIR / '企业档案.json','r',encoding='utf-8') as f:
        profs = json.load(f)
    for i, obj in enumerate(profs):
        name = obj.get('name') or obj.get('企业名称') or f'entity_{i}'
        aid = f'A-{datetime.now().strftime("%Y%m%d")}-{i+1:06d}'
        assets.append({
            'asset_id': aid,
            'type': '企业档案',
            'name': name,
            'source': '11_数据资产/assets/企业档案.json',
            'proof_type': 'sha256',
            'proof': sha256_str(json.dumps(obj, ensure_ascii=False, sort_keys=True)),
            'files': [],
            'licensing': 'internal-use-license-v1',
            'tags': ['entity','profile'],
            'price_cny_floor': 1.00,
            'price_cny_ref': 5.00,
            'deliverable': 'JSON片段（可验证哈希）'
        })
except Exception as e:
    pass

# HTML
for i,p in enumerate(ASSETS_DIR.glob('*.html')):
    aid = f'H-{datetime.now().strftime("%Y%m%d")}-{i+1:06d}'
    assets.append({
        'asset_id': aid,
        'type': '网页快照',
        'name': p.stem,
        'source': str(p).replace('F:\\2026\\24xs\\',''),
        'proof_type': 'sha256',
        'proof': sha256_file(p),
        'files': [str(p).replace('F:\\2026\\24xs\\','')],
        'licensing': 'internal-use-license-v1',
        'tags': ['snapshot','html'],
        'price_cny_floor': 0.50,
        'price_cny_ref': 2.00,
        'deliverable': 'HTML快照文件'
    })

# CCGP notices
try:
    import sqlite3
    db = r'F:\2026\24xs\11_数据资产\ccgp_production.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute('SELECT rowid, * FROM notices')
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for i,r in enumerate(rows):
        row = dict(zip(cols,r))
        aid = f'N-{datetime.now().strftime("%Y%m%d")}-{i+1:06d}'
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            'asset_id': aid,
            'type': '招采公告',
            'name': (row.get('title') or row.get('TITLE') or f'notice_{row.get("rowid") or i}')[:120],
            'source': '11_数据资产/ccgp_production.db:notices',
            'proof_type': 'sha256',
            'proof': sha256_str(s),
            'files': [],
            'licensing': 'internal-use-license-v1',
            'tags': ['ccgp','notice','b2b'],
            'price_cny_floor': 0.20,
            'price_cny_ref': 1.00,
            'deliverable': '结构化记录(JSON)'
        })
    conn.close()
except Exception as e:
    pass

# yield
try:
    import sqlite3
    db = r'F:\2026\24xs\11_数据资产\yield_test.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='n'")
    cur.execute('SELECT rowid,* FROM n')
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for i,r in enumerate(rows):
        row = dict(zip(cols,r))
        aid = f'Y-{datetime.now().strftime("%Y%m%d")}-{i+1:06d}'
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            'asset_id': aid,
            'type': '抽取结果',
            'name': f'yield_{row.get("rowid") or i}',
            'source': '11_数据资产/yield_test.db:n',
            'proof_type': 'sha256',
            'proof': sha256_str(s),
            'files': [],
            'licensing': 'internal-use-license-v1',
            'tags': ['extract','yield'],
            'price_cny_floor': 0.10,
            'price_cny_ref': 0.50,
            'deliverable': '结构化记录(JSON)'
        })
    conn.close()
except Exception as e:
    pass

# factory probes
try:
    import sqlite3
    db = r'F:\2026\24xs\99_产出\_data\factory.sqlite3'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute('SELECT rowid,* FROM geo_probes')
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for i,r in enumerate(rows):
        row = dict(zip(cols,r))
        aid = f'P-{datetime.now().strftime("%Y%m%d")}-{i+1:06d}'
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            'asset_id': aid,
            'type': 'GEO探测',
            'name': f'probe_{row.get("rowid") or i}',
            'source': '99_产出/_data/factory.sqlite3:geo_probes',
            'proof_type': 'sha256',
            'proof': sha256_str(s),
            'files': [],
            'licensing': 'internal-use-license-v1',
            'tags': ['geo','probe'],
            'price_cny_floor': 0.50,
            'price_cny_ref': 2.00,
            'deliverable': '探测记录(JSON)'
        })
    conn.close()
except Exception as e:
    pass

OUT_DIR = BASE / 'registry'
OUT_DIR.mkdir(exist_ok=True)
with open(OUT_DIR / 'assets_registry.json','w',encoding='utf-8') as f:
    json.dump(assets,f,ensure_ascii=False,indent=2)
with open(OUT_DIR / 'sku_list.json','w',encoding='utf-8') as f:
    skus = []
    for a in assets:
        skus.append({'sku_id':a['asset_id'],'name':a['name'][:60],'type':a['type'],'price_cny_ref':a['price_cny_ref'],'proof':a['proof'][:16]+'...'})
    json.dump(skus,f,ensure_ascii=False,indent=2)
print(len(assets))
