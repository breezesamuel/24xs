#!/usr/bin/env python3
"""验证新部署 f60awjt2d 的 /dashboard + IndexNow key"""
import urllib.request, urllib.error

HOST = "https://tools.highkingflower.com"
tests = [
    ("/dashboard", 200, "仪表盘"),
    ("/eba1648ac2e72921f694b451970d59d9.txt", 200, "IndexNow key"),
    ("/", 200, "首页"),
    ("/api/health", 200, "health"),
]
for path, expected, label in tests:
    url = HOST + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "diag/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"  {'✅' if r.status == expected else '❌'} {label:10s} {path:40s} HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"  {'✅' if e.code == expected else '❌'} {label:10s} {path:40s} HTTP {e.code}")
    except Exception as e:
        print(f"  ❌ {label:10s} {path:40s} ERR {type(e).__name__}")
