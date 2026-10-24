# -*- coding: utf-8 -*-
"""免费 GEO 体检引擎。

对外只给「免费结论 + 分数」，完整整改清单是 ¥99 付费解锁的内容。
这是敲门砖：让对方先看到自己官网在 AI 里的真实处境，再决定要不要改。

检测项（全部基于真实抓取，不臆测）：
  1. robots.txt 是否拦 GPTBot / ClaudeBot / PerplexityBot / Bytespider
  2. llms.txt 是否存在（给大模型的站点说明文件）
  3. JSON-LD 结构化数据：有没有、含哪些类型
  4. sitemap.xml 是否存在
  5. FAQ / Q&A 区块是否存在（AI 抽取问答对的依据）
  6. 标题与描述是否缺失
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; GEOAudit/1.0; +free-visibility-check)"

# AI 爬虫：拦了就等于在 AI 搜索里隐身
AI_BOTS = [
    ("GPTBot", "OpenAI 训练与检索"),
    ("ClaudeBot", "Anthropic Claude"),
    ("PerplexityBot", "Perplexity 搜索"),
    ("Bytespider", "字节豆包"),
    ("Baiduspider", "百度 AI"),
    ("Google-Extended", "Google AI 训练"),
]


def _get(url: str, timeout: int = 20) -> tuple[int, bytes]:
    """抓一个 URL。带 Referer 与更完整的 UA。

    实测踩坑：部分企业站（尤其 http 的老站、CDN/WAF 后面）用裸 UA 会回
    403/0，直接记 0 分会误伤——那不是客户的问题，是我们自己没抓到。
    所以这里逐级重试，并记录「最终是否真的抓到」。
    """
    uas = [
        UA,
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ]
    referer = urllib.parse.urlparse(url)
    last = (0, b"")
    for i, ua in enumerate(uas):
        req = urllib.request.Request(url, headers={
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": f"{referer.scheme}://{referer.netloc}/",
        })
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
            body = r.read(400_000)
            if r.status == 200 and body:
                return r.status, body
            last = (r.status, body)
        except urllib.error.HTTPError as e:
            try:
                last = (e.code, e.read(80_000))
            except Exception:
                last = (e.code, b"")
        except Exception as e:
            # SSL 证书链验不过（VERIFY_FAILED）是**真问题**：主流 AI 爬虫
            # 同样会在这里放弃，所以这条结论对客户是有价值的，不是我们抓不到。
            # 必须和"我们网络不通"分开记，否则会把网络问题算到客户头上。
            if "CERTIFICATE_VERIFY_FAILED" in str(e) or "certificate verify" in str(e).lower():
                last = (-1, b"")   # -1 = 证书问题
            else:
                last = (0, b"")
    return last


def _text(b: bytes) -> str:
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return ""


def _nodes(o) -> list:
    """展开 JSON-LD 实体，必须认 @graph（Google 推荐写法）。

    顶层只有 @context/@graph 而没有 @type，按"顶层字典"解析会让所有
    @graph 站点被误判为无结构化数据 —— 假阴性会让客户白整改。
    """
    if isinstance(o, list):
        return [x for x in o if isinstance(x, dict)]
    if isinstance(o, dict):
        g = o.get("@graph")
        if isinstance(g, list):
            return [x for x in g if isinstance(x, dict)]
        return [o]
    return []


# 行业推断：从企业名和页面标题里抽关键词。
# 这是"行业基准"能卖的前提 —— 没人会为"未分类"付钱，
# 但会为"上海口腔诊所行业里你排第 3"付钱。
INDUSTRY_RULES = [
    ("口腔", "口腔医疗"), ("齿科", "口腔医疗"), ("牙科", "口腔医疗"),
    ("诊所", "口腔医疗"), ("医院", "医疗健康"),
    ("装饰", "装修装饰"), ("装修", "装修装饰"), ("建材", "装修装饰"),
    ("设计", "设计创意"), ("广告", "营销传媒"),
    ("教育", "教育培训"), ("培训", "教育培训"), ("学校", "教育培训"),
    ("编程", "教育培训"), ("少儿", "教育培训"), ("早教", "教育培训"),
    ("律师", "法律服务"), ("法律", "法律服务"), ("事务所", "法律服务"),
    ("财税", "财税服务"), ("会计", "财税服务"), ("税务", "财税服务"),
    ("科技", "软件科技"), ("软件", "软件科技"), ("信息", "软件科技"),
    ("贸易", "跨境贸易"), ("外贸", "跨境贸易"), ("跨境", "跨境贸易"),
    ("物流", "物流供应链"), ("供应链", "物流供应链"), ("货运", "物流供应链"),
    ("制造", "工业制造"), ("机械", "工业制造"), ("精密", "工业制造"),
    ("光电", "工业制造"), ("电子", "工业制造"), ("化工", "工业制造"),
    ("婚礼", "本地生活"), ("婚庆", "本地生活"), ("摄影", "本地生活"),
    ("瑜伽", "本地生活"), ("健身", "本地生活"), ("宠物", "本地生活"),
    ("汽修", "汽车服务"), ("汽车", "汽车服务"),
    ("文旅", "文旅服务"), ("旅游", "文旅服务"),
    ("餐饮", "餐饮服务"), ("食品", "餐饮服务"),
    ("实业", "综合实业"), ("集团", "综合实业"),
]


def _page_title(html: str) -> str:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else ""


def guess_industry(name: str, html: str = "") -> str:
    """按企业名（必要时加首页关键词）归类行业。

    规则命中优先；都��不中才回退到「其他」，不硬编一个行业出来 ——
    行业基准是这个产品唯一值钱的部分，错标等于整个产品失效。
    """
    # 只看企业名，不看正文。页面里出现"口腔"可能是同行案例/文章目录，
    # 拿正文当依据会把测评站自己判成口腔诊所 —— 行业错标整个基准就废了。
    for kw, ind in INDUSTRY_RULES:
        if kw in name:
            return ind
    return "其他"


def audit(url: str) -> dict:
    """对单个官网跑体检，返回结构化结果。"""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url.strip()
    host = urllib.parse.urlparse(url).netloc
    root = urllib.parse.urlparse(url)
    base = f"{root.scheme}://{root.netloc}"
    # robots.txt / llms.txt / sitemap.xml 要按「站点根」找，不是「域名根」。
    # 大量客户把站点挂在子目录（github.io/project、/shop、/index.html 之外的
    # 子站等），只查域名根会把好站误判成"什么都没配"。
    site_path = root.path if root.path.endswith("/") else root.path.rsplit("/", 1)[0] + "/"
    site_base = (base + "/" + site_path.strip("/") + "/") if site_path.strip("/") else base

    def _probe(fname: str) -> tuple[int, bytes]:
        """先查站点根，再回落域名根。两处都没有才算真的没有。"""
        c, b = _get(site_base + "/" + fname)
        if c == 200 and b:
            return c, b
        if site_base != base:
            c2, b2 = _get(base + "/" + fname)
            if c2 == 200 and b2:
                return c2, b2
        return c, b
    res: dict = {"url": url, "host": host, "checks": {}, "score": 0,
                "industry": "其他"}

    # 1) robots.txt
    rc, rb = _probe("robots.txt")
    robots = _text(rb) if rc == 200 else ""
    blocked = []
    if robots:
        # 逐段解析：某 bot 段里出现 Disallow: / 且非空 → 视为全站拦截
        for bot, _label in AI_BOTS:
            m = re.search(
                rf"(?im)^user-agent:\s*{re.escape(bot)}\s*$([\s\S]*?)(?=^\s*user-agent:|\Z)",
                robots)
            if m:
                seg = m.group(1)
                dis = re.findall(r"(?im)^\s*disallow:\s*(\S*)", seg)
                if any(d.strip() in ("/", "") for d in dis):
                    blocked.append(bot)
    res["checks"]["robots"] = {
        "exists": rc == 200,
        "blocked": blocked,
        "total": len(AI_BOTS),
    }

    # 2) llms.txt
    lc, lb = _probe("llms.txt")
    res["checks"]["llms"] = {"exists": lc == 200 and len(lb) > 30}

    # 3) 首页正文
    hc, hb = _get(url)
    # 只拿到了正文就继续解析，状态码只作为记录
    html = _text(hb) if hb else ""
    res["http"] = hc
    res["name"] = _page_title(html) or host
    res["industry"] = guess_industry(res["name"], html)

    # 反爬/风控页识别。阿里云 WAF 返 200 + JS 挑战页；B 站这类返 412 +
    # 「出错啦」；很多站对机器人返 403。这些都不是官网内容，拿去打分就是诬告。
    # 标成「需人工复核」：既不冤枉客户，也不假装我们抓到了。绝不绕 WAF。
    anti_bot = bool(re.search(
        r"(?i)(aliyun_waf_\w+|captcha-delivery\.com|_captcha|"
        r"请开启.{0,6}JavaScript|just a moment|checking your browser|"
        r"cf-browser-verification|安全验证|滑动验证|出错啦|"
        r"Access Denied|Forbidden|人机验证|请稍候)", html[:6000]))
    challenge = anti_bot or hc in (401, 403, 405, 406, 412, 429, 451, 503)
    waf = challenge
    # 「官网打不开」和「AI 搜不到」责任方不同，不能混。
    # 站点有响应就算活着：3xx 是它在跳转、403/503 后面往往仍有真 HTML（WAF、
    # 地域限流、反爬）。只有真正零响应（DNS/超时/连接被拒）才算不可访问。
    # 之前硬判 hc==200，把华为、海尔、蔚来这类活站打成"无法访问"，
    # 等于凭空指控客户网站坏了 —— 这种误判会让报告失去可信度。
    # 520/521/522 加一个几十字节的回源失败占位页不是官网。只看"有响应"
    # 会把它当真页面，再按"什么都没配"打分 —— 等于凭空指控客户。宁可判
    # "探测端取不到"，也不给假结论。
    origin_error = hc >= 500 and len(hb) < 1024
    res["checks"]["reachable"] = {
        "ok": hc > 0 and len(hb) >= 256 and not origin_error,
        "bytes": len(hb),
        "waf": waf,
    }

    # 4) JSON-LD
    types = []
    for m in re.finditer(
            r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html):
        try:
            obj = json.loads(m.group(1).strip())
            for o in _nodes(obj):
                t = o.get("@type")
                if t:
                    types.extend(t if isinstance(t, list) else [t])
        except Exception:
            continue
    res["checks"]["schema"] = {
        "exists": bool(types),
        "types": sorted(set(str(t) for t in types)),
        "has_org": any("Organization" in str(t) or "LocalBusiness" in str(t)
                       or "MedicalBusiness" in str(t) for t in types),
        "has_faq": any("FAQ" in str(t) for t in types),
    }

    # 5) sitemap
    sc, _sb = _probe("sitemap.xml")
    res["checks"]["sitemap"] = {"exists": sc == 200}

    # 6) FAQ / Q&A 区块
    has_faq = bool(re.search(r"(?i)(FAQ|常见问题|问答|Q&A)", html))
    res["checks"]["faq"] = {"exists": has_faq}

    # 7) title / description
    tm = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    dm = re.search(
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html)
    res["checks"]["meta"] = {
        "title": (tm.group(1).strip() if tm else "")[:120],
        "has_title": bool(tm and tm.group(1).strip()),
        "has_description": bool(dm),
    }

    # ---- 计分：满分 100，只看「能不能被 AI 读到」相关的硬指标 ----
    score = 0
    why: list[str] = []
    # 站点根本没抓到（DNS 挂了/超时/服务端错误）就不能给 AI 可见度打分，
    # 那不是"AI 里搜不到"，而是"网站本身打不开"，两者责任方不同。
    if not res["checks"]["reachable"]["ok"]:
        res["score"] = 0
        if res["http"] == -1:
            res["grade"] = "证书故障"
            res["blockers"] = ["官网 HTTPS 证书链校验不通过。"
                               "主流 AI 爬虫在握手阶段就会放弃，等于直接不收录 —— "
                               "这是真问题，建议优先修复证书链。"]
        else:
            res["grade"] = "无法访问"
            res["blockers"] = [f"探测端未取得任何响应（HTTP {res['http']}），"
                               f"AI 大概率也抓不到；建议先在境内网络复测可达性，"
                               f"确认不是我们这边网络的问题"]
        res["unreachable"] = True
        return res

    # WAF 挡住的站不能按"抓到了"算分：拿到的是挑战页，不是官网内容，
    # 打分等于造假。也不绕过去，直接标成需人工复核。
    if waf:
        res["score"] = 0
        res["grade"] = "需人工复核"
        res["blockers"] = ["站点启用了反爬验证（WAF/验证码），自动探测拿不到真实页面。"
                           "这不代表该站有问题，需人工用浏览器打开确认后再判分。"]
        res["waf_blocked"] = True
        res["unreachable"] = False
        return res
    res["unreachable"] = False

    # 关键区分：robots.txt 不存在 ≠ 拦截 AI 爬虫。实测 21 家没有一家真拦了。
    # 早期版本把"没放行"和"拦了"混为一谈，把全场打成 0 分 —— 那是制造假问题
    # 去卖货，结论不可信。这里只在真的出现 Disallow: / 时才判为拦截。
    r_rob = res["checks"]["robots"]
    if r_rob["blocked"]:
        why.append("robots.txt 明确拦截了 AI 爬虫：" + "、".join(r_rob["blocked"]))
    elif r_rob["exists"]:
        score += 30
    else:
        score += 18   # 没 robots.txt：不扣满分，但也没有明确放行
        why.append("没有 robots.txt，未明确放行 AI 爬虫")
    s = res["checks"]["schema"]
    if s["exists"] and s["has_org"]:
        score += 25
    elif s["exists"]:
        score += 12
        why.append("有结构化数据但没有实体（Organization/LocalBusiness）")
    else:
        why.append("没有 JSON-LD 结构化数据，AI 难以识别你是谁")
    if s["has_faq"]:
        score += 15
    else:
        why.append("没有 FAQ/问答区块，AI 无从抽取问答对")
    if res["checks"]["llms"]["exists"]:
        score += 10
    else:
        why.append("没有 llms.txt（给大模型的站点说明书）")
    if res["checks"]["meta"]["has_description"]:
        score += 10
    else:
        why.append("缺少 meta description")
    if res["checks"]["sitemap"]["exists"]:
        score += 10
    else:
        why.append("没有 sitemap.xml")

    res["score"] = min(score, 100)
    res["grade"] = ("优" if res["score"] >= 80 else
                    "中" if res["score"] >= 55 else "差")
    res["blockers"] = why
    return res


def public_view(r: dict) -> dict:
    """给浏览器看的免费部分：分数 + 结论，不含具体整改方案。"""
    return {
        "host": r["host"],
        "score": r["score"],
        "grade": r["grade"],
        "reachable": r["checks"]["reachable"]["ok"],
        "blocked_bots": r["checks"]["robots"]["blocked"],
        "blockers": r["blockers"],
        "has_schema": r["checks"]["schema"]["exists"],
        "has_faq": r["checks"]["faq"]["exists"],
        "has_llms": r["checks"]["llms"]["exists"],
    }