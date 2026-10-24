# -*- coding: utf-8 -*-
"""
ccgp 24/7 生产采集器 v2

解决三个已实测的问题：
1. 限流/封禁 —— 会话复用 + 指数退避 + 空结果连续出现即判定被封并长睡
2. 浪费带宽 —— 已入库 URL 直接跳过详情请求（详情请求是主要成本）
3. 无法续跑 —— 查询网格持久化，崩溃/断网后从断点继续

只抓取公开政府采购公告，不采集任何个人信息。
"""
import http.cookiejar
import io
import json
import os
import random
import re
import sqlite3
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "ccgp_production.db")
STATE = os.path.join(BASE, "_crawler_state.json")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

COOKIES = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(COOKIES),
    urllib.request.HTTPSHandler(context=CTX),
)
OPENER.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.8"),
    ("Accept-Language", "zh-CN,zh;q=0.9"),
    ("Connection", "keep-alive"),
]

# 六种公告类型
TYPES = [("bidx", "公开招标"), ("yixb", "邀请招标"), ("jztp", "竞争性谈判"),
         ("jzcs", "竞争性磋商"), ("xunjia", "询价"), ("dyly", "单一来源"),
         ("zbj", "中标结果"), ("cjj", "成交结果")]

# 关键词网格：行业词 × 通用采购词，覆盖面优先
KEYWORDS = [
    "医院", "学校", "大学", "软件", "电梯", "物业", "食堂", "绿化", "保洁",
    "监控", "消防", "装修", "审计", "印刷", "车辆", "家具", "空调", "锅炉",
    "供水", "供电", "网络", "机房", "服务器", "系统集成", "测绘", "设计",
    "施工", "监理", "检测", "评估", "咨询", "培训", "广告", "印刷品",
    "劳保", "办公用品", "药品", "耗材", "试剂", "设备", "仪器", "车辆租赁",
    "安保", "门禁", "停车场", "食堂管理", "垃圾清运", "绿化养护", "虫害防治",
    "档案管理", "财务软件", "机房建设", "视频会议", "安防监控", "窗帘",
    "食堂桌椅", "床品", "制服", "劳保用品", "印刷服务", "展板", "显示屏",
    "LED", "会议服务", "差旅", "车辆维修", "轮胎", "油料", "水处理",
    "电梯维保", "特种设备", "消防维保", "安防工程", "管线", "管道", "桥梁",
    "道路", "绿化工程", "保洁服务", "洗涤", "食堂托管", "劳务派遣", "外包",
    "信息系统", "大数据", "云计算", "软件开发", "运维服务", "等级保护",
    "网站", "新媒体", "宣传片", "纪录片", "翻译", "法律顾问", "财税",
    "银行", "保险", "拍卖", "评估机构", "认证", "检测服务", "维修",
    "建筑", "装修工程", "景观", "苗木", "花卉", "石材", "瓷砖", "涂料",
    "卫浴", "灯具", "家具采购", "床上用品", "食堂设备", "厨房设备",
]
YEARS = list(range(2013, 2027))


def search_url(page, kw, dbselect, year, zone=""):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": page, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": dbselect,
        "kw": kw, "start_time": "%d:01:01" % year, "end_time": "%d:12:31" % year,
        "timeType": 6, "displayZone": "", "zoneId": zone, "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


# ---------------------------------------------------------------- 节流
class Throttle:
    """自适应节流：越慢越安全，但也不能慢到没有产能。"""

    def __init__(self, lo=1.4, hi=25.0, backoff=1.6):
        self.lo, self.hi, self.k = lo, hi, backoff
        self.d = 2.0
        self.misses = 0

    def wait(self):
        time.sleep(self.d * (0.75 + random.random() * 0.5))

    def ok(self):
        self.d = max(self.lo, self.d / self.k)
        self.misses = 0

    def degrade(self):
        self.misses += 1
        self.d = min(self.hi, self.d * self.k)
        return self.d

    def blocked(self):
        self.d = self.hi
        self.misses += 1
        time.sleep(self.hi * 6)


TH = Throttle()


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = OPENER.open(url, timeout=30)
            raw = r.read()
            TH.ok()
            for e in ("utf-8", "gbk", "gb18030"):
                try:
                    return raw.decode(e)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 403, 503):
                TH.degrade()
                time.sleep(TH.d * 2)
            elif e.code in (521, 520):
                time.sleep(8)
            else:
                time.sleep(2)
        except Exception as e:
            last = e
            TH.degrade()
            time.sleep(TH.d)
    raise last


# ---------------------------------------------------------------- 解析
A_RE = re.compile(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.S)


def parse_list(html):
    rows = []
    for blk in re.findall(r"<li[^>]*>(.*?)</li>", html, re.S):
        m = A_RE.search(blk)
        if not m:
            continue
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip()
        url = m.group(1)
        if url.startswith("./"):
            url = "http://www.ccgp.gov.cn" + url[1:]
        if len(title) >= 8 and ".htm" in url and "t20" in url:
            rows.append((title, url))
    return rows


TAGS = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
ORG = (r"公司|集团|中心|医院|卫生院|诊所|学校|大学|学院|研究院|研究所|委员会|"
       r"政府|局|所|厂|店|部|院|馆|社|协会|学会|基金会|管理处|事务所|站|办|园区|基地")
_BAD = re.compile(r"[。，；：、！？（）()\[\]【】<>“”\"'0-9\s]|[年月日时分秒]")


def detail_text(html):
    s = TAGS.sub(" ", html)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</(p|div|tr|li|h\d)>", "\n", s)
    s = re.sub(r"(?is)</?span[^>]*>", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t　]+", " ", s)).strip()


def clean_org(s):
    if not s:
        return ""
    s = s.strip()
    for cut in "。；：，、！（()":
        i = s.find(cut)
        if i > 0:
            s = s[:i]
    s = re.split(r"\s{2,}", s)[0]
    s = re.sub(r"^(名称|名　称|单位名称)\s*[：:]?\s*", "", s).strip()
    if not s or len(s) < 3 or len(s) > 50:
        return ""
    if not re.search(ORG + r"$", s) or _BAD.search(s):
        return ""
    return s


def grab_org(t, pats):
    for p in pats:
        m = re.search(p, t)
        if m:
            g = clean_org(m.group(1))
            if g:
                return g
    return ""


def cut(t, labels, maxlen=120):
    for lab in labels:
        m = re.search(lab + r"\s*[：:]\s*([^\n]{1,%d})" % maxlen, t)
        if m:
            v = re.split(r"\s{2,}|\d+\s*\.", m.group(1))[0]
            v = re.split(r"(?:项目|采购|招标|公告|联系人|地址|电话|时间|金额)(?=：)", v)[0]
            v = v.strip().strip("：:，,。;；")
            if v:
                return v
    return ""


CHANNEL = {"gkzb": "公开招标", "yzb": "邀请招标", "jzxcs": "竞争性磋商",
           "jztp": "竞争性谈判", "xj": "询价", "dyly": "单一来源",
           "zbgg": "中标结果", "cggg": "采购公告", "fblbgg": "废标公告",
           "gzgg": "更正公告", "cjsgg": "成交结果", "qtgg": "其他公告"}
AMT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(万元|亿元|万|元)")


def parse_detail(html, url):
    t = detail_text(html)
    r = {"url": url}
    r["buyer"] = grab_org(t, [
        r"1\.\s*采购人信息\s*名\s*称\s*[：:]?\s*([^\n]{3,60})",
        r"采购人名称\s*[：:]?\s*([^\n]{3,60})",
        r"采购单位\s*[：:]?\s*([^\n]{3,60})",
    ])
    if not r["buyer"]:
        m = re.search(r"采购项目名称\s*([^\n]{3,60}?)\s*(?:公开招标|竞争性磋商|询价|"
                      r"单一来源|竞争性谈判|招标|磋商|中标|成交|废标)?"
                      r"(?:公告|项目|采购|服务)", t)
        if m:
            r["buyer"] = clean_org(m.group(1))
    r["agency"] = grab_org(t, [
        r"2\.\s*采购代理机构信息\s*名\s*称\s*[：:]?\s*([^\n]{3,60})",
        r"代理机构名称\s*[：:]?\s*([^\n]{3,60})",
        r"采购代理机构\s*[：:]?\s*([^\n]{3,60})",
    ])
    r["project_no"] = cut(t, ["采购项目编号", "项目编号", "招标编号"], 60)
    r["project_name"] = cut(t, ["采购项目名称", "项目名称"], 120)
    r["buyer_address"] = cut(t, [r"地\s*址", "地址"], 100)
    r["open_time"] = cut(t, ["开标时间", "响应文件开启时间", "截止时间"], 50)
    r["requirement"] = cut(t, ["采购需求", "标的名称", "项目概况"], 240)
    m = re.search(r"/cggg/[a-z]+/([a-z]+)/\d{6}/", url)
    r["channel"] = CHANNEL.get(m.group(1), "") if m else ""
    dm = re.search(r"/(20\d{2})(\d{2})/t(\d{8})_", url)
    r["publish_date"] = ("%s-%s-%s" % (dm.group(1), dm.group(2), dm.group(3)[6:])
                         if dm else "")
    am = AMT.search(t)
    r["budget"] = am.group(0) if am else ""
    r["budget_cny"] = 0.0
    if am:
        v = float(am.group(1).replace(",", ""))
        u = am.group(2)
        r["budget_cny"] = v * 1e8 if u == "亿元" else v * 1e4 if u in ("万元", "万") else v
    r["content_len"] = len(t)
    return r


# ---------------------------------------------------------------- 存储
def init_db():
    c = sqlite3.connect(DB, timeout=30)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS notices (
      url TEXT PRIMARY KEY, title TEXT, publish_date TEXT, province TEXT,
      channel TEXT, project_no TEXT, project_name TEXT, buyer TEXT,
      buyer_address TEXT, agency TEXT, open_time TEXT, requirement TEXT,
      budget TEXT, budget_cny REAL, content_len INTEGER,
      kw TEXT, dbselect TEXT, fetched_at TEXT
    );
    CREATE INDEX IF NOT EXISTS ix_buyer ON notices(buyer);
    CREATE INDEX IF NOT EXISTS ix_pub ON notices(publish_date);
    CREATE TABLE IF NOT EXISTS buyers (
      name TEXT PRIMARY KEY, n_notices INTEGER DEFAULT 0,
      total_budget REAL DEFAULT 0, provinces TEXT, latest TEXT, latest_url TEXT
    );
    CREATE TABLE IF NOT EXISTS grid (
      kw TEXT, dbselect TEXT, yr INTEGER, page INTEGER,
      zone TEXT, done INTEGER DEFAULT 0, hits INTEGER DEFAULT 0, at TEXT,
      PRIMARY KEY (kw, dbselect, yr, page, zone)
    );
    """)
    c.commit()
    return c


def uid(url):
    m = re.search(r"t(\d{8})_(\d+)\.htm", url)
    return url


def save(c, r, kw, dbselect):
    if not r.get("buyer"):
        return 0
    try:
        c.execute("""INSERT OR REPLACE INTO notices
          (url,title,publish_date,province,channel,project_no,project_name,buyer,
           buyer_address,agency,open_time,requirement,budget,budget_cny,
           content_len,kw,dbselect,fetched_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
                  (r["url"], r.get("title", ""), r.get("publish_date", ""),
                   r.get("province", ""), r.get("channel", ""),
                   r.get("project_no", ""), r.get("project_name", ""),
                   r["buyer"], r.get("buyer_address", ""), r.get("agency", ""),
                   r.get("open_time", ""), r.get("requirement", ""),
                   r.get("budget", ""), r.get("budget_cny", 0.0),
                   r.get("content_len", 0), kw, dbselect))
        c.execute("""INSERT INTO buyers (name,n_notices,total_budget,latest,latest_url)
          VALUES (?,1,?,?,?) ON CONFLICT(name) DO UPDATE SET
          n_notices=n_notices+1, total_budget=total_budget+excluded.total_budget,
          latest=CASE WHEN excluded.latest>latest THEN excluded.latest ELSE latest END,
          latest_url=CASE WHEN excluded.latest>latest THEN excluded.latest_url ELSE latest_url END""",
                  (r["buyer"], r.get("budget_cny", 0.0),
                   r.get("publish_date", ""), r.get("project_no", "") and r["url"]))
        c.commit()
        return 1
    except sqlite3.Error:
        return 0


# ---------------------------------------------------------------- 主循环
def run(max_seconds=600, page_max=12):
    c = init_db()
    seen = set(x[0] for x in c.execute("SELECT url FROM notices"))
    t_end = time.time() + max_seconds
    stats = {"lists": 0, "details": 0, "saved": 0, "skip": 0, "empty": 0}
    grid = [(k, d, y) for y in YEARS for d, _ in TYPES for k in KEYWORDS]
    random.shuffle(grid)

    for kw, dbselect, yr in grid:
        if time.time() > t_end:
            break
        for p in range(1, page_max + 1):
            if time.time() > t_end:
                break
            row = c.execute("SELECT done FROM grid WHERE kw=? AND dbselect=? "
                            "AND yr=? AND page=?", (kw, dbselect, yr, p)).fetchone()
            if row and row[0]:
                break
            try:
                items = parse_list(get(search_url(p, kw, dbselect, yr)))
            except Exception:
                break
            TH.wait()
            stats["lists"] += 1
            if not items:
                stats["empty"] += 1
                c.execute("INSERT OR REPLACE INTO grid VALUES (?,?,?,?,1,0,datetime('now'))",
                          (kw, dbselect, yr, p))
                c.commit()
                TH.degrade()
                if TH.misses >= 4:
                    print("   疑似被限流，长睡 %ds" % (TH.d * 6))
                    time.sleep(TH.d * 6)
                    TH.misses = 0
                break
            for title, url in items:
                if url in seen:
                    stats["skip"] += 1
                    continue
                try:
                    d = parse_detail(get(url, tries=2), url)
                except Exception:
                    continue
                d["title"] = title
                seen.add(url)
                stats["details"] += 1
                stats["saved"] += save(c, d, kw, dbselect)
                TH.wait()
            c.execute("INSERT OR REPLACE INTO grid VALUES (?,?,?,?,1,?,datetime('now'))",
                      (kw, dbselect, yr, p, len(items)))
            c.commit()

    n = c.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    b = c.execute("SELECT COUNT(*) FROM buyers").fetchone()[0]
    done = c.execute("SELECT COUNT(*) FROM grid WHERE done=1").fetchone()[0]
    stats.update(notices=n, buyers=b, grid_done=done,
                 delay=round(TH.d, 2), cookies=len(COOKIES))
    c.close()
    with io.open(os.path.join(BASE, "_crawler_run.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats


if __name__ == "__main__":
    import sys
    mins = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    s = run(max_seconds=mins * 60)
    print(json.dumps(s, ensure_ascii=False, indent=2))
