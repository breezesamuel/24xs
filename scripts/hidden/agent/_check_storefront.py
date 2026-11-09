#!/usr/bin/env python3
"""检查 storefront 静态页 + API 端点 (用 tools.highkingflower.com)"""
import urllib.request, urllib.error

HOST = "https://tools.highkingflower.com"
tests = [
    # (path, expected_status, label)
    ("/", 200, "首页"),
    ("/dashboard", 200, "仪表盘"),
    ("/sitemap.xml", 200, "sitemap"),
    ("/robots.txt", 200, "robots"),
    ("/paid.html", 200, "支付回跳"),
    ("/api/health", 200, "health"),
    ("/api/pay", 200, "pay"),
    ("/api/config", 200, "config"),
    ("/api/track", 200, "track"),
    ("/api/alert", 200, "alert"),
    ("/api/subwall", 200, "subwall"),
    ("/api/commission", 200, "commission"),
    ("/pay/cancel", 200, "pay/cancel"),
]
passed = 0
failed = []
for path, expected, label in tests:
    url = HOST + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "diag/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            ok = r.status == expected
            if ok:
                passed += 1
            print(f"  {'✅' if ok else '❌'} {label:10s} {path:25s} HTTP {r.status}")
    except urllib.error.HTTPError as e:
        ok = e.code == expected
        if ok:
            passed += 1
        print(f"  {'✅' if ok else '❌'} {label:10s} {path:25s} HTTP {e.code}")
    except Exception as e:
        print(f"  ❌ {label:10s} {path:25s} ERR {type(e).__name__}")
        failed.append(label)

print(f"\n=== {passed}/{passed+len(failed)} 通过 ===")
if failed:
    print(f"失败: {failed}")
