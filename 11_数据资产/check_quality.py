# -*- coding: utf-8 -*-
"""把抽取结果写成 JSON 文件（绕开控制台编码），验证真实抽取质量。"""
import io
import json
import re
import sys

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
from ccgp_pipeline import _get, detail_text, parse_detail, parse_list, search_url  # noqa

OUT = r"F:\2026\24xs\11_数据资产\_抽取质量.json"

rows = parse_list(_get(search_url(1, "医院")))
report = {"list_items": len(rows), "samples": []}
for row in rows[:8]:
    try:
        html = _get(row["url"], tries=2)
    except Exception as e:
        report["samples"].append({"url": row["url"], "error": type(e).__name__})
        continue
    d = parse_detail(html, row["url"])
    d["_list_title"] = row["title"]
    d["_list_date"] = row["list_date"]
    d["_list_prov"] = row["province"]
    report["samples"].append(d)

# 统计字段命中率
fields = ["project_no", "project_name", "buyer", "buyer_address", "agency",
          "agency_contact", "open_time", "publish_date", "budget", "channel"]
ok = {f: sum(1 for s in report["samples"] if s.get(f)) for f in fields}
report["hit_rate"] = {f: "%d/%d" % (v, len(report["samples"])) for f, v in ok.items()}

# 确认编码真实无损：检查是否有 U+FFFD
txt = detail_text(_get(rows[0]["url"]))
report["replacement_chars"] = txt.count("\ufffd")
report["sample_text_head"] = txt[:300]

with io.open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("written", OUT)
