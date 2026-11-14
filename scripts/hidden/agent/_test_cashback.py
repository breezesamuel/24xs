#!/usr/bin/env python3
"""测试 CN /api/cashback 端点 (fail-closed + 各 action)"""
import urllib.request, ssl, json
ctx = ssl.create_default_context()
def call(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {"User-Agent":"Mozilla/5.0"})
    try:
        r = urllib.request.urlopen(req, timeout=30, context=ctx)
        return r.status, r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8","replace")
BASE = "https://tools-cn.highkingflower.com"
print("=== 1. /api/cashback?action=rate (无 ref, 应 ok + rate_pct=5) ===")
s,b = call(f"{BASE}/api/cashback?action=rate")
print("  ", s, b[:150])
print("=== 2. /api/cashback?action=summary&ref=TESTUSER (无存储应 store_failed/fail-closed) ===")
s,b = call(f"{BASE}/api/cashback?action=summary&ref=TESTUSER")
print("  ", s, b[:150])
print("=== 3. /api/cashback 无 ref (应 missing_or_invalid_ref, 不 500) ===")
s,b = call(f"{BASE}/api/cashback")
print("  ", s, b[:120])
print("=== 4. 不存在的 action (应 404 no_route, 不 500) ===")
s,b = call(f"{BASE}/api/cashback?action=bogus&ref=TESTUSER")
print("  ", s, b[:120])
