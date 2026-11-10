#!/usr/bin/env python3
"""验证 Vercel PayPal/pay 端点: 500(FUNCTION_INVOCATION_FAILED) 应变为 503/4xx (干净 fail-closed)"""
import urllib.request, urllib.error

EPS = [
    ("POST", "/api/paypal/order", {"plan": "basic"}),
    ("POST", "/api/paypal/capture", {"order_id": "TEST123"}),
    ("GET", "/api/paypal/status?order_id=TEST123", None),
    ("GET", "/pay/return?token=TEST123", None),
    ("GET", "/pay/cancel", None),
]
print("=" * 50)
print("  Vercel PayPal/pay 端点 (应干净 fail-closed, 非 500 崩溃)")
print("=" * 50)
for method, path, payload in EPS:
    url = "https://tools.highkingflower.com" + path
    if payload is not None:
        import json
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method=method,
            headers={"Content-Type": "application/json", "User-Agent": "verify"})
    else:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "verify"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode("utf-8", "replace")[:80]
            print(f"  {method:4s} {path:30s} → HTTP {r.status}  {body}")
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", "replace")[:80]
        is_crash = "FUNCTION_INVOCATION_FAILED" in body or "server error" in body.lower()
        print(f"  {method:4s} {path:30s} → HTTP {e.code}  {body}  {'❌仍崩溃' if is_crash else '✅干净'}")
    except Exception as e:
        print(f"  {method:4s} {path:30s} → {type(e).__name__} {str(e)[:50]}")
