# -*- coding: utf-8 -*-
"""验证两种真实崩溃窗口，都能收敛且不重复发额度。

A) activate 抛错（钱收了，额度没开）-> 重试必须补上
B) activate 成功但没来得及置 fulfilled（额度已开）-> 重试不能重复发
"""
import sys, sqlite3, tempfile, shutil
from pathlib import Path
sys.path.insert(0, r"F:\2026\24xs\01_引擎")
sys.path.insert(0, r"F:\2026\24xs\08_军团\experiments")
import sub_admin
ok = fail = 0
def case(n, cond, why=""):
    global ok, fail
    if cond: ok += 1; print(f"  [PASS] {n}")
    else: fail += 1; print(f"  [FAIL] {n} {why}")
def setup(tag):
    d = Path(tempfile.mkdtemp())
    sub_admin.DB = d / "t.sqlite3"
    lg = d / "log.txt"
    lg.write_text(
        "[ALIPAY-ORDER] no=G1-20261001120001-ZZZZZZ-6000-M plan=month "
        "cents=6000 lang=cn ref= email=%s@test.cn\n"
        "[ALIPAY-PAID] no=G1-20261001120001-ZZZZZZ-6000-M\n" % tag,
        encoding="utf-8")
    return lg
def q(sql, *a):
    c = sqlite3.connect(sub_admin.DB); c.row_factory = sqlite3.Row
    r = c.execute(sql, a).fetchone(); c.close(); return r

print("=== A) 开通前崩溃：钱收了但额度没开 ===")
lg = setup("crashA")
real = sub_admin.activate
sub_admin.activate = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("崩"))
sub_admin.import_alipay([lg])
case("订单记为 paid", q("SELECT status FROM orders")["status"] == "paid")

case("额度确实还没开", q("SELECT uses_left FROM users") is None)
case("未标记交付", q("SELECT fulfilled FROM orders")["fulfilled"] == 0)
sub_admin.activate = real
sub_admin.import_alipay([lg])
case("重试后额度补上 60", q("SELECT uses_left FROM users")["uses_left"] == 60)
case("重试后标记交付", q("SELECT fulfilled FROM orders")["fulfilled"] == 1)

print("\n=== B) 开通后崩溃：额度已开但没置 fulfilled ===")
lg = setup("crashB")
sub_admin.activate = real
sub_admin.import_alipay([lg])
# 模拟"额度已发、fulfilled 还没写"这一瞬间的状态
c = sqlite3.connect(sub_admin.DB); c.execute("UPDATE orders SET fulfilled=0")
c.commit(); c.close()
sub_admin.import_alipay([lg])
u = q("SELECT uses_total,uses_left FROM users")
case("额度没有重复发放（仍是 60）", u["uses_total"] == 60 and u["uses_left"] == 60,
     f"total={u['uses_total']} left={u['uses_left']}")
case("标记补齐为 1", q("SELECT fulfilled FROM orders")["fulfilled"] == 1)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
