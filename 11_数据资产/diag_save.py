# -*- coding: utf-8 -*-
import io
import json
import sys
import time

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import crawler24 as C  # noqa

out = []
for kw, db, yr, z in [("医院", "bidx", 2026, "110000"),
                      ("学校", "bidx", 2025, "310000"),
                      ("软件", "jzcs", 2026, "440000")]:
    u = C.search_url(1, kw, db, yr, zone=z)
    try:
        html = C.get(u, tries=2)
        items = C.parse_list(html)
    except Exception as e:
        out.append({"case": [kw, db, yr, z], "error": type(e).__name__})
        time.sleep(1.5)
        continue
    got = kept = 0
    samples = []
    for title, url in items[:6]:
        try:
            d = C.parse_detail(C.get(url, tries=2), url)
        except Exception as e:
            samples.append({"url": url, "err": type(e).__name__})
            continue
        got += 1
        samples.append({"title": title[:40], "buyer": d.get("buyer", ""),
                        "len": d.get("content_len"), "url_ok": bool(url)})
        if d.get("buyer"):
            kept += 1
        time.sleep(0.3)
    out.append({"case": [kw, db, yr, z], "list": len(items),
                "detail_ok": got, "with_buyer": kept, "samples": samples})
    time.sleep(1.2)

with io.open(r"F:\2026\24xs\11_数据资产\_入库诊断.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("ok")
