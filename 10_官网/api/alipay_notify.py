# -*- coding: utf-8 -*-
"""POST /api/alipay_notify  —— 支付宝异步通知。

**不采信回调内容。** 流程：
  1. 只从回调里取出 out_trade_no；
  2. 用我方私钥签名，反向调 alipay.trade.query 问支付宝真相；
  3. 以支付宝应答里的 trade_status / total_amount 为准，
     再和我方编进单号的应付金额比对；
  4. 一致才落一条 [ALIPAY-PAID] 记录（供 sub_admin import-paid 开额度）。

这样即使回调被伪造，或我方尚未配置支付宝公钥，也不会白发货。
"""
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alipay_lib as A  # noqa: E402

OK_STATUS = ("TRADE_SUCCESS", "TRADE_FINISHED")


def check(out_trade_no: str) -> tuple[bool, str]:
    parsed = A.parse_order_no(out_trade_no)
    if not parsed:
        return False, "单号格式不认识"
    plan, cents = parsed

    truth = A.query_trade(out_trade_no)
    if truth is None:
        return False, "支付宝查不到该订单或查询失败"
    if truth.get("trade_status") not in OK_STATUS:
        return False, f"状态为 {truth.get('trade_status')}"
    try:
        got = A.money(int(round(float(truth["total_amount"]) * 100)))
    except (KeyError, ValueError, TypeError):
        return False, "应答缺少金额"
    if got != A.money(cents):
        return False, f"金额不符 实收 {got} 应收 {A.money(cents)}"
    return True, f"{plan} {A.money(cents)} trade_no={truth.get('trade_no','')}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _text(self, code: int, msg: str):
        b = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._text(405, "fail")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 20_000:
            return self._text(400, "fail")
        raw = self.rfile.read(n).decode("utf-8", "replace")
        form = {k: v[0] for k, v in
                urllib.parse.parse_qs(raw, keep_blank_values=True).items()}

        # 支付宝公钥若已配置则一并验签；未配置不阻断，
        # 因为下面的主动查询才是最终判定依据。
        try:
            pub = A.cfg().get("public_key") or ""
        except Exception:
            pub = ""
        if pub and not A.verify({k: v for k, v in form.items()
                                 if k not in ("sign", "sign_type")},
                                form.get("sign", ""), pub):
            sys.stderr.write("[ALIPAY-NOTIFY-REJECT] 回调验签失败\n")
            return self._text(200, "failure")

        no = form.get("out_trade_no", "")
        ok, why = check(no)
        if not ok:
            sys.stderr.write(f"[ALIPAY-NOTIFY-REJECT] no={no} 原因={why}\n")
            sys.stdout.write(f"[ALIPAY-REJECT] no={no} reason={why}\n")
            sys.stdout.flush()
            return self._text(200, "failure")

        sys.stdout.write(f"[ALIPAY-PAID] no={no} detail={why}\n")
        sys.stdout.flush()
        self._text(200, "success")


handler = Handler