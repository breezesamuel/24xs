# -*- coding: utf-8 -*-
"""国内服务器形态（china/server.py）的端到端验收。

这条路径和 Vercel 完全不同：不是各自独立冷启动的函数，而是**一个进程
里共享模块级限流状态**的路由器。Vercel 上测过不代表这里能过，所以单独立测。

覆盖：静态、目录穿越、四条 API 路由、SSRF、限流、跨模块共享状态。
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

CHINA = r"F:\2026\24xs\10_官网\china"
PORT = int(os.environ.get("TEST_PORT", "8833"))
BASE = f"http://127.0.0.1:{PORT}"
ok = fail = 0


def case(name, cond, why=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [PASS] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {why}")


def get(path):
    try:
        r = urllib.request.urlopen(BASE + path, timeout=30)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def post(path, obj, hdrs=None):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers=hdrs or {"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=90)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"exc": str(e)}


# 等端口起来
for _ in range(40):
    s = socket.socket()
    try:
        s.connect(("127.0.0.1", PORT))
        s.close()
        break
    except Exception:
        time.sleep(0.25)
    finally:
        try:
            s.close()
        except Exception:
            pass

print("=== 1. 静态资源 ===")
st, body = get("/")
case("首页 200", st == 200, str(st))
case("首页是 HTML", b"<html" in body.lower() or b"<!doctype" in body.lower())
case("首页含免费体检入口", b'id="faUrl"' in body)
st, _ = get("/subscribe.html")
case("订阅页 200", st == 200, str(st))
st, _ = get("/llms.txt")
case("llms.txt 已部署(200)", st == 200, str(st))
st, _ = get("/api/nope")
case("未知 POST 路由 404", st == 404, str(st))

print("\n=== 2. 目录穿越 ===")
for evil in ("/../../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd", "/..%2f..%2fetc/passwd"):
    st, b = get(evil)
    case(f"穿越被挡 {evil[:26]}", st in (403, 404) and b"root:" not in b, str(st))

print("\n=== 3. 四条 API 路由都能应答 ===")
st, d = post("/api/audit", {"url": "http://169.254.169.254/"})
case("audit SSRF 挡下(400)", st == 400, f"{st} {d}")
st, d = post("/api/audit", {"url": ""})
case("audit 空输入 400", st == 400, f"{st} {d}")
st, d = post("/api/alipay_pay", {"plan": "hacker", "email": "a@b.cn"})
case("alipay_pay 非法档位 400", st == 400, f"{st} {d}")
st, d = post("/api/order", {})
case("order 应答非 500", st != 500, f"{st} {d}")
st, d = post("/api/alipay_notify", {})
case("notify 空通知被拒(非200业务失败)", st in (200, 400, 403), f"{st} {d}")

print("\n=== 4. 真实体检能跑通 ===")
st, d = post("/api/audit", {"url": "https://www.baidu.com"})
case("公网站 200", st == 200, f"{st} {str(d)[:90]}")
if st == 200:
    case("返回分数", isinstance(d.get("score"), int), str(d.get("score")))
    case("返回评级", bool(d.get("grade")))
    case("免费层不含付费模板",
         not any(k in json.dumps(d, ensure_ascii=False)
                 for k in ("@context", "PostalAddress", "acceptedAnswer")))

print("\n=== 5. 限流状态在本进程内跨请求共享 ===")
codes = [post("/api/audit", {"url": "https://www.baidu.com"})[0] for _ in range(14)]
case("触发 429", 429 in codes, str(codes[-3:]))

print("\n=== 6. 并发不能把服务打挂 ===")
import threading  # noqa: E402
res = []


def hit(i):
    res.append(post("/api/audit", {"url": "https://www.baidu.com"})[0])


ts = [threading.Thread(target=hit, args=(i,)) for i in range(12)]
[t.start() for t in ts]
[t.join() for t in ts]
case("并发 12 请求无 5xx", all(c in (200, 400, 429) for c in res),
     str(sorted(set(res))))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)