# -*- coding: utf-8 -*-
"""支付宝网关（Vercel 运行时版）。

设计要点
--------
1) 凭据只从**环境变量**读，绝不写进仓库、绝不返回给浏览器。
2) 回调**不直接采信**。收到通知后用我方私钥签名去问支付宝
   `alipay.trade.query`，以支付宝的应答为准 —— 这样即便我方还没配置
   支付宝公钥（无法验回调签名），也不会被伪造回调骗发货。
3) 应付金额**编进 out_trade_no**。服务端无持久数据库，靠这个在回调时
   还原"这单应该收多少"，再和支付宝应答的金额比对，防止 ¥0.01 买 ¥500。
   out_trade_no 由我方签名下发，支付宝原样回传，不可篡改。
4) 没有支付宝公钥时降级为"仅主动查询验证"，并记录告警，不静默放行。
"""
import base64
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal

GATEWAY = "https://openapi.alipay.com/gateway.do"
TZ = timezone(timedelta(hours=8))
# R = 一次性报告（不是订阅）。它是获客入口的单次付费，
# 必须能编进单号，这样无库校验金额时报告单同样能验。
PLAN_CODE = {"month": "M", "quarter": "Q", "year": "Y", "report": "R"}
CODE_PLAN = {v: k for k, v in PLAN_CODE.items()}


class AlipayNotConfigured(Exception):
    pass


def cfg() -> dict:
    app_id = os.environ.get("ALIPAY_APP_ID", "").strip()
    priv = os.environ.get("ALIPAY_PRIVATE_KEY", "").strip()
    if not app_id or not priv:
        raise AlipayNotConfigured("缺少 ALIPAY_APP_ID / ALIPAY_PRIVATE_KEY")
    return {
        "app_id": app_id,
        "private_key": _to_pem(priv, "PRIVATE KEY"),
        "public_key": _to_pem(os.environ.get("ALIPAY_PUBLIC_KEY", ""),
                              "PUBLIC KEY"),
        "seller_id": os.environ.get("ALIPAY_SELLER_ID", "").strip(),
        "notify_url": os.environ.get("ALIPAY_NOTIFY_URL", "").strip(),
        "return_url": os.environ.get("ALIPAY_RETURN_URL", "").strip(),
    }


def _which(exe: str):
    from shutil import which
    return which(exe)


def _to_pem(raw: str, kind: str) -> str:
    """把 base64 裸串或 PEM 文本统一成 PEM。"""
    raw = raw.replace("\\n", "\n").strip()
    if raw.startswith("-----BEGIN"):
        return raw
    b = "".join(raw.split())
    if not b:
        return ""
    der = base64.b64decode(b + "=" * (-len(b) % 4))
    b64 = base64.b64encode(der).decode()
    lines = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    return f"-----BEGIN {kind}-----\n{lines}\n-----END {kind}-----\n"


def _rsa_key(pem: str):
    from Crypto.PublicKey import RSA
    return RSA.import_key(pem)


def sign_str(params: dict) -> str:
    """支付宝【请求】签名原文：按 key 升序，只排除 sign 和空值。

    注意：sign_type 必须参与签名。支付宝签名失败时会把期望的待签名串原样
    回显，实测其中含 sign_type=RSA2。早期版本这里把 sign_type 也排除了，
    结果收银台直接 invalid-signature，链接根本收不了款。
    """
    items = sorted((k, str(v)) for k, v in params.items()
                   if k != "sign" and v not in (None, ""))
    return "&".join(f"{k}={v}" for k, v in items)


def notify_str(params: dict) -> str:
    """支付宝【异步通知】验签原文：官方文档要求连 sign_type 一起排除。"""
    items = sorted((k, str(v)) for k, v in params.items()
                   if k not in ("sign", "sign_type") and v not in (None, ""))
    return "&".join(f"{k}={v}" for k, v in items)


def verify_response(resp: dict, sign_b64: str, public_pem: str) -> bool:
    """校验支付宝【接口应答】的签名。

    实测结论（本地拿真实应答逐种试出来的，不是照文档猜的）：
      1. 支付宝签的是**业务应答字段**（形如 xxx_response）的紧凑 JSON，
         不是整个报文，也不是拍平后的 key=value 串；
      2. 应答正文实际是 **GB18030** 编码，任何 decode/re-encode 的差异
         都会让验签失败，所以这里按 utf-8 / gb18030 依次尝试原始编码。
    早期版本按"顶层拍平 + 排除 sign"验，结果永远失败，
    于是误判成"没有支付宝公钥"，白白丢掉了响应验签这一层。
    """
    if not sign_b64 or not public_pem:
        return False
    body = None
    for k, v in resp.items():
        if k.endswith("_response") and isinstance(v, dict):
            body = v
            break
    if body is None:
        return False
    # 应答正文是紧凑 JSON，且可能是 GB18030。两种编码都试原始字节。
    txt = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    sig = base64.b64decode(sign_b64)
    return any(_rsa("verify", public_pem, txt.encode(enc), sig) is True
               for enc in ("utf-8", "gb18030"))


def _rsa(op: str, pem: str, data: bytes, sig: bytes = None):
    """RSA-SHA256 签/验。主路径 pycryptodome，缺失时退回 openssl CLI。

    为什么要兜底：目标机（用户国内阿里云）不一定能 pip install，
    装不上依赖 == 收不到钱。openssl 是 Linux 标配，所以兜底它。
    主路径仍是已充分测试的 pycryptodome，不动它。
    返回值：sign -> 签名字节；verify -> True/False。sign 失败返回 None。
    """
    try:
        from Crypto.Hash import SHA256
        from Crypto.Signature import pkcs1_15
        k = _rsa_key(pem)
        if op == "sign":
            return pkcs1_15.new(k).sign(SHA256.new(data))
        try:
            pkcs1_15.new(k).verify(SHA256.new(data), sig)
            return True
        except Exception:
            return False
    except ImportError:
        pass

    import subprocess
    import tempfile

    # openssl 不一定在 PATH（Windows 上尤其常见），按常见位置找一下。
    exe = "openssl"
    if not _which(exe):
        for c in (r"C:\Program Files\Git\usr\bin\openssl.exe",
                  r"C:\Program Files\Git\mingw64\bin\openssl.exe",
                  "/usr/bin/openssl", "/usr/local/bin/openssl",
                  "/opt/homebrew/bin/openssl"):
            if os.path.exists(c):
                exe = c
                break
    d = tempfile.mkdtemp(prefix="alipay_")
    kf, df = os.path.join(d, "k.pem"), os.path.join(d, "d.bin")
    # 密钥可能是裸 base64（支付宝后台下载的就是那种），先规整成 PEM。
    # 公钥用 PKCS#1 的 "RSA PUBLIC KEY"，openssl -verify 认这个格式。
    kind = "RSA PRIVATE KEY" if op == "sign" else "RSA PUBLIC KEY"
    with open(kf, "w", encoding="utf-8") as f:
        f.write(_to_pem(pem, kind))
    with open(df, "wb") as f:
        f.write(data)
    try:
        if op == "sign":
            p = subprocess.run([exe, "dgst", "-sha256", "-sign", kf, df],
                               capture_output=True)
            return p.stdout if p.returncode == 0 else None
        sf = os.path.join(d, "d.sig")
        with open(sf, "wb") as f:
            f.write(sig)
        p = subprocess.run([exe, "dgst", "-sha256", "-verify", kf,
                            "-signature", sf, df], capture_output=True)
        return p.returncode == 0
    except Exception:
        return None if op == "sign" else False


def sign(params: dict, private_pem: str) -> str:
    sig = _rsa("sign", private_pem, sign_str(params).encode())
    if sig is None:
        raise RuntimeError("RSA 签名失败：pycryptodome 与 openssl 都不可用")
    return base64.b64encode(sig).decode()


def verify(params: dict, sign_b64: str, public_pem: str) -> bool:
    """验签（通知语义）。任何异常都算失败，不放行。"""
    if not sign_b64 or not public_pem:
        return False
    try:
        return _rsa("verify", public_pem,
                    notify_str(params).encode(),
                    base64.b64decode(sign_b64)) is True
    except Exception:
        return False


def build_order_no(plan: str, cents: int) -> str:
    """G1-时间戳-随机-金额(分)-套餐码；金额编在单号里以便无库校验。"""
    rnd = base64.b32encode(os.urandom(4)).decode().strip("=")[:6]
    ts = datetime.now(TZ).strftime("%Y%m%d%H%M%S")
    return f"G1-{ts}-{rnd}-{cents}-{PLAN_CODE[plan]}"


def parse_order_no(no: str):
    """还原 (套餐, 分)。格式不符返回 None。"""
    m = re.fullmatch(r"G1-\d{14}-([A-Z2-7]{4,8})-(\d{3,8})-([MQYR])", no or "")
    if not m:
        return None
    cents = int(m.group(2))
    return CODE_PLAN[m.group(3)], cents


def _common(method: str, biz: dict, c: dict) -> dict:
    p = {
        "app_id": c["app_id"],
        "method": method,
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": json.dumps(biz, separators=(",", ":"), ensure_ascii=False),
    }
    p["sign"] = sign(p, c["private_key"])
    return p


def _post(p: dict, timeout: int = 20) -> dict:
    req = urllib.request.Request(
        GATEWAY, data=urllib.parse.urlencode(p).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    txt = next(raw.decode(e) for e in ("utf-8", "gb18030", "latin-1")
               if _ok(raw, e))
    return json.loads(txt)


def _ok(raw: bytes, enc: str) -> bool:
    try:
        raw.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def page_pay_url(plan: str, cents: int, subject: str, lang: str = "cn") -> str:
    """生成电脑网站支付跳转链接（不扣款，仅跳转）。"""
    c = cfg()
    no = build_order_no(plan, cents)
    biz = {
        "out_trade_no": no,
        "total_amount": f"{cents / 100:.2f}",
        "subject": subject[:256],
        "product_code": "FAST_INSTANT_TRADE_PAY",
    }
    if c["notify_url"]:
        biz["notify_url"] = c["notify_url"]
    if c["return_url"]:
        biz["return_url"] = c["return_url"]
    p = _common("alipay.trade.page.pay", biz, c)
    return no, f"{GATEWAY}?{urllib.parse.urlencode(p, quote_via=urllib.parse.quote_plus)}"


def query_trade(out_trade_no: str) -> dict | None:
    """向支付宝查询订单真相。返回 None 表示查不到/失败（不可发货）。"""
    try:
        c = cfg()
        r = _post(_common("alipay.trade.query", {"out_trade_no": out_trade_no}, c))
    except Exception:
        return None
    body = r.get("alipay_trade_query_response") or {}
    if body.get("code") != "10000":
        return None
    # 现在支付宝公钥已配置，因此必须验签、且验签不过即拒（fail-closed）。
    # 可靠性来源：HTTPS + 我方请求签名 + 支付宝应答验签。
    if r.get("sign"):
        if not c["public_key"]:
            return None
        if not verify_response(r, r["sign"], c["public_key"]):
            return None
    return body


def money(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(Decimal("0.01"))