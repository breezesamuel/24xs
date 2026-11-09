#!/usr/bin/env python3
"""详细测试支付宝建单: /api/pay + /api/order + 签名探测"""
import urllib.request, urllib.error, json

HOST = "https://tools.highkingflower.com"

def post(path, payload):
    url = HOST + path
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), method="POST",
            headers={"User-Agent": "diag", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"  {path}: HTTP {r.status}")
            print(f"  body: {body[:500]}")
            return r.status, body
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", "replace")
        print(f"  {path}: HTTP {e.code}  body: {body[:400]}")
        return e.code, body
    except Exception as e:
        print(f"  {path}: ERR {type(e).__name__}: {e}")
        return 0, str(e)

def get(path):
    url = HOST + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "diag"})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode("utf-8", "replace")
            print(f"  {path}: HTTP {r.status}")
            print(f"  body: {body[:400]}")
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", "replace")
        print(f"  {path}: HTTP {e.code}  body: {body[:400]}")
    except Exception as e:
        print(f"  {path}: ERR {type(e).__name__}: {e}")

print("=== 1. /api/pay 建单 (POST) ===")
post("/api/pay", {"plan": "trial", "ref": "alipay_diag_1"})

print("\n=== 2. /api/config (GET 查支付宝 app_id/account/ready) ===")
get("/api/config")

print("\n=== 3. /api/aliq 探测 (GET 查支付宝网关连通性) ===")
get("/api/aliq")
