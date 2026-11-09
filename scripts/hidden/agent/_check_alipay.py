#!/usr/bin/env python3
"""检查支付宝收款状态: /api/health env + /api/pay 建单"""
import urllib.request, urllib.error, json

HOST = "https://tools.highkingflower.com"

# 1. /api/health 查支付宝凭据就绪状态
print("=== /api/health 支付宝凭据状态 ===")
try:
    req = urllib.request.Request(HOST + "/api/health", headers={"User-Agent": "diag"})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.loads(r.read().decode("utf-8", "replace"))
        print(json.dumps(j, ensure_ascii=False, indent=2))
except urllib.error.HTTPError as e:
    body = (e.read() or b"").decode("utf-8", "replace")
    print(f"HTTP {e.code}: {body[:300]}")
except Exception as e:
    print(f"ERR {type(e).__name__}: {e}")

# 2. /api/pay 尝试真实建单（看支付宝签名是否可用）
print("\n=== /api/pay 建单测试 (plan=trial) ===")
try:
    payload = json.dumps({"plan": "trial", "ref": "alipay_diag_1"}).encode()
    req = urllib.request.Request(
        HOST + "/api/pay",
        data=payload,
        method="POST",
        headers={"User-Agent": "diag", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.loads(r.read().decode("utf-8", "replace"))
        print(json.dumps(j, ensure_ascii=False, indent=2)[:800])
except urllib.error.HTTPError as e:
    body = (e.read() or b"").decode("utf-8", "replace")
    print(f"HTTP {e.code}: {body[:400]}")
except Exception as e:
    print(f"ERR {type(e).__name__}: {e}")
