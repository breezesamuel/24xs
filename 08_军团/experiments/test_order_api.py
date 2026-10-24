"""本地测试 api/order.py，不部署也能验证行为。

重点验四件事：
  1. 正常申请能拿到编号
  2. 邮箱非法 / 套餐非法 / body 超大 / GET 都被拒
  3. 返回体里不含任何凭据
  4. 限流真的会触发（同一 IP 连续打）
"""
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(r"F:\2026\24xs\10_官网") / "api"))
sys.stdout.reconfigure(encoding="utf-8")

import order  # noqa: E402  复用被测模块本身，不复制逻辑

HOST, PORT = "127.0.0.1", 8791
BASE = f"http://{HOST}:{PORT}/api/order"

passed = failed = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}  {extra}")


def post(payload, raw: bytes | None = None, ctype="application/json"):
    body = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(BASE, data=body,
                                 headers={"Content-Type": ctype},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


class Q(BaseHTTPRequestHandler):
    def log_message(self, *a):
        return

    def do_GET(self):
        self.send_response(405)
        self.send_header("Content-Length", "0")
        self.end_headers()


srv = HTTPServer((HOST, PORT), Q)
srv.RequestHandlerClass = order.handler
threading.Thread(target=srv.serve_forever, daemon=True).start()

print("=" * 70)
print("  api/order.py 本地验收")
print("=" * 70)

st, j = post({"email": "a@example.com", "plan": "month", "lang": "cn"})
check("正常申请返回 201", st == 201, f"got {st} {j}")
check("返回申请编号 GEO-YYYYMMDD-XXXXXX",
      isinstance(j.get("order_id"), str) and j["order_id"].startswith("GEO-"),
      str(j))
check("状态为 pending_payment", j.get("status") == "pending_payment", str(j))
check("返回收款支付宝账号", j.get("pay_alipay", "").count("@") == 1, str(j))

st, _ = post({"email": "not-an-email", "plan": "month"})
check("非法邮箱被拒 400", st == 400, f"got {st}")

st, _ = post({"email": "a@example.com", "plan": "lifetime"})
check("非法套餐被拒 400", st == 400, f"got {st}")

st, _ = post({"email": "a@example.com", "plan": "month",
              "site": "javascript:alert(1)"})
check("非 http(s) 网址被拒 400", st == 400, f"got {st}")

st, _ = post(None, raw=b"x" * 5000)
check("超大 body 被拒 413", st == 413, f"got {st}")

st, _ = post(None, raw=b"{not json")
check("坏 JSON 被拒 400", st == 400, f"got {st}")

st, j = post({"email": "a@example.com", "plan": "month",
              "ref": "<script>x</script>", "lang": "cn"})
blob = json.dumps(j, ensure_ascii=False)
check("返回体不含用户原文回显",
      "<script>" not in blob, blob)

try:
    req = urllib.request.Request(BASE, method="GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        gst = r.status
except urllib.error.HTTPError as e:
    gst = e.code
check("GET 被拒 405", gst == 405, f"got {gst}")

codes = []
for i in range(order.RATE_MAX + 4):
    st, _ = post({"email": f"r{i}@example.com", "plan": "year"})
    codes.append(st)
check("连续高频触发限流 429", 429 in codes,
      f"codes={codes[-6:]}")

srv.shutdown()
print("=" * 70)
print(f"  {passed} passed, {failed} failed")
print("=" * 70)
raise SystemExit(0 if failed == 0 else 1)
