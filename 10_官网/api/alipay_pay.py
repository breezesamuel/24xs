# -*- coding: utf-8 -*-
"""POST /api/alipay_pay  —— 生成支付宝支付跳转链接。

只生成链接，不扣款。返回给浏览器的只有 order_id 和 pay_url。
"""
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alipay_lib as A  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "_paylib"))

_RATE: dict[str, list[float]] = {}
MAX_BODY = 4_000

PERIODS = ("month", "quarter", "year", "report")
# 价格单一来源：读 _paylib/subscription.py（由 deploy_site.sync_paylib 从
# 01_引擎 同步）。原来这里硬编码一份，改价只改一处必然漏掉。
try:
    import subscription as _S
    PRICE_CENTS = {p: int(round(v["price"] * 100))
                    for p, v in _S.PLANS["cn"]["plans"].items()}
    SUBJECT = {p: f"GEO 自动快检 · {v['label']}订阅"
               for p, v in _S.PLANS["cn"]["plans"].items()}
    PRICE_CENTS.update({k: int(v["price_cny"] * 100)
                        for k, v in _S.ONE_OFF.items()})
    SUBJECT.update({k: v["subject"] for k, v in _S.ONE_OFF.items()})
except Exception as e:  # 同步缺失时要响亮失败，不能静默用错价格
    raise RuntimeError(f"价格配置加载失败: {e}")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def limiter(ip: str):
    now = time.time()
    hits = [t for t in _RATE.get(ip, []) if now - t < 3600]
    if len(hits) >= 10:
        return None
    hits.append(now)
    _RATE[ip] = hits
    return True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, obj: dict):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(405, {"ok": False, "error": "只支持 POST"})

    def do_POST(self):
        if not limiter(self.client_address[0]):
            return self._send(429, {"ok": False, "error": "请求过于频繁"})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._send(400, {"ok": False, "error": "请求大小不合法"})
        try:
            d = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return self._send(400, {"ok": False, "error": "JSON 解析失败"})
        if not isinstance(d, dict):
            return self._send(400, {"ok": False, "error": "参数格式错误"})

        plan = str(d.get("plan", ""))[:16]
        email = str(d.get("email", "")).strip().lower()[:120]
        lang = "en" if str(d.get("lang", ""))[:2] == "en" else "cn"
        ref = str(d.get("ref", "")).strip()[:32]
        if plan not in PERIODS:
            return self._send(400, {"ok": False, "error": "套餐不存在"})
        if not EMAIL_RE.match(email):
            return self._send(400, {"ok": False, "error": "邮箱格式不正确"})

        try:
            cents = PRICE_CENTS[plan]
            no, url = A.page_pay_url(plan, cents, SUBJECT[plan], lang)
        except A.AlipayNotConfigured as e:
            sys.stderr.write(f"[ALIPAY-CONFIG] {e}\n")
            return self._send(503, {"ok": False, "error": "支付通道未配置"})
        except Exception as e:
            sys.stderr.write(f"[ALIPAY-ERR] {type(e).__name__}: {e}\n")
            return self._send(502, {"ok": False, "error": "支付通道暂时不可用"})

        sys.stdout.write(
            f"[ALIPAY-ORDER] no={no} plan={plan} cents={cents} lang={lang} "
            f"ref={ref or '-'} email={email} host={self.headers.get('Host','-')}\n")
        sys.stdout.flush()
        self._send(200, {"ok": True, "order_id": no, "pay_url": url,
                         "amount": f"{cents/100:.2f}", "currency": "CNY"})


handler = Handler