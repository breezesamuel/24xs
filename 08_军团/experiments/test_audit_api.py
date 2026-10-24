# -*- coding: utf-8 -*-
"""本地起 audit 服务跑一遍：正常站 / 内网站 / 非法输入 / 限流。"""
import json, sys, threading, urllib.request, urllib.error
sys.path.insert(0, r"F:\2026\24xs\10_官网\api")
import audit as A
from http.server import HTTPServer
ok = fail = 0
def case(name, cond, why=""):
    global ok, fail
    if cond: ok += 1; print(f"  [PASS] {name}")
    else: fail += 1; print(f"  [FAIL] {name} {why}")
def serve():
    s = HTTPServer(("127.0.0.1", 0), A.Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s
def post(port, obj):
    rq = urllib.request.Request(f"http://127.0.0.1:{port}/audit",
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(rq, timeout=60)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
s = serve(); port = s.server_port
print("=== 正常站 ===")
c, d = post(port, {"url": "https://www.baidu.com"})
case("公网站返回 200", c == 200, str(d)[:120])
if c == 200:
    case("有分数", isinstance(d.get("score"), int))
    case("有评级", bool(d.get("grade")))
    case("有 host", bool(d.get("host")))
    # 免费层绝不能泄露付费整改模板。判据用模板独有的标记，
    # 而不是 "schema.org" —— 后者会出现在合法的 @type 列表里，误判。
    blob = json.dumps(d, ensure_ascii=False)
    paid_markers = ["@context", "PostalAddress", "acceptedAnswer", "sameAs",
                    "addressLocality", "streetAddress"]
    leaked = [m for m in paid_markers if m in blob]
    case("响应不含付费整改模板", not leaked, f"泄露={leaked}")
    case("只回分数与结论字段",
         set(d.keys()) <= {"host", "reachable", "http", "blocked_bots", "schema",
                           "has_org", "has_faq", "has_llms", "has_desc",
                           "has_sitemap", "score", "grade", "blockers"},
         f"多余字段={set(d.keys())}")
    print(f"       -> {d['host']} {d['score']}分 [{d.get('grade')}] 拦AI爬虫={d.get('blocked_bots')}")
print("\n=== 安全 ===")
for label, u in [("内网地址", "http://127.0.0.1/"), ("云元数据", "http://169.254.169.254/"),
                 ("内网IP", "http://10.0.0.1/"), ("空输入", "")]:
    c, d = post(port, {"url": u})
    case(f"{label}被挡", c == 400, f"got {c} {d}")
c, d = post(port, {})
case("缺 url 被挡", c == 400)
c, d = post(port, {"url": "x" * 400})
case("超长 url 被挡", c == 400)
print("\n=== 限流（12次/小时）===")
codes = [post(port, {"url": "https://www.baidu.com"})[0] for _ in range(14)]
case("超过12次后 429", 429 in codes, f"codes={codes[-4:]}")
s.shutdown()
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
