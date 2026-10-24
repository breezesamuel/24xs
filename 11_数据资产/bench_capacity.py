# -*- coding: utf-8 -*-
"""产能实测：跑 N 页，测真实吞吐，输出报告文件。"""
import io
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import ccgp_pipeline as P  # noqa

DB = P.DB
KWS = ["医院", "学校", "软件", "电梯", "物业", "食堂", "绿化", "保洁",
       "监控", "消防", "装修", "审计", "印刷", "车辆", "家具"]
PAGES_PER_KW = int(sys.argv[1]) if len(sys.argv) > 1 else 2

if os.path.exists(DB):
    os.remove(DB)
c = P.init_db()

start = time.time()
detail_calls = 0
list_calls = 0
for i, kw in enumerate(KWS, 1):
    for p in range(1, PAGES_PER_KW + 1):
        try:
            rows = P.parse_list(P._get(P.search_url(p, kw)))
            list_calls += 1
        except Exception as e:
            print("  %s p%d list fail %s" % (kw, p, type(e).__name__))
            continue
        for row in rows:
            try:
                html = P._get(row["url"], tries=2)
                detail_calls += 1
            except Exception:
                continue
            d = P.parse_detail(html, row["url"])
            d["title"] = row["title"]
            d["list_date"] = row["list_date"]
            d["province"] = row["province"]
            P.save(c, d)
            time.sleep(0.35)
        time.sleep(1.4)
    n = c.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    print("  [%2d/%d] %-4s 库内=%d" % (i, len(KWS), kw, n))

elapsed = time.time() - start
notices = c.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
buyers = c.execute("SELECT COUNT(*) FROM buyers").fetchone()[0]
provs = c.execute("SELECT COUNT(DISTINCT province) FROM notices "
                  "WHERE province<>''").fetchone()[0]
chan = c.execute("SELECT COUNT(DISTINCT channel) FROM notices "
                 "WHERE channel<>''").fetchone()[0]
avg_len = c.execute("SELECT ROUND(AVG(content_len)) FROM notices").fetchone()[0]
budget = c.execute("SELECT ROUND(SUM(budget_cny)) FROM notices").fetchone()[0]
with_budget = c.execute("SELECT COUNT(*) FROM notices WHERE budget_cny>0").fetchone()[0]
with_addr = c.execute("SELECT COUNT(*) FROM notices WHERE buyer_address<>''").fetchone()[0]
with_proj = c.execute("SELECT COUNT(*) FROM notices WHERE project_no<>''").fetchone()[0]

sec_per = elapsed / max(detail_calls, 1)
rate_hour = 3600.0 / sec_per if sec_per else 0

rep = {
    "关键词数": len(KWS), "每关键词页数": PAGES_PER_KW,
    "列表请求": list_calls, "详情请求": detail_calls,
    "耗时秒": round(elapsed, 1),
    "每条平均秒": round(sec_per, 2),
    "单线程每小时产能_条": round(rate_hour),
    "入库公告": notices, "唯一采购人": buyers,
    "覆盖省份": provs, "公告类别数": chan,
    "平均正文字数": avg_len,
    "有金额条数": with_budget, "有地址条数": with_addr, "有项目编号条数": with_proj,
    "预算总额_元": budget,
    "推算_24h不间断日产能_条": round(rate_hour * 24),
    "推算_到100万需天": round(1000000 / (rate_hour * 24), 1),
}
with io.open(r"F:\2026\24xs\11_数据资产\_产能报告.json", "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=2)

print("\n=== 样本（采购人 Top8）===")
for r in c.execute("SELECT name,province,n_notices,total_budget FROM buyers "
                   "ORDER BY n_notices DESC LIMIT 8"):
    print("  %-40s %-4s %d条 %.0f元" % (r[0][:40], r[1] or "-", r[2], r[3]))
c.close()
print("\n报告已写入 _产能报告.json")
