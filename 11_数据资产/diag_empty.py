# -*- coding: utf-8 -*-
"""诊断：空结果是「无数据」还是「被封」。看响应体特征。"""
import io
import re
import sys
import time

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import crawler24 as C  # noqa

CASES = [
    ("医院", "bidx", 2020, "已知应该有大量数据"),
    ("医院", "bidx", 2015, "应该有数据"),
    ("医院", "yixb", 2020, "邀请招标-可能有"),
    ("医院", "zbj", 2020, "中标结果-应该有"),
    ("学校", "bidx", 2020, "应该有数据"),
    ("医院", "bidx", 2026, "最新年"),
]
out = []
print("%-8s %-7s %-6s %-7s %-9s %s" % ("kw", "type", "year", "bytes", "items", "页面特征"))
for kw, db, yr, note in CASES:
    try:
        html = C.get(C.search_url(1, kw, db, yr), tries=2)
    except Exception as e:
        print("%-8s %-7s %-6s ERR %s" % (kw, db, yr, type(e).__name__))
        time.sleep(2)
        continue
    items = C.parse_list(html)
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    feat = []
    for token, tag in [("没有找到", "无结果提示"), ("总共", "含总数"),
                       ("验证码", "验证码"), ("安全验证", "安全验证"),
                       ("访问频繁", "访问频繁"), ("请稍后", "请稍后"),
                       ("系统繁忙", "系统繁忙"), ("robots", "robots"),
                       ("请输入", "交互验证")]:
        if token in html:
            feat.append(tag)
    m = re.search(r"(?:共|总共|找到)\s*(\d[\d,]*)\s*(?:条|个)", flat)
    total = m.group(1) if m else "?"
    print("%-8s %-7s %-6s %-7d %-9d 总数=%-8s %s | %s"
          % (kw, db, yr, len(html), len(items), total, ",".join(feat) or "无特征", note))
    out.append({"kw": kw, "dbselect": db, "year": yr, "bytes": len(html),
                "items": len(items), "total": total, "features": feat,
                "note": note, "head": flat[:300]})
    time.sleep(2.5)

with io.open(r"F:\2026\24xs\11_数据资产\_空结果诊断.json", "w", encoding="utf-8") as f:
    import json
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n写入 _空结果诊断.json")
