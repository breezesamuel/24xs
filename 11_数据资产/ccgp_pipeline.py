# -*- coding: utf-8 -*-
"""
ccgp 生产管道 v1 —— 政府采购公告 -> 结构化「一篇档案」

已验证：搜索接口分页生效（4页4个不同指纹），详情页可达且字段可定位。
本模块负责：翻页、抽取、去重、入库。每篇=一个采购人（真实企业实体）。
只存公开公告字段，不含任何个人信息。
"""
import hashlib
import json
import os
import re
import sqlite3
import ssl
import time
import urllib.parse
import urllib.request

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "ccgp_production.db")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.8",
    "Referer": "http://www.ccgp.gov.cn/",
}

# 搜索类型：1=公开招标 2=邀请招标 3=竞争性谈判 4=竞争性磋商 5=询价 6=单一来源
DBSELECT = {
    "bidx": "公开招标",
    "yixb": "邀请招标",
    "jztp": "竞争性谈判",
    "jzcs": "竞争性磋商",
    "xunjia": "询价",
    "dyly": "单一来源",
}


# ---------------------------------------------------------------- 网络
def _get(url, tries=3, sleep=1.5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            r = urllib.request.urlopen(req, timeout=30, context=CTX)
            raw = r.read()
            for enc in ("utf-8", "gbk", "gb18030"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "ignore")
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(sleep * (i + 1))
    raise last


# ---------------------------------------------------------------- 列表页
def search_url(page, kw, dbselect="bidx", zone=""):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": page, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": dbselect,
        "kw": kw, "start_time": "2015:01:01", "end_time": "2026:10:01",
        "timeType": 6, "displayZone": "", "zoneId": zone, "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


def parse_list(html):
    """从列表页抽 (title, url, 粗略地区, 粗略日期)。"""
    rows = []
    for blk in re.findall(r"<li[^>]*>(.*?)</li>", html, re.S):
        a = re.search(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", blk, re.S)
        if not a:
            continue
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", a.group(2))).strip()
        url = a.group(1)
        if url.startswith("./"):
            url = "http://www.ccgp.gov.cn" + url[1:]
        if len(title) < 8 or ".htm" not in url:
            continue
        meta = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", blk)).strip()
        dm = re.search(r"(20\d{2})[年\-/\.](\d{1,2})[月\-/\.](\d{1,2})", meta)
        date = ""
        if dm:
            date = "%s-%02d-%02d" % (dm.group(1), int(dm.group(2)), int(dm.group(3)))
        province = ""
        for p in ["北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
                  "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
                  "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
                  "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆"]:
            if p in meta[:60]:
                province = p
                break
        rows.append({"title": title, "url": url, "list_date": date,
                     "province": province, "kind": DBSELECT.get("bidx", "")})
    return rows


# ---------------------------------------------------------------- 详情页
_TAGS = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_SPAN_SPLIT = re.compile(r"(?is)</?span[^>]*>")


def detail_text(html):
    """还原正文：span 被拆散的标签要先合并，再去标签。"""
    # 把 </span><span ...> 之间的 &nbsp; 视作标签的一部分会丢字，
    # 所以先按纯文本提标签，再回填。
    s = _TAGS.sub(" ", html)
    s = re.sub(r"(?is)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)</(p|div|tr|li|h\d)>", "\n", s)
    s = _SPAN_SPLIT.sub("", s)          # 合并被 span 拆开的文字
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    s = re.sub(r"[ \t　]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def _after(text, labels, maxlen=140):
    """在 text 里找 labels 任一，取其后一段。"""
    for lab in labels:
        m = re.search(re.escape(lab) + r"\s*[）)]?\s*[：:]\s*([^\n]{2,%d})" % maxlen, text)
        if m:
            v = m.group(1).strip()
            v = re.split(r"\s{3,}", v)[0].strip()
            if v:
                return v
    return ""


AMOUNT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(万元|元|万|亿元)")

# 公告 URL 目录名 -> 公告类别
CHANNEL = {
    "gkzb": "公开招标", "yzb": "邀请招标", "jzxcs": "竞争性磋商",
    "jztp": "竞争性谈判", "xj": "询价", "dyly": "单一来源",
    "zbgg": "中标结果", "cggg": "采购公告", "fblbgg": "废标公告",
    "gzgg": "更正公告", "cjsgg": "成交结果", "qtgg": "其他公告",
    "yqgg": "邀请公告", "qtgg1": "其他公告",
}

# 企业名尾巴：判断一段文字像不像一个组织实体
ORG_SUFFIX = (
    "公司|集团|中心|医院|卫生院|卫生服务中心|诊所|学校|大学|学院|研究院|研究所|"
    "委员会|政府|管理局|监督局|局|所|厂|店|部|院|馆|社|协会|学会|基金会|"
    "管理处|服务社|合作社|事务所|中心站|总站|站|办|园区|基地|厂矿"
)
_BAD_IN_NAME = re.compile(r"[。，；：、！？（）()\[\]【】<>“”\"'0-9\s]|[年月日时分秒]")


def clean_org(s):
    """从一段噪声里截出一个像样的组织名。不像就返回空。"""
    if not s:
        return ""
    s = s.strip()
    # 在第一个明显不是名字的符号处截断
    for cut in ("。", "，", "；", "、", "（", "(", "：", ":"):
        i = s.find(cut)
        if i > 0:
            s = s[:i]
    s = s.strip().lstrip("0123456789.、 ").strip()
    s = re.split(r"\s{2,}", s)[0]
    s = re.sub(r"^(名称|名　称|单位名称)\s*[：:]?\s*", "", s)
    if not s or len(s) < 3 or len(s) > 50:
        return ""
    if not re.search(ORG_SUFFIX + r"$", s):
        return ""
    if _BAD_IN_NAME.search(s):
        return ""
    return s


def _cut(text, labels, maxlen=120):
    """取 label 后的值，并在明显的边界处停止（避免整段吞掉）。"""
    for lab in labels:
        m = re.search(lab + r"\s*[：:]\s*([^\n]{1,%d})" % maxlen, text)
        if m:
            v = m.group(1)
            v = re.split(r"\s{2,}", v)[0]
            v = re.split(r"\d+\s*\.", v)[0]
            v = re.split(r"(?:项目|采购|招标|公告|联系人|地址|电话|时间|金额)" r"(?=：)", v)[0]
            v = v.strip().strip("：:，,。;；")
            if v:
                return v
    return ""


def _grab(text, labels, maxlen=200):
    """找 label 后面一段噪声，再交给 clean_org 判断。"""
    for lab in labels:
        m = re.search(lab + r"\s*[）)]?\s*[：:]?\s*([^\n]{2,%d})" % maxlen, text)
        if m:
            got = clean_org(m.group(1))
            if got:
                return got
    return ""


def parse_detail(html, url):
    t = detail_text(html)
    rec = {"url": url}

    # --- 采购人：多个模板位置，按可靠性排序 ---
    # 浙江系模板：七、…联系 / 1.采购人信息 / 名称：XXX
    # 深圳/山东系：公告概要里"采购单位XXX"
    rec["buyer"] = _grab(t, [
        r"1\.\s*采购人信息\s*名\s*称\s*[：:]?\s*",
        r"采购人名称\s*[：:]?\s*",
        r"采购单位\s*[：:]?\s*",
        r"采购人\s*[：:]\s*",
        r"名\s*称\s*[：:]\s*(?=[^\n]{0,4}(公司|医院|学校|中心|局|所|院|厂|大学|学院))",
    ])
    if not rec["buyer"]:
        # 兜底：项目名去掉"XX项目/XX采购"后缀常就是采购人
        m = re.search(r"采购项目名称\s*([^\n]{3,60}?)\s*(?:公开招标|竞争性磋商|询价|"
                      r"单一来源|竞争性谈判|招标|磋商|询价|中标|成交|废标)?"
                      r"(?:公告|项目|采购|服务)", t)
        if m:
            rec["buyer"] = clean_org(m.group(1))

    rec["agency"] = _grab(t, [
        r"2\.\s*采购代理机构信息\s*名\s*称\s*[：:]?\s*",
        r"代理机构名称\s*[：:]?\s*",
        r"采购代理机构\s*[：:]?\s*",
    ])

    rec["project_no"] = _cut(t, ["采购项目编号", "项目编号", "招标编号"], 60)
    rec["project_name"] = _cut(t, ["采购项目名称", "项目名称"], 120)
    rec["buyer_address"] = _cut(t, [r"地\s*址", "地址"], 100)
    rec["open_time"] = _cut(t, ["开标时间", "响应文件开启时间", "截止时间"], 50)
    rec["requirement"] = _cut(t, ["采购需求", "标的名称"], 200)

    cm = re.search(r"(?:项目联系人|联\s*系\s*人)\s*[（(]?[^）)]{0,12}[）)]?\s*[：:]\s*"
                   r"([^\n]{2,40})", t)
    rec["buyer_contact_dept"] = cm.group(1).strip() if cm else ""
    ph = re.search(r"(?:项目)?(?:联系电话|联系方式|电\s*话)\s*[：:]\s*"
                   r"([\d\-() ]{7,30})", t)
    rec["buyer_phone_public"] = ph.group(1).strip() if (ph and ph.group(1)) else ""

    am = AMOUNT.search(t)
    rec["budget"] = (am.group(0) if am else "")
    rec["budget_cny"] = 0.0
    if am:
        val = float(am.group(1).replace(",", ""))
        unit = am.group(2)
        rec["budget_cny"] = (val * 10000 if unit in ("万元", "万")
                             else val * 1e8 if unit == "亿元" else val)

    m = re.search(r"/cggg/[a-z]+/([a-z]+)/\d{6}/", url)
    rec["channel"] = CHANNEL.get(m.group(1), "") if m else ""
    dm = re.search(r"/(20\d{2})(\d{2})/t(\d{8})_", url)
    if dm:
        rec["publish_date"] = "%s-%s-%s" % (dm.group(1), dm.group(2), dm.group(3)[6:])
    else:
        rec["publish_date"] = _cut(t, ["公告发布时间", "发布时间"], 30)

    rec["content_len"] = len(t)
    return rec



# ---------------------------------------------------------------- 存储
def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS notices (
      url TEXT PRIMARY KEY,
      uid TEXT UNIQUE,
      title TEXT, list_date TEXT, province TEXT, channel TEXT,
      project_no TEXT, project_name TEXT,
      buyer TEXT, buyer_contact_dept TEXT, buyer_address TEXT,
      buyer_phone_public TEXT,
      agency TEXT, agency_contact TEXT,
      open_time TEXT, publish_date TEXT,
      budget TEXT, budget_cny REAL, requirement TEXT, content_len INTEGER,
      fetched_at TEXT, raw_ok INTEGER
    );
    CREATE INDEX IF NOT EXISTS ix_buyer ON notices(buyer);
    CREATE INDEX IF NOT EXISTS ix_prov ON notices(province);
    CREATE TABLE IF NOT EXISTS buyers (
      name TEXT PRIMARY KEY,
      province TEXT, n_notices INTEGER DEFAULT 0,
      total_budget REAL DEFAULT 0, first_seen TEXT, last_seen TEXT
    );
    """)
    c.commit()
    return c


def uid_of(url):
    m = re.search(r"t(\d{8})_(\d+)\.htm", url)
    return (m.group(1) + m.group(2)) if m else hashlib.md5(url.encode()).hexdigest()[:16]


def save(c, r):
    if not r.get("buyer"):
        return 0
    try:
        c.execute("""INSERT OR REPLACE INTO notices
          (url,uid,title,list_date,province,channel,project_no,project_name,
           buyer,buyer_contact_dept,buyer_address,buyer_phone_public,
           agency,agency_contact,
           open_time,publish_date,budget,budget_cny,requirement,content_len,
           fetched_at,raw_ok)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),1)""",
                  (r["url"], uid_of(r["url"]), r.get("title", ""),
                   r.get("list_date", ""), r.get("province", ""), r.get("channel", ""),
                   r.get("project_no", ""), r.get("project_name", ""),
                   r["buyer"], r.get("buyer_contact_dept", ""),
                   r.get("buyer_address", ""), r.get("buyer_phone_public", ""),
                   r.get("agency", ""),
                   r.get("agency_contact", ""), r.get("open_time", ""),
                   r.get("publish_date", ""), r.get("budget", ""),
                   r.get("budget_cny", 0.0), r.get("requirement", ""),
                   r.get("content_len", 0)))
        b = r["buyer"]
        c.execute("""INSERT INTO buyers (name,province,n_notices,total_budget,first_seen,last_seen)
          VALUES (?,?,1,?,?,?) ON CONFLICT(name) DO UPDATE SET
          n_notices=n_notices+1, total_budget=total_budget+excluded.total_budget,
          last_seen=excluded.last_seen""",
                  (b, r.get("province", ""), r.get("budget_cny", 0.0),
                   r.get("publish_date", "") or r.get("list_date", ""),
                   r.get("publish_date", "") or r.get("list_date", "")))
        c.commit()
        return 1
    except sqlite3.Error:
        return 0


# ---------------------------------------------------------------- 采集
def harvest(kw, pages=5, dbselect="bidx", delay=1.6, verbose=True):
    c = init_db()
    got = kept = 0
    for p in range(1, pages + 1):
        try:
            rows = parse_list(_get(search_url(p, kw, dbselect)))
        except Exception as e:
            if verbose:
                print("   列表页 p%d 失败 %s" % (p, type(e).__name__))
            time.sleep(delay)
            continue
        if not rows:
            if verbose:
                print("   列表页 p%d 无结果，停止" % p)
            break
        for row in rows:
            got += 1
            try:
                html = _get(row["url"], tries=2)
            except Exception:
                continue
            d = parse_detail(html, row["url"])
            d["title"] = row["title"]
            d["list_date"] = row["list_date"]
            d["province"] = row["province"]
            d["channel"] = d["channel"] or row["kind"]
            kept += save(c, d)
            time.sleep(delay * 0.55)
        if verbose:
            n = c.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
            print("   p%-3d 抓取=%-4d 入库=%-4d 库内累计=%d" % (p, got, kept, n))
        time.sleep(delay)
    c.close()
    return got, kept


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "医院"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    print("=== 首次试产: 关键词=%s 页数=%d ===" % (kw, pages))
    g, k = harvest(kw, pages)
    print("抓取 %d 条，入库 %d 条" % (g, k))
    c = sqlite3.connect(DB)
    print("\n--- 库内统计 ---")
    for q, lbl in [("SELECT COUNT(*) FROM notices", "公告"),
                   ("SELECT COUNT(*) FROM buyers", "采购人企业"),
                   ("SELECT COUNT(DISTINCT province) FROM notices", "覆盖省份"),
                   ("SELECT ROUND(AVG(content_len)) FROM notices", "平均正文字数"),
                   ("SELECT ROUND(SUM(budget_cny)) FROM notices", "预算总额(元)")]:
        print("  %-16s %s" % (lbl, c.execute(q).fetchone()[0]))
    print("\n--- 采购人 Top5 ---")
    for r in c.execute("SELECT name,province,n_notices,total_budget FROM buyers "
                       "ORDER BY n_notices DESC LIMIT 5"):
        print("  %-44s %-5s %d条  %.0f元" % (r[0][:44], r[1] or "-", r[2], r[3]))
    c.close()
