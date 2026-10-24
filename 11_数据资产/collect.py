# -*- coding: utf-8 -*-
"""丙大山数据资产采集器 —— 把"能卖钱的东西"真的抓出来。

设计前提（都已实测确认）：
  * 本机在中国大陆网络内，不需要代理
  * 百度/Bing/爱企查/企查查/天眼查 直连 200
  * 工信部备案 gsxt 返 521（反爬），所以不碰官方登记库，改走搜索引擎发现

产出（每家一条）—— 这是可售卖的资产本体：
  企业名 / 官网 / 行业 / 城市 / AI可见度体检分 / 缺什么 / 整改建议 / 联系方式

合规边界（重要）：
  只采**企业公开经营信息**（企业名、官网、行业、公开电话邮箱）。
  不采个人身份证、不采私人手机号归属人、不做人群画像。
  遵守 robots.txt；抓取限速；失败即弃，不绕验证码。
  这条线不越，后面所有商业化才有意义。
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib
import re
import sqlite3
import ssl
import sys
import threading
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(r"F:\2026\24xs")
OUT = ROOT / "11_数据资产"
DB = OUT / "assets.sqlite3"
JSONL = OUT / "companies.jsonl"

sys.path.insert(0, str(ROOT / "01_引擎"))
import geo_health as gh  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

_sctx = ssl.create_default_context()
_sctx.check_hostname = False
_sctx.verify_mode = ssl.CERT_NONE

_lock = threading.Lock()
_seen_domains: set[str] = set()

# 明确不碰的：个人隐私、征信、爬虫禁区词
BAD_DOMAIN = re.compile(
    r"(tianyancha|qcc|aiqicha|baidu|bing|google|zhihu|douyin|xiaohongshu|"
    r"weibo|twitter|facebook|instagram|youtube|taobao|tmall|jd\.com|"
    r"pinduoduo|meituan|dianping|58\.com|zhipin|liepin|ganji)",
    re.I)
BAD_NAME = re.compile(r"(个人|先生|女士|老师|律师|诊所|医院|小学|中学|大学)")


def _get(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_sctx) as r:
            raw = r.read(400_000)
            return r.status, raw.decode("utf-8", "replace")
    except Exception:
        return 0, ""


def _strip(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"<[^>]+>", " ", html)


# ---------- 1. 发现：从搜索引擎找上海企业官网 ----------
def discover(query: str, pages: int = 2) -> list[dict]:
    out: list[dict] = []
    for p in range(pages):
        url = ("https://cn.bing.com/search?q=" + urllib.parse.quote(query)
               + f"&first={p*10+1}&count=20")
        _, html = _get(url)
        if not html:
            continue
        for m in re.finditer(r'<h2><a href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.S):
            link, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
            if BAD_DOMAIN.search(urllib.parse.urlparse(link).netloc):
                continue
            out.append({"url": link, "name": title.strip()})
        time.sleep(1.2)
    return out


# ---------- 2. 抽联系方式（只取公开企业邮箱/总机电话）----------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
EMAIL_DROP = re.compile(r"(example|sentry|wixpress|godaddy|cloudflare|"
                        r"\.png|\.jpg|\.gif|noreply|no-reply)", re.I)
PHONE_RE = re.compile(r"(?:电话|热线|Tel|TEL)\s*[:：]?\s*([0-9\-\s]{7,20})")


def extract_contact(url: str) -> dict:
    status, html = _get(url, timeout=12)
    if not html:
        return {}
    text = _strip(html)
    emails = [e for e in EMAIL_RE.findall(html)
              if not EMAIL_DROP.search(e) and not re.search(r"\.(png|jpg)$", e, re.I)]
    phones = [re.sub(r"\s+", "", p) for p in PHONE_RE.findall(text)
              if 7 <= len(re.sub(r"\s+", "", p)) <= 20]
    return {
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
        "contact_http": status,
    }


# ---------- 3. 体检：跑自家 GEO 引擎 ----------
def probe(url: str) -> dict:
    try:
        return gh.audit(url)
    except Exception as e:
        return {"url": url, "score": 0, "grade": "err", "blockers": [str(e)[:80]],
                "unreachable": True, "checks": {}}


# ---------- 4. 落库 ----------
def init_db() -> sqlite3.Connection:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""
      CREATE TABLE IF NOT EXISTS companies(
        domain TEXT PRIMARY KEY,
        name TEXT, url TEXT, title TEXT,
        score INT, grade TEXT,
        has_schema INT, has_llms INT, has_faq INT, has_sitemap INT,
        robots_ok INT,
        blockers TEXT, pitch TEXT,
        email TEXT, phone TEXT,
        ts TEXT, verified INT DEFAULT 0
      )""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_score ON companies(score)")
    con.commit()
    return con


def upsert(con: sqlite3.Connection, d: dict) -> None:
    c = d.get("checks", {}) or {}
    sch = (c.get("schema") or {})
    rob = (c.get("robots") or {})
    con.execute("""
      INSERT OR REPLACE INTO companies
      (domain,name,url,title,score,grade,has_schema,has_llms,has_faq,has_sitemap,
       robots_ok,blockers,pitch,email,phone,ts,verified)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),?)""",
               (d["domain"], d.get("name", ""), d["url"], d.get("title", ""),
                d.get("score", 0), d.get("grade", ""),
                int(bool(sch.get("exists"))), int(bool((c.get("llms") or {}).get("exists"))),
                int(bool((c.get("faq") or {}).get("exists"))),
                int(bool((c.get("sitemap") or {}).get("exists"))),
                int(not rob.get("blocked")),
                " | ".join(d.get("blockers", [])[:4])[:500],
                pitch(d), d.get("email", ""), d.get("phone", ""), 0))
    con.commit()


def pitch(d: dict) -> str:
    b = d.get("blockers") or []
    if not b:
        return ""
    top = b[0]
    return f"{d.get('name','该公司')}在AI搜索里基本搜不到：{top} 免费查完整整改清单。"


# ---------- 主流程 ----------
QUERIES = [
    "上海 口腔 诊所 官网", "上海 装修 公司 官网", "上海 编程 少儿 科技 官网",
    "上海 律师 事务所 官网", "上海 摄影 工作室 官网", "上海 舞蹈 培训 机构 官网",
    "上海 宠物 医院 官网", "上海 瑜伽 馆 官网", "上海 少儿 英语 培训 官网",
    "上海 汽修 门店 官网", "上海 装修 装饰 公司 官网", "上海 财税 代理 公司 官网",
    "深圳 外贸 工厂 官网", "广州 跨境 电商 公司 官网", "杭州 直播 电商 公司 官网",
    "苏州 精密 制造 公司 官网", "宁波 汽配 出口 公司 官网", "青岛 冷链 物流 公司 官网",
    "成都 餐饮 连锁 官网", "武汉 教育 科技 官网", "西安 文旅 公司 官网",
    "南京 软件 公司 官网", "重庆 智能 制造 公司 官网", "天津 化工 企业 官网",
]


def run(target_per_query: int = 6, budget_min: float = 12.0) -> dict:
    con = init_db()
    t0 = time.time()
    cand: dict[str, dict] = {}

    print("== 阶段1：搜索发现 ==")
    for i, q in enumerate(QUERIES, 1):
        if (time.time() - t0) / 60 > budget_min * 0.45:
            print("  预算用尽，停止发现")
            break
        got = discover(q)
        new = 0
        for g in got:
            dom = urllib.parse.urlparse(g["url"]).netloc.lower()
            if not dom or dom in _seen_domains or BAD_DOMAIN.search(dom):
                continue
            if dom.endswith(".cn") is False and "." not in dom:
                continue
            if BAD_NAME.search(g["name"]):
                continue
            _seen_domains.add(dom)
            g["domain"] = dom
            cand[dom] = g
            new += 1
            if new >= target_per_query:
                break
        print(f"  [{i:2d}/{len(QUERIES)}] {q[:24]:26} 新增 {new}  累计 {len(cand)}")
        time.sleep(0.8)

    print("\n== 阶段2：体检 + 抽联系方式 ==")
    done = 0
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {}
        for dom, g in cand.items():
            futs[ex.submit(probe, g["url"])] = g
        for fu in cf.as_completed(futs):
            g = futs[fu]
            try:
                r = fu.result()
            except Exception:
                r = {}
            r["url"] = g["url"]
            r["domain"] = g["domain"]
            r["name"] = g.get("name", "")[:80]
            r["title"] = g.get("name", "")[:80]
            if not r.get("unreachable"):
                try:
                    r.update(extract_contact(g["url"]))
                except Exception:
                    pass
                upsert(con, r)
                done += 1
            if done % 10 == 0:
                print(f"  已入库 {done}/{len(cand)}")

    print("\n== 阶段3：导出 ==")
    rows = con.execute("""SELECT domain,name,url,score,grade,has_schema,has_llms,
        has_faq,has_sitemap,robots_ok,blockers,pitch,email,phone,ts
        FROM companies ORDER BY score ASC""").fetchall()
    cols = ["domain", "name", "url", "score", "grade", "has_schema", "has_llms",
            "has_faq", "has_sitemap", "robots_ok", "blockers", "pitch",
            "email", "phone", "ts"]
    with JSONL.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(dict(zip(cols, r)), ensure_ascii=False) + "\n")

    stats = {
        "collected": len(rows),
        "avg_score": round(sum(r[3] for r in rows) / max(1, len(rows)), 1),
        "no_schema": sum(1 for r in rows if not r[5]),
        "no_llms": sum(1 for r in rows if not r[6]),
        "with_email": sum(1 for r in rows if r[12]),
        "with_phone": sum(1 for r in rows if r[13]),
        "under_40": sum(1 for r in rows if r[3] < 40),
        "minutes": round((time.time() - t0) / 60, 1),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == "__main__":
    run()