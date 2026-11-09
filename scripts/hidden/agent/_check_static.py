#!/usr/bin/env python3
"""检查 mag0t3qw2 部署里静态页是否被部署"""
import urllib.request, urllib.error

HOST = "https://bingdashan-pain-tools-mag0t3qw2-solmount.vercel.app"
paths = [
    "/dashboard", "/dashboard.html", "/index.html", "/portal.html",
    "/pricing.html", "/api-docs.html", "/paid.html", "/robots.txt",
]
for p in paths:
    url = HOST + p
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "diag"})
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"{p:20s} HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"{p:20s} HTTP {e.code}")
    except Exception as e:
        print(f"{p:20s} ERR {type(e).__name__}: {str(e)[:60]}")
