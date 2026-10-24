# -*- coding: utf-8 -*-
import sqlite3
import sys
import traceback

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import crawler24 as C  # noqa

c = C.init_db()
d = {
    "url": "http://www.ccgp.gov.cn/cggg/dfgg/gkzb/202610/t20261001_1.htm",
    "title": "测试",
    "buyer": "测试医院",
    "buyer_address": "北京",
    "agency": "",
    "open_time": "",
    "requirement": "x",
    "channel": "公开招标",
    "publish_date": "2026-10-01",
    "budget": "1万元",
    "budget_cny": 10000.0,
    "content_len": 100,
    "project_no": "A1",
    "project_name": "测试项目",
    "province": "北京",
}
# 手工执行 save 的两条 SQL，看真实异常
try:
    c.execute("""INSERT OR REPLACE INTO notices
      (url,title,publish_date,province,channel,project_no,project_name,buyer,
       buyer_address,agency,open_time,requirement,budget,budget_cny,
       content_len,kw,dbselect,datetime('now'))
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
              (d["url"], d["title"], d["publish_date"], d["province"], d["channel"],
               d["project_no"], d["project_name"], d["buyer"], d["buyer_address"],
               d["agency"], d["open_time"], d["requirement"], d["budget"],
               d["budget_cny"], d["content_len"], "kw", "db"))
    print("notices INSERT ok")
except Exception:
    print("notices INSERT FAIL:")
    traceback.print_exc()

try:
    c.execute("""INSERT INTO buyers (name,n_notices,total_budget,latest,latest_url)
      VALUES (?,1,?,?,?) ON CONFLICT(name) DO UPDATE SET
      n_notices=n_notices+1, total_budget=total_budget+excluded.total_budget,
      latest=CASE WHEN excluded.latest>latest THEN excluded.latest ELSE latest END,
      latest_url=CASE WHEN excluded.latest>latest THEN excluded.latest_url ELSE latest_url END""",
              (d["buyer"], d["budget_cny"], d["publish_date"], d["url"]))
    print("buyers UPSERT ok")
except Exception:
    print("buyers UPSERT FAIL:")
    traceback.print_exc()

c.commit()
print("save() returns:", C.save(c, d, "kw", "db"))
print("notices count:", c.execute("SELECT COUNT(*) FROM notices").fetchone()[0])
print("buyers count:", c.execute("SELECT COUNT(*) FROM buyers").fetchone()[0])
