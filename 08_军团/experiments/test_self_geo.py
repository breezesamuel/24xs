# -*- coding: utf-8 -*-
"""自家站点的自我验收：JSON-LD 合法性 + 用自家体检引擎测自家站。

这是产品可信度的底线 —— 我卖的就是"帮你修 AI 可见度"，那自己的站必须先过。
之前 /llms.txt 是 404，也就是自家站通不过自家体检，说服力为零。
"""
import json
import pathlib
import re
import sys

SITE = pathlib.Path(r"F:\2026\24xs\10_官网")
sys.path.insert(0, r"F:\2026\24xs\10_官网\api")
import audit  # noqa: E402

ok = fail = 0


def case(name, cond, why=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [PASS] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {why}")


print("=== 1. JSON-LD 合法性 ===")
html = (SITE / "index.html").read_text(encoding="utf-8")
blocks = re.findall(
    r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
case("存在 JSON-LD 块", len(blocks) >= 1, str(len(blocks)))
types, has_org, has_faq = [], False, False
for b in blocks:
    try:
        d = json.loads(b)
    except Exception as e:
        case("JSON 可解析", False, str(e)[:80])
        continue
    for node in d.get("@graph", [d]):
        t = node.get("@type")
        types.append(t)
        has_org = has_org or t in ("Organization", "LocalBusiness")
        has_faq = has_faq or t == "FAQPage"
    case("JSON 可解析", True)
print(f"       @type: {types}")

print("\n=== 2. 必备的 AI 入口文件 ===")
for f in ("robots.txt", "llms.txt", "sitemap.xml"):
    p = SITE / f
    case(f"{f} 存在", p.is_file())
    if p.is_file():
        case(f"{f} 非空", p.stat().st_size > 40, str(p.stat().st_size))
rt = (SITE / "robots.txt").read_text(encoding="utf-8")
for bot in ("GPTBot", "ClaudeBot", "PerplexityBot", "Baiduspider", "Bytespider"):
    case(f"robots 放行 {bot}", bot in rt)
case("robots 有 sitemap 声明", "Sitemap:" in rt)

print("\n=== 3. 用自家引擎测自家站（经本地 china 服务的真实抓取）===")
import threading  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402

# 用**国内服务器那套真实路由器**来提供页面，而不是 audit.Handler ——
# 后者只有 do_POST（Vercel 函数形态），根本不能提供静态页，那样测的是个假东西。
sys.path.insert(0, r"F:\2026\24xs\10_官网\china")
import server as chs  # noqa: E402

srv = ThreadingHTTPServer(("127.0.0.1", 0), chs.Router)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_port
url = f"http://127.0.0.1:{port}/index.html"
# 只在本测试里放行环回地址：生产必须挡住 127.0.0.1（SSRF 防护），
# 正是它刚才挡住了本地自测 —— 那是正确行为，不能为了让自测过而削弱它。
_real_guard = audit._public_host
audit._public_host = lambda u: (True, "")
try:
    r = audit.audit(url)
finally:
    audit._public_host = _real_guard
srv.shutdown()
case("自家站可达", r["reachable"] is True, str(r))
print(f"       分数 = {r['score']}/100  评级 = {r['grade']}")
print(f"       拦截AI爬虫={r['blocked_bots']}  schema={r['schema']}")
for b in r["blockers"]:
    print(f"       - {b}")
case("自家站 >= 80 分", r["score"] >= 80, str(r["score"]))
case("环回地址在生产仍被挡",
     _real_guard("http://127.0.0.1/")[0] is False)

print("\n=== 4. 首页有转化入口 ===")
case("有免费体检输入框", 'id="faUrl"' in html)
case("有 ¥99 解锁按钮", 'id="faBuy"' in html)
case("调用后端 API", "/api/audit" in html)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)