#!/usr/bin/env python3
"""Vercel 主站 6 渠道是否已部署"""
import urllib.request, ssl
ctx = ssl.create_default_context()
for e in ['bounty?action=tasks','cashback?action=rate','writerewards?action=rate','charity?action=total','bandwidth?action=rate','config']:
    try:
        r = urllib.request.urlopen('https://tools.highkingflower.com/api/'+e, timeout=20, context=ctx)
        print(f"  {e:30s} HTTP {r.status}")
    except urllib.error.HTTPError as ex:
        print(f"  {e:30s} HTTP {ex.code} (未部署)")
    except Exception as ex:
        print(f"  {e:30s} ERR {type(ex).__name__}: {str(ex)[:40]}")
