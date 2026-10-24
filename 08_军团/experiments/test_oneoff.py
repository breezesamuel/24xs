# -*- coding: utf-8 -*-
"""一次性报告档（report/¥99）通过支付导入器：金额、交付、不占额度、幂等。

崩溃窗口的测试在 test_crash_retry.py，不在这里重复。
"""
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"F:\2026\24xs\01_引擎")
sys.path.insert(0, r"F:\2026\24xs\08_军团\experiments")

tmp = Path(tempfile.mkdtemp())
DB = tmp / "t.sqlite3"
LOG = tmp / "log.txt"
LOG.write_text(
    "[ALIPAY-ORDER] no=G1-20261001120000-AAAAAA-9900-R plan=report "
    "cents=9900 lang=cn ref= email=rpt@test.cn\n"
    "[ALIPAY-ORDER] no=G1-20261001120001-BBBBBB-6000-M plan=month "
    "cents=6000 lang=cn ref= email=sub@test.cn\n"
    "[ALIPAY-PAID] no=G1-20261001120000-AAAAAA-9900-R\n"
    "[ALIPAY-PAID] no=G1-20261001120001-BBBBBB-6000-M\n",
    encoding="utf-8")

import sub_admin  # noqa: E402

sub_admin.DB = DB
ok = fail = 0


def case(name, cond, why=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [PASS] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {why}")


def q(sql, *a):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    r = c.execute(sql, a).fetchone()
    c.close()
    return r


print("=== import with report tier ===")
sub_admin.import_alipay([LOG])
rpt = q("SELECT * FROM orders WHERE plan='report'")
case("report paid", rpt["status"] == "paid")
case("report amount 99", abs(rpt["amount"] - 99) < 0.001, rpt["amount"])
case("report fulfilled", rpt["fulfilled"] == 1)
case("report note", bool(rpt["note"]), rpt["note"])
case("report not a subscriber",
     q("SELECT COUNT(*) c FROM users WHERE email='rpt@test.cn'")["c"] == 0)
case("month opened",
     q("SELECT COUNT(*) c FROM users WHERE email='sub@test.cn'")["c"] == 1)
case("month uses=60",
     q("SELECT uses_left FROM users WHERE email='sub@test.cn'")["uses_left"] == 60)

print("\n=== idempotent re-import ===")
sub_admin.import_alipay([LOG])
sub_admin.import_alipay([LOG])
case("uses not multiplied",
     q("SELECT uses_left FROM users WHERE email='sub@test.cn'")["uses_left"] == 60)
case("report note not rewritten twice",
     q("SELECT fulfilled FROM orders WHERE plan='report'")["fulfilled"] == 1)

print("\n=== report tier never touches quota ===")
before = q("SELECT SUM(uses_total) t FROM users")["t"]
sub_admin.import_alipay([LOG])
case("total quota unchanged",
     q("SELECT SUM(uses_total) t FROM users")["t"] == before)

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)