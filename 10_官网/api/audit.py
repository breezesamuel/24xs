# -*- coding: utf-8 -*-
"""免费 AI 可见度体检接口（官网自用入口）。

安全约束：
  - 只接受被检测站点的 URL，不接受任意抓取代理参数，避免变成 SSRF 跳板
  - 禁止内网/环回/元数据地址
  - 同 IP 每小时限次，防止被人当免费工具刷
  - 免费结果只回分数与结论；完整整改清单是 ¥99 付费内容，不在响应里
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

BOT = "Mozilla/5.0 (compatible; GEOAuditBot/1.0)"

AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Bytespider",
           "Baiduspider", "Google-Extended"]
_RATE: dict[str, list[float]] = {}
MAX_PER_HOUR = 12


def _decode(raw: bytes) -> str:
    for e in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(e)
        except Exception:
            continue
    return ""


def _public_host(url: str) -> tuple[bool, str]:
    """只允许公网 http(s)。挡内网、环回、云元数据地址。"""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return False, "网址格式不对"
    if not host:
        return False, "网址格式不对"
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False, "域名解析不了，检查一下网址"
    for info in infos:
        ip = info[4][0]
        try:
            a = ipaddress.ip_address(ip)
        except Exception:
            return False, "网址里的 IP 无法识别"
        if (a.is_private or a.is_loopback or a.is_link_local
                or a.is_reserved or a.is_multicast):
            return False, "只支持公网网址"
    return True, ""


def _get(url: str, timeout: int = 18) -> tuple[int, bytes]:
    uas = [BOT,
           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"]
    ref = urllib.parse.urlparse(url)
    last = (0, b"")
    for ua in uas:
        req = urllib.request.Request(url, headers={
            "User-Agent": ua,
            "Accept": "text/html,*/*;q=0.8",
            "Referer": f"{ref.scheme}://{ref.netloc}/"})
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
            b = r.read(300_000)
            if r.status == 200 and b:
                return r.status, b
            last = (r.status, b)
        except Exception:
            pass
    return last


def _nodes(o) -> list:
    """展开 JSON-LD 里的所有实体。

    必须处理 @graph：那是 Google 推荐的写法（一个 @context 下挂多个实体），
    顶层对象只有 @context/@graph、没有 @type。之前按"顶层字典"解析，
    于是所有用 @graph 的站都被误判成"完全没有结构化数据" —— 这是会让
    客户白花钱整改的假阴性，必须认。
    """
    if isinstance(o, list):
        return [x for x in o if isinstance(x, dict)]
    if isinstance(o, dict):
        g = o.get("@graph")
        if isinstance(g, list):
            return [x for x in g if isinstance(x, dict)]
        return [o]
    return []


def audit(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        url = "http://" + url.strip()
    ok, why = _public_host(url)
    if not ok:
        raise ValueError(why)
    root = urllib.parse.urlparse(url)
    base = f"{root.scheme}://{root.netloc}"

    st, rb = _get(base + "/robots.txt")
    robots = _decode(rb) if st == 200 else ""
    blocked = []
    if robots:
        for bot in AI_BOTS:
            m = re.search(
                rf"(?im)^user-agent:\s*{re.escape(bot)}\s*$([\s\S]*?)(?=^\s*user-agent:|\Z)",
                robots)
            if m and any(d.strip() in ("/", "")
                         for d in re.findall(r"(?im)^\s*disallow:\s*(\S*)", m.group(1))):
                blocked.append(bot)

    hc, hb = _get(url)
    html = _decode(hb) if hc == 200 else ""
    reachable = hc == 200 and len(hb) > 200

    types = []
    for m in re.finditer(
            r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html):
        try:
            o = json.loads(m.group(1).strip())
        except Exception:
            continue
        for x in _nodes(o):
            t = x.get("@type")
            if t:
                types.extend(t if isinstance(t, list) else [t])
    types = sorted(set(str(t) for t in types))
    has_org = any(k in "".join(types) for k in
                  ("Organization", "LocalBusiness", "MedicalBusiness", "Store"))
    has_faq = "FAQ" in "".join(types)
    faq_block = bool(re.search(r"(?i)(FAQ|常见问题|问答|Q&A)", html))
    has_desc = bool(re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'][^"\']+', html))
    lc, lb = _get(base + "/llms.txt")
    has_llms = lc == 200 and len(lb) > 30
    sc, _ = _get(base + "/sitemap.xml")
    has_sm = sc == 200

    out = {
        "host": root.netloc, "reachable": reachable, "http": hc,
        "blocked_bots": blocked, "schema": types, "has_org": has_org,
        "has_faq": has_faq or faq_block, "has_llms": has_llms,
        "has_desc": has_desc, "has_sitemap": has_sm,
    }
    if not reachable:
        out.update(score=0, grade="无法访问",
                   blockers=[f"官网当前无法正常访问（HTTP {hc}），AI 同样抓不到。"
                             "这不是 GEO 问题，站点先恢复可达再说。"])
        return out

    score = 0
    why: list[str] = []
    # 关键：robots.txt 缺失 ≠ 拦截 AI 爬虫。只有真出现 Disallow: / 才算被拦。
    if blocked:
        why.append("robots.txt 拦截了 AI 爬虫：" + "、".join(blocked))
    elif st == 200:
        score += 30
    else:
        score += 18
        why.append("没有 robots.txt，未明确放行 AI 爬虫")
    if has_org:
        score += 25
    elif types:
        score += 12
        why.append("有结构化数据，但没有实体声明（Organization/LocalBusiness）")
    else:
        why.append("没有 JSON-LD 结构化数据，AI 读到你却认不出你是谁")
    if out["has_faq"]:
        score += 15
    else:
        why.append("没有 FAQ/问答区块，AI 无从抽取问答对")
    if has_llms:
        score += 10
    else:
        why.append("没有 llms.txt（给大模型的站点说明书）")
    if has_desc:
        score += 10
    else:
        why.append("缺少 meta description")
    if has_sm:
        score += 10
    else:
        why.append("没有 sitemap.xml")
    out.update(score=min(score, 100),
               grade=("优" if score >= 80 else "中" if score >= 55 else "差"),
               blockers=why)
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _limited(self) -> bool:
        ip = self.client_address[0]
        now = time.time()
        hit = [t for t in _RATE.get(ip, []) if now - t < 3600]
        if len(hit) >= MAX_PER_HOUR:
            _RATE[ip] = hit
            return True
        hit.append(now)
        _RATE[ip] = hit
        return False

    def do_POST(self):  # noqa: N802
        if not self.path.endswith("/audit"):
            self._send(404, {"error": "not found"})
            return
        if self._limited():
            self._send(429, {"error": "今天测得有点多，明天再来或联系我们"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(_decode(self.rfile.read(min(n, 4096))) or "{}")
        except Exception:
            self._send(400, {"error": "请求格式不对"})
            return
        url = str(data.get("url") or "").strip()
        if not url or len(url) > 300:
            self._send(400, {"error": "请填官网网址"})
            return
        try:
            r = audit(url)
        except ValueError as e:
            self._send(400, {"error": str(e)})
            return
        except Exception:
            self._send(502, {"error": "检测超时，请稍后再试"})
            return
        # 免费层：分数与结论。整改方案不在这里。
        self._send(200, r)

    def log_message(self, *a):  # 静音
        pass


handler = Handler