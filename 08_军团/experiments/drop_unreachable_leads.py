# -*- coding: utf-8 -*-
"""把真实名单里"三种联系方式全空"的行剔除。

背景：上海宠伊宠物诊所原本只有一个从 <script> 里抓出来的噪音号
0368738174，清掉之后就完全没有联系方式了。这种行不该留在
"真实核验名单"里 —— 留着只会让人以为有线索可跟。
数据库里它已经是 needs_contact，CSV 要跟上。
"""
from __future__ import annotations

import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

LEAD_DIR = Path(r"F:\2026\24xs\99_产出\获客名单")
BACKUP_DIR = LEAD_DIR / "_backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

CONTACT_COLS = ("电话", "邮箱", "微信")
dropped_total = 0

for p in sorted(LEAD_DIR.glob("真实名单_*.csv")):
    if ".bak-" in p.name:
        continue
    with p.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    keep, drop = [], []
    for r in rows:
        if any(str(r.get(k) or "").strip() not in ("", "-") for k in CONTACT_COLS):
            keep.append(r)
        else:
            drop.append(r)

    if not drop:
        continue

    shutil.copy2(p, BACKUP_DIR / f"{p.stem}.bak-{stamp}.csv")
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(keep)

    for r in drop:
        print(f"  [剔除] {r.get('公司')}  （三种联系方式全空）")
    print(f"  已重写 {p.name}  保留 {len(keep)} / 剔除 {len(drop)}  备份见 _backup/")
    dropped_total += len(drop)

print()
print("=" * 70)
print(f"共剔除 {dropped_total} 行无联系方式的线索" if dropped_total
      else "名单里没有空联系方式行")
print("=" * 70)
