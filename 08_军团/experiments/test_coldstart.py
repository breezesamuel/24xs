# -*- coding: utf-8 -*-
"""隔离导入回归：本地同进程测试会掩盖"漏 import"。

本地跑测试时，别的模块（比如 alipay_lib）可能已经 import 过 urllib.request，
于是 audit.py 里漏写也能跑通。但 Vercel 每个函数是独立冷启动，
只会 import audit.py 自己，漏掉的 import 直接 AttributeError -> 502。

这个测试在**干净子进程**里只 import audit，然后真正调用一次 audit()。
"""
import subprocess, sys, textwrap, os
ok = fail = 0
def case(n, cond, why=""):
    global ok, fail
    if cond: ok += 1; print(f"  [PASS] {n}")
    else: fail += 1; print(f"  [FAIL] {n} {why}")

print("=== 1. 每个 api 模块单独冷启动能否 import ===")
api = r"F:\2026\24xs\10_官网\api"
mods = ["audit", "alipay_lib", "alipay_pay", "alipay_notify", "geo_health"]
for m in mods:
    r = subprocess.run([sys.executable, "-c",
        f"import sys; sys.path.insert(0,{api!r}); import {m}; print('ok')"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    case(f"{m}.py 独立 import", "ok" in r.stdout,
         (r.stderr or "").strip().splitlines()[-1] if r.stderr else "")

print("\n=== 2. 干净进程里真跑一次 audit() ===")
r = subprocess.run([sys.executable, "-c", textwrap.dedent("""
    import sys
    sys.path.insert(0, r"F:\\2026\\24xs\\10_官网\\api")
    import audit
    res = audit.audit("https://www.baidu.com")
    assert isinstance(res.get("score"), int), res
    assert res.get("host"), res
    print("score=%s grade=%s" % (res["score"], res["grade"]))
""")], capture_output=True, text=True, encoding="utf-8", errors="replace",
   env={**os.environ, "PYTHONIOENCODING": "utf-8"})
case("audit() 在冷启动下返回结果", "score=" in r.stdout,
     (r.stderr or "").strip().splitlines()[-1] if r.stderr else "")
if "score=" in r.stdout:
    print("       -> " + r.stdout.strip())

print("\n=== 3. 冷启动下 SSRF 仍生效 ===")
r = subprocess.run([sys.executable, "-c", textwrap.dedent("""
    import sys
    sys.path.insert(0, r"F:\\2026\\24xs\\10_官网\\api")
    import audit
    for u in ("http://127.0.0.1/", "http://169.254.169.254/", "http://10.0.0.1/"):
        try:
            audit.audit(u); print("LEAK", u)
        except ValueError:
            pass
    print("blocked-all")
""")], capture_output=True, text=True, encoding="utf-8", errors="replace",
   env={**os.environ, "PYTHONIOENCODING": "utf-8"})
case("内网/元数据/私网 全部被挡", "blocked-all" in r.stdout and "LEAK" not in r.stdout,
     r.stdout.strip()[-80:])
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
