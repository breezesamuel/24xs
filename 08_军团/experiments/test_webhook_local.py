"""按官方规范验证 webhook 验签逻辑（本地，不打网络）。"""
import hashlib
import hmac
import importlib.util
import json
import os
import sys
import time
import types
from unittest import mock

sys.stdout.reconfigure(encoding="utf-8")

MOD = r"F:\2026\24xs\10_官网\api\webhook\moltspay.py"
SECRET = "test_secret_abc123"


def load(secret):
    with mock.patch.dict(os.environ, {"MOLTSPAY_WEBHOOK_SECRET": secret}):
        spec = importlib.util.spec_from_file_location("wh_%d" % int(time.time() * 1e6), MOD)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m


class FakeResp:
    def __init__(self):
        self.status = None
        self.headers = {}
        self.out = b""

    def send_response(self, c):
        self.status = c

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass

    def write(self, b):
        self.out += b


class FakeHandler:
    def __init__(self, module, body, sig, ts):
        self.rfile = __import__("io").BytesIO(body)
        self.headers = {}
        self.wfile = FakeResp()
        if sig is not None:
            self.headers["X-X402-Signature"] = sig
        if ts is not None:
            self.headers["X-X402-Timestamp"] = ts
        self.headers["Content-Length"] = str(len(body))
        self._m = module

    def send_response(self, code):
        self.wfile.status = code

    def send_header(self, k, v):
        self.wfile.headers[k] = v

    def end_headers(self):
        pass

    def log_request(self, *a, **k):
        pass

    def log_error(self, *a, **k):
        pass

    def __getattr__(self, k):
        attr = getattr(self._m.handler, k)
        if callable(attr):
            return types.MethodType(attr, self)
        return attr


def post(m, body: bytes, sig, ts):
    h = FakeHandler(m, body, sig, ts)
    m.handler.do_POST(h)
    return h.wfile.status


def sign(secret, ts, body):
    payload = f"{ts}.{body.decode()}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


EVENT = {
    "id": "evt_test_001",
    "event": "payment.succeeded",
    "timestamp": "2026-09-30T19:30:00Z",
    "data": {"source": "product", "source_slug": "geo-audit",
             "amount": "83.00", "currency": "USDC",
             "tx_hash": "0xdead", "network": "base", "status": "settled"},
}
BODY = json.dumps(EVENT).encode()
NOW = str(int(time.time()))

results = []
m = load(SECRET)

# 1 正确签名
ts = NOW
s = sign(SECRET, ts, BODY)
results.append(("正确签名 -> 200", post(m, BODY, s, ts) == 200))

# 2 同一事件重放（幂等）也返回 200
results.append(("重复事件 -> 200 且幂等", post(m, BODY, s, ts) == 200))

# 3 错误密钥签名
ts = NOW
bad = sign("wrong_secret", ts, BODY)
results.append(("错误密钥 -> 401", post(m, BODY, bad, ts) == 401))

# 4 篡改 body
ts = NOW
tampered = BODY.replace(b"83.00", b"1.00")
results.append(("篡改金额 -> 401", post(m, tampered, s, ts) == 401))

# 5 过期时间戳（重放攻击）
old = str(int(time.time()) - 4000)
oldsig = sign(SECRET, old, BODY)
results.append(("过期时间戳 -> 400", post(m, BODY, oldsig, old) == 400))

# 6 缺签名头
results.append(("缺签名头 -> 400", post(m, BODY, None, NOW) == 400))

# 7 空 body
results.append(("空 body -> 400", post(m, b"", sign(SECRET, NOW, b""), NOW) == 400))

# 8 未配置 secret 时 fail-closed
m2 = load("")
results.append(("未配置 secret -> 503", post(m2, BODY, "x", NOW) == 503))

# 9 verify() 直接对照官方 Python 片段
raw = BODY
sig = sign(SECRET, NOW, raw)
payload = f"{NOW}.{raw.decode()}".encode()
expected = hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()
results.append(("与官方示例算法一致", hmac.compare_digest(expected, sig)))

print("=" * 56)
ok = 0
for name, passed in results:
    print(("  PASS  " if passed else "  FAIL  ") + name)
    ok += bool(passed)
print("=" * 56)
print(f"{ok}/{len(results)} 通过")
sys.exit(0 if ok == len(results) else 1)
