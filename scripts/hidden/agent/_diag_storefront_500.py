#!/usr/bin/env python3
"""测试 storefront 各端点 + 诊断 alipay.js 失败原因"""
import urllib.request, urllib.error

HOST = "https://tools.highkingflower.com"

endpoints = [
    "/", "/sitemap.xml", "/eba1648ac2e72921f694b451970d59d9.txt",
    "/dashboard", "/api/dashboard",
    "/api/health", "/api/pay", "/api/plans", "/api/config", "/api/track",
    "/api/pending", "/api/alert", "/api/subwall",
    "/api/commission", "/api/stripe/checkout", "/api/wxpay/create",
    "/api/paypal/order", "/api/paypal/capture", "/api/paypal/status",
    "/pay/return", "/pay/cancel",
]

print("=== storefront 端点状态 ===")
for p in endpoints:
    url = HOST + p
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "diag/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode("utf-8", "replace")[:80]
            print(f"  ✅ {p:30s} HTTP {r.status}")
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", "replace")[:80]
        if e.code == 500:
            print(f"  ❌ {p:30s} HTTP 500  (server error)")
        elif e.code == 404:
            print(f"  ⚠️  {p:30s} HTTP 404")
        elif e.code == 503:
            print(f"  ⚠️  {p:30s} HTTP 503 (disabled)")
        else:
            print(f"  ❌ {p:30s} HTTP {e.code}")
    except Exception as e:
        print(f"  ❌ {p:30s} ERR {type(e).__name__}")

# 检查 Vercel 函数调用失败的原因
print("\n=== /api/health 详细错误 ===")
try:
    req = urllib.request.Request(HOST + "/api/health", headers={"User-Agent": "diag/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"HTTP {r.status}")
except urllib.error.HTTPError as e:
    body = (e.read() or b"").decode("utf-8", "replace")
    print(f"HTTP {e.code}")
    print(f"body: {body[:300]}")
    if "FUNCTION_INVOCATION_FAILED" in body:
        # 解析 Vercel 错误代码
        import re
        m = re.search(r"hnd1::(\w+)", body)
        if m:
            print(f"Vercel 错误标识: {m.group(1)}")
