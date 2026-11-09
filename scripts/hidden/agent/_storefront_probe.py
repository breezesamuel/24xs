#!/usr/bin/env python3
"""Diagnose storefront endpoints"""
import urllib.request, urllib.error, json

def probe(name, url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bds-diag/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", "replace")[:300]
            ct = r.headers.get("Content-Type", "")
            print(f"{name:30s} HTTP {r.status}  CT={ct[:30]}")
            if "error" in body.lower() or "fail" in body.lower():
                print(f"  body: {body[:200]}")
            return r.status, body
    except urllib.error.HTTPError as e:
        body = (e.read() or b"").decode("utf-8", "replace")[:300]
        print(f"{name:30s} HTTP {e.code}  body: {body[:200]}")
        return e.code, body
    except Exception as e:
        print(f"{name:30s} ERR {type(e).__name__}: {str(e)[:100]}")
        return 0, str(e)

print("=== storefront 端点检查 ===")
HOST = "https://tools.highkingflower.com"
tests = [
    ("首页", f"{HOST}/"),
    ("health", f"{HOST}/api/health"),
    ("pay", f"{HOST}/api/pay"),
    ("dashboard", f"{HOST}/dashboard"),
    ("dashboard API", f"{HOST}/api/dashboard"),
    ("plans", f"{HOST}/api/plans"),
    ("config", f"{HOST}/api/config"),
    ("IndexNow key", f"{HOST}/eba1648ac2e72921f694b451970d59d9.txt"),
    ("sitemap", f"{HOST}/sitemap.xml"),
]
for name, url in tests:
    probe(name, url)
