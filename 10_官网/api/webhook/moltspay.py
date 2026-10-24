import hmac
import hashlib
import json
import os
import sys
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler

SECRET = os.environ.get("MOLTSPAY_WEBHOOK_SECRET", "").strip()
TOLERANCE_S = 300
_seen = OrderedDict()
_SEEN_MAX = 512


def verify(raw: bytes, signature: str, timestamp: str, secret: str) -> bool:
    payload = f"{timestamp}.{raw.decode('utf-8', 'replace')}".encode()
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def already_seen(event_id: str) -> bool:
    now = time.time()
    for k in list(_seen):
        if now - _seen[k] > TOLERANCE_S:
            del _seen[k]
    if event_id in _seen:
        return True
    _seen[event_id] = now
    while len(_seen) > _SEEN_MAX:
        _seen.popitem(last=False)
    return False


class handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _reply(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not SECRET:
            return self._reply(503, b"MOLTSPAY_WEBHOOK_SECRET not configured")
        self._reply(200, b"ok")

    def do_POST(self):
        if not SECRET:
            return self._reply(503, b"MOLTSPAY_WEBHOOK_SECRET not configured")

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self._reply(400, b"bad content-length")
        if length <= 0 or length > 65536:
            return self._reply(400, b"bad content-length")

        raw = self.rfile.read(length)
        signature = self.headers.get("X-X402-Signature", "")
        timestamp = self.headers.get("X-X402-Timestamp", "")

        if not signature or not timestamp:
            return self._reply(400, b"missing signature headers")
        try:
            age = abs(time.time() - int(timestamp))
        except ValueError:
            return self._reply(400, b"bad timestamp")
        if age > TOLERANCE_S:
            return self._reply(400, b"timestamp outside tolerance")

        if not verify(raw, signature, timestamp, SECRET):
            return self._reply(401, b"invalid signature")

        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            return self._reply(400, b"invalid json")

        event_id = str(event.get("id", ""))
        if event_id and already_seen(event_id):
            return self._reply(200, b"duplicate")

        if event.get("event") == "payment.succeeded":
            d = event.get("data") or {}
            sys.stdout.write(
                "[PAID] id=%s slug=%s amount=%s %s tx=%s network=%s status=%s\n"
                % (
                    event_id,
                    d.get("source_slug"),
                    d.get("amount"),
                    d.get("currency"),
                    d.get("tx_hash"),
                    d.get("network"),
                    d.get("status"),
                )
            )
            sys.stdout.flush()

        self._reply(200, b"ok")
