# -*- coding: utf-8 -*-
"""@graph 支持回归。

背景：JSON-LD 有两种常见写法 ——
  A. 顶层直接是实体      {"@type":"Organization", ...}
  B. @graph 包一层      {"@context":..., "@graph":[{...},{...}]}   ← Google 推荐
早期实现只认 A，把 B 判成"完全没有结构化数据"。这是**假阴性**：客户会照着
报告去整改一个根本不存在的��题，钱花了问题还在 —— 这种 bug 最伤信任。

这里锁住两种写法都必须被识别。
"""
import json
import pathlib
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, r"F:\2026\24xs\10_官网\api")
sys.path.insert(0, r"F:\2026\24xs\01_引擎")
sys.path.insert(0, r"F:\2026\24xs\10_官网\china")
import audit as apiaudit  # noqa: E402
import geo_health as gh  # noqa: E402
import server as chs  # noqa: E402

ok = fail = 0


def case(name, cond, why=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [PASS] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {why}")


def entities():
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@graph":['
            '{"@type":"Organization","name":"X"},'
            '{"@type":"FAQPage","mainEntity":[]}]}'
            '</script>')


def flat():
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Organization","name":"X"}'
            '</script>')


def as_list():
    return ('<script type="application/ld+json">'
            '[{"@context":"https://schema.org","@type":"Organization"}]'
            '</script>')


print("=== 1. _nodes 单元行为 ===")
for name, obj, want in [
    ("平铺实体", json.loads(flat().split(">")[1].split("</")[0]), 1),
    ("@graph 多实体", json.loads(entities().split(">")[1].split("</")[0]), 2),
    ("数组", json.loads(as_list().split(">")[1].split("</")[0]), 1),
    ("非字典", "hello", 0),
    ("空 graph", {"@graph": []}, 0),
]:
    got = len(apiaudit._nodes(obj))
    case(f"_nodes({name}) = {want}", got == want, f"got {got}")

print("\n=== 2. 端到端：三种写法都要被认出来 ===")
srv = ThreadingHTTPServer(("127.0.0.1", 0), chs.Router)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_port
_real = apiaudit._public_host
apiaudit._public_host = lambda u: (True, "")
_real_gh = gh._public_host if hasattr(gh, "_public_host") else None
if _real_gh:
    gh._public_host = lambda u: (True, "")

try:
    import tempfile
    body = {"index.html": "<html><head>" + entities() + "</head><body>x</body></html>"}
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "index.html").write_text(body["index.html"], encoding="utf-8")
    chs.WEB = d
    r = apiaudit.audit(f"http://127.0.0.1:{port}/index.html")
    case("api/audit 认得 @graph", "Organization" in r["schema"], str(r["schema"]))
    case("api/audit 认得 FAQPage", "FAQPage" in r["schema"], str(r["schema"]))
    case("api/audit has_org=True", r["has_org"] is True)
    case("api/audit 报告里有结构化数据",
         any("结构化数据" not in b for b in r["blockers"])
         or not any("没有 JSON-LD" in b for b in r["blockers"]),
         str(r["blockers"]))
finally:
    chs.WEB = pathlib.Path(r"F:\2026\24xs\10_官网")
    apiaudit._public_host = _real
    if _real_gh:
        gh._public_host = _real_gh
    srv.shutdown()

print("\n=== 3. 自家站现在应 >= 80 分 ===")
sys.path.insert(0, r"F:\2026\24xs\08_军团\experiments")
srv2 = ThreadingHTTPServer(("127.0.0.1", 0), chs.Router)
threading.Thread(target=srv2.serve_forever, daemon=True).start()
p2 = srv2.server_port
apiaudit._public_host = lambda u: (True, "")
try:
    r2 = apiaudit.audit(f"http://127.0.0.1:{p2}/index.html")
    print(f"       分数 = {r2['score']}/100  评级 = {r2['grade']}")
    for b in r2["blockers"]:
        print(f"       - {b}")
    case("自家站 >= 80 分", r2["score"] >= 80, str(r2["score"]))
finally:
    apiaudit._public_host = _real
    srv2.shutdown()

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)