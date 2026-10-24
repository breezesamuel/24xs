# -*- coding: utf-8 -*-
"""把 Vercel 函数形态的 Handler 复用到一台自有的国内服务器。

为什么需要这个：
  *.vercel.app 在中国大陆被 DNS 污染 + IP 封锁，官网打不开，
  更糟的是**支付宝的异步通知也打不进来** —— 付了钱系统永远收不到确认。
  所以收款链路必须放在国内。本机跑这个服务，前面挂 nginx。

为什么用"转发"而不是重写：
  api/*.py 里那套 Handler 已经被 77 条断言验证过（签名、金额校验、
  SSRF、限流、幂等）。重写等于把已验证的东西推倒重来。
  这里只做一个薄路由器：按 path 把请求转给对应模块的 Handler.do_POST，
  业务逻辑一行都不动。

路由：
  POST /api/audit         -> api.audit.Handler
  POST /api/alipay_pay    -> api.alipay_pay.Handler
  POST /api/alipay_notify -> api.alipay_notify.Handler
  POST /api/order         -> api.order.Handler
  GET  /*                 -> 静态文件（10_官网 目录）
"""
from __future__ import annotations

import importlib
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE.parent                      # 10_官网
sys.path.insert(0, str(WEB))
sys.path.insert(0, str(WEB / "api"))

ROUTES = {
    "/api/audit": "audit",
    "/api/alipay_pay": "alipay_pay",
    "/api/alipay_notify": "alipay_notify",
    "/api/order": "order",
}
_CACHE: dict[str, object] = {}


def _mod(name: str):
    if name not in _CACHE:
        _CACHE[name] = importlib.import_module(name)
    return _CACHE[name]


MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}


class Router(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "geoaudit/1.0"

    # 四个 Handler 各自的 _send 逻辑一样，这里提供一份给它们复用。
    def _send(self, code: int, obj: dict) -> None:
        import json
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- 静态 ----
    def do_GET(self):
        p = self.path.split("?", 1)[0]
        if p in ("/", ""):
            p = "/index.html"
        # 目录穿越防护：解析后必须仍在 WEB 内
        try:
            target = (WEB / p.lstrip("/")).resolve()
            target.relative_to(WEB.resolve())
        except Exception:
            self._send(403, {"error": "forbidden"})
            return
        if not target.is_file():
            # 无扩展名时当 SPA/短链再试一次加 .html
            alt = target.with_suffix(".html")
            target = alt if alt.is_file() else target
        if not target.is_file():
            self._send(404, {"error": "not found"})
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type",
                         MIME.get(target.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    # ---- API：转交给已验证的模块 Handler ----
    def do_POST(self):
        p = self.path.split("?", 1)[0]
        name = ROUTES.get(p)
        if not name:
            self._send(404, {"error": "not found"})
            return
        try:
            m = _mod(name)
        except Exception as e:
            self._send(500, {"error": f"模块加载失败: {e}"})
            return
        # 关键：各 Handler 依赖自己类里的辅助方法（限流 _limited、_rate 等）。
        # 只转发 do_POST 而不把这些方法挂过来，运行期才会炸 —— 而且是
        # "本地测试全过、线上 AttributeError" 这种最难查的形态。
        for attr, val in vars(m.Handler).items():
            if attr.startswith("__") or attr.startswith("do_"):
                continue
            if attr in ("_send",):
                continue          # 用 Router 自己的 _send
            if callable(val):
                self.__dict__[attr] = val.__get__(self, type(self))
            else:
                self.__dict__[attr] = val
        try:
            m.Handler.do_POST(self)          # 业务逻辑一行未改
        except Exception as e:
            # Handler 内部已各自处理业务异常；走到这说明是真崩了，
            # 必须让前端拿到 5xx 而不是挂起，否则页面一直转圈。
            import traceback
            self._send(500, {"error": f"服务异常: {type(e).__name__}: {e}"})
            traceback.print_exc()

    def log_message(self, fmt, *args):
        if os.environ.get("GEO_VERBOSE"):
            sys.stderr.write("%s - %s\n" % (self.client_address[0], fmt % args))


def main():
    host = os.environ.get("GEO_HOST", "127.0.0.1")
    port = int(os.environ.get("GEO_PORT", "8800"))
    srv = ThreadingHTTPServer((host, port), Router)
    srv.daemon_threads = True
    sys.stderr.write(f"[geoaudit] listening on {host}:{port}  web={WEB}\n")
    sys.stderr.flush()
    srv.serve_forever()


if __name__ == "__main__":
    main()