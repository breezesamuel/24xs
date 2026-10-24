"""订阅开通申请接收端。

收款方式是「支付宝转账 + 人工确认开通」，所以这个接口**不碰钱**：
它只做一件事 —— 收下申请、生成申请编号、留痕，等人工核对到账。

为什么不接支付 API
------------------
个人支付宝账号拿不到程序化支付能力，也没有回调地址。要自动开通就得先办
支付宝开放平台（营业执照 + 法人认证 + RSA2 密钥）。在那之前，人工确认
反而更稳：不会出现"扣款成功但没开通"这种需要人工扯皮的对账事故。

留痕方式
--------
写到函数日志。用 `vercel logs` 捞出来，再由本机 sub_admin.py 落库。
服务端无状态，所以重启、换实例都不影响 —— 申请记录在日志里，不在内存里。
（别用内存 dict 存申请，实例一回收就没了。）

安全
----
- 只接受 POST，body 上限 4KB
- 邮箱严格校验，其余字段长度上限
- 任何输入都不回显到 HTML，只回申请编号
- 不打印任何凭据
"""
import json
import os
import re
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler

MAX_BODY = 4096
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s.]{1,63}\.[A-Za-z]{2,24}$")
SITE_RE = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{1,200}$")
VALID_PLANS = {"month", "quarter", "year"}
VALID_LANGS = {"cn", "en"}
# 单 IP 每小时最多 20 次申请，挡住脚本刷单
RATE_MAX = 20
RATE_WINDOW = 3600
_RATE: dict[str, list[float]] = {}

STARTED = time.time()


def _too_many(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _RATE.get(ip, []) if now - t < RATE_WINDOW]
    if len(hits) >= RATE_MAX:
        _RATE[ip] = hits
        return True
    hits.append(now)
    _RATE[ip] = hits
    return False


def clean(v, maxlen: int) -> str:
    """去掉控制字符并截断。回显前一律过这个。"""
    if not isinstance(v, str):
        return ""
    v = re.sub(r"[\x00-\x1f\x7f]", "", v).strip()
    return v[:maxlen]


def build_order_id() -> str:
    day = time.strftime("%Y%m%d")
    return f"GEO-{day}-{secrets.token_hex(3).upper()}"


class handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "geo-sub"

    def _reply(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *a):  # 别让默认日志把请求体也打出来
        return

    def do_GET(self):
        self._reply(405, {"error": "POST only"})

    def do_POST(self):
        ip = self.headers.get("X-Forwarded-For", "?").split(",")[0].strip()
        if _too_many(ip):
            return self._reply(429, {"error": "too many requests"})

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self._reply(400, {"error": "bad content-length"})
        if length <= 0 or length > MAX_BODY:
            return self._reply(413, {"error": "payload too large"})

        try:
            raw = self.rfile.read(length)
            data = json.loads(raw)
        except Exception:
            return self._reply(400, {"error": "invalid json"})
        if not isinstance(data, dict):
            return self._reply(400, {"error": "expected object"})

        email = clean(data.get("email"), 96)
        if not EMAIL_RE.match(email):
            return self._reply(400, {"error": "invalid email"})

        plan = clean(data.get("plan"), 16)
        if plan not in VALID_PLANS:
            return self._reply(400, {"error": "invalid plan"})

        lang = clean(data.get("lang"), 4) or "cn"
        if lang not in VALID_LANGS:
            lang = "cn"

        ref = clean(data.get("ref"), 32)
        site = clean(data.get("site"), 200)
        if site and not SITE_RE.match(site):
            return self._reply(400, {"error": "invalid site url"})

        oid = build_order_id()
        # 邮箱必须落全名：开通额度、发送报告都要靠它把订单对上人。
        # 这里只对**返回给浏览器**的内容做脱敏（只回编号），日志侧不脱敏，
        # 因为日志就是订单台账，脱敏了后台就没法发货。
        #
        # 由此产生的纪律：`vercel logs` 的输出属于敏感数据，不要贴进聊天、
        # 不要提交进仓库、不要外发。它只有项目所有者能看。
        sys.stdout.write(
            "[ORDER] id=%s plan=%s lang=%s ref=%s site=%s email=%s ua_host=%s\n"
            % (oid, plan, lang, ref or "-", site or "-", email,
               self.headers.get("Host", "-"))
        )
        sys.stdout.flush()

        self._reply(201, {"order_id": oid, "status": "pending_payment",
                          "pay_alipay": os.environ.get(
                              "SUB_PAY_ALIPAY", "supi24@163.com")})


if __name__ == "__main__":
    print("order endpoint; uptime=%.0fs" % (time.time() - STARTED))
