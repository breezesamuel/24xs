# -*- coding: utf-8 -*-
"""
决定性验证：每查询约 1000 条封顶。
若按 省份 / 月份 继续切分可击穿上限 => 169,851 条可完整拿下。
"""
import io
import json
import re
import sys
import time
import urllib.parse

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import crawler24 as C  # noqa

PROV = [("110000", "北京"), ("310000", "上海"), ("440000", "广东"),
        ("320000", "江苏"), ("330000", "浙江"), ("370000", "山东"),
        ("510000", "四川"), ("420000", "湖北"), ("610000", "陕西"),
        ("460000", "海南")]


def url(page, kw, db, y0, m0, m1, zone=""):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": page, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": db,
        "kw": kw,
        "start_time": "%d:%02d:01" % (y0, m0), "end_time": "%d:%02d:31" % (y0, m1),
        "timeType": 6, "displayZone": "", "zoneId": zone, "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


def total_of(html):
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    m = re.search(r"(?:共|总共|找到)\s*(\d[\d,]*)\s*(?:条|个)", flat)
    return m.group(1) if m else None


def depth(u, cap=50):
    last = 0
    for p in range(1, cap + 1):
        try:
            it = C.parse_list(C.get(u(p), tries=2))
        except Exception:
            break
        if not it:
            break
        last = p
        time.sleep(1.0)
    return last


rep = []
print("=== A. 基线：医院/bidx/2026 全年 ===")
h = C.get(url(1, "医院", "bidx", 2026, 1, 12), tries=2)
tot = total_of(h)
print("  总数=%s  第1页条目=%d" % (tot, len(C.parse_list(h))))
rep.append({"case": "医院_2026_全年", "total": tot})

print()
print("=== B. 按省份切分（看每省总数与深度）===")
sum_prov = 0
for z, name in PROV:
    h = C.get(url(1, "医院", "bidx", 2026, 1, 12, z), tries=2)
    t = total_of(h)
    n = len(C.parse_list(h))
    print("  %-4s(z=%s) 总数=%-9s 第1页=%d" % (name, z, t, n))
    rep.append({"case": "医院_2026_" + name, "zone": z, "total": t})
    sum_prov += int(t) if (t and t.isdigit()) else 0
    time.sleep(1.6)
print("  ---- 10省合计 %d（占全国 %s 的 %.1f%%）" %
      (sum_prov, tot, 100.0 * sum_prov / int(tot) if tot and tot.isdigit() else 0))

print()
print("=== C. 按月份切分能否拿到更深 ===")
for m0, m1, lbl in [(1, 1, "1月"), (1, 3, "1-3月"), (1, 6, "1-6月"), (1, 12, "全年")]:
    u = lambda p, m0=m0, m1=m1: url(p, "医院", "bidx", 2026, m0, m1)
    h = C.get(u(1), tries=2)
    t = total_of(h)
    d = depth(u, 12)
    print("  %-6s 总数=%-9s 可达页=%d -> 约 %d 条" % (lbl, t, d, d * 20))
    rep.append({"case": "医院_2026_" + lbl, "total": t, "depth": d, "est": d * 20})
    time.sleep(1.8)

print()
print("=== D. 多年份为什么少？（2020 医院 bidx）===")
for y in (2026, 2025, 2024, 2023, 2022, 2021, 2020, 2018, 2015):
    h = C.get(url(1, "医院", "bidx", y, 1, 12), tries=2)
    print("  %d 年 总数=%-9s 第1页=%d" % (y, total_of(h), len(C.parse_list(h))))
    rep.append({"case": "医院_%d" % y, "total": total_of(h)})
    time.sleep(1.6)

with io.open(r"F:\2026\24xs\11_数据资产\_分区验证.json", "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=2)
print("\n写入 _分区验证.json")
