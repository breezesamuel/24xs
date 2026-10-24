# -*- coding: utf-8 -*-
"""订阅墙 / 收款注册的真实状态核查。

只回答三个问题，不做任何猜测：
  1. 官网首页到底有没有订阅墙（付费墙）？用户能不能真的走到"付钱"这一步？
  2. 收款 webhook 线上是通还是不通？通了的话有没有配置签名密钥？
  3. 官方文档里要求的 KYC / 产品 / 提现账户，我们这边有没有？
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"F:\2026\24xs\07_运维")))
sys.stdout.reconfigure(encoding="utf-8")

from deploy_site import _opener  # noqa: E402  复用同一个代理出口

ROOT = Path(r"F:\2026\24xs")
SITE = ROOT / "10_官网" / "index.html"
URL = "https://geo-audit-24xs.vercel.app"
HOOK = URL + "/api/webhook/moltspay"

SECRET_VARS = ("MOLTSPAY_WEBHOOK_SECRET", "MOLTSPAY_SIGNING_SECRET",
               "MOLTSPAY_API_KEY", "X402_SECRET")

# 订阅墙/付费入口应该出现的信号
PAY_SIGNALS = {
    "订阅套餐/价格表": (r"¥\s?\d[\d,]{2,}", r"套餐", r"订阅", r"会员价", r"pricing"),
    "支付按钮": (r"立即支付", r"去支付", r"购买", r"checkout", r"支付"),
    "收款二维码/付款信息": (r"二维码", r"支付宝", r"微信支付", r"对公账户", r"收款"),
    "MoltsPay/x402 接入": (r"moltspay", r"x402", r"MOLTSPAY"),
    "服务条款/退款政策": (r"服务条款", r"退款", r"隐私政策", r"terms"),
}


def get(url: str, timeout: int = 30) -> tuple[int, str]:
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _opener().open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        code = getattr(e, "code", None)
        return code or 0, f"<{type(e).__name__}: {e}>"


print("=" * 78)
print("  1. 官网首页有没有订阅墙")
print("=" * 78)
html = SITE.read_text(encoding="utf-8")
for name, pats in PAY_SIGNALS.items():
    hit = [p for p in pats if re.search(p, html, re.I)]
    mark = "有" if hit else "无"
    print(f"  {name:<22} {mark}   {hit[:3] if hit else ''}")

print()
print("=" * 78)
print("  2. 线上 webhook 状态")
print("=" * 78)
code, body = get(HOOK)
print(f"  {HOOK}")
print(f"  -> HTTP {code}")
snippet = re.sub(r"\s+", " ", body)[:200]
print(f"  -> {snippet}")

print()
print("=" * 78)
print("  3. 收款凭据是否就位（只看本机有没有，不打印任何密钥内容）")
print("=" * 78)
found = [v for v in SECRET_VARS if os.environ.get(v)]
if found:
    for v in found:
        print(f"  [有] {v}")
else:
    print("  [无] 下列环境变量全部未设置：")
    for v in SECRET_VARS:
        print(f"       - {v}")

# 本地 .env / 配置文件里是否硬写了密钥
env_files = list(ROOT.rglob(".env*")) + list(ROOT.rglob("*.env"))
leaks = []
for ef in env_files:
    try:
        t = ef.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for v in SECRET_VARS:
        for line in t.splitlines():
            if line.strip().startswith(v) and len(line.split("=", 1)[-1].strip()) > 8:
                leaks.append(f"{ef} -> {v}")
print()
if leaks:
    print("  [警告] 配置文件里存在已填写的凭据：")
    for x in leaks:
        print(f"       {x}")
else:
    print("  [OK] 配置文件里没有已填写的收款凭据（即尚未注册的现状）")

print()
print("=" * 78)
verdict = []
verdict.append(("官网订阅墙", any(
    re.search(p, html, re.I) for p in PAY_SIGNALS["支付按钮"])))
verdict.append(("线上 webhook 放行", code == 200))
verdict.append(("签名密钥已配置", bool(found)))
for n, v in verdict:
    print(f"  {n:<20} {'已完成' if v else '未完成'}")
print("=" * 78)
