# -*- coding: utf-8 -*-
"""
公开招标/采购公告 联系人采集器 v3
====================================================================
背景（v1/v2 失败复盘）
  v1 猜站内检索 URL      -> 全部 404 / JS 渲染，0 结果
  v2 用已知详情页顺藤摸瓜 -> 只爬到 1 个种子页，且该页是「律所采购催收服务」
                           —— 那是同行，不是客户，方向反了
结论：这些聚合站（采招网/千里马/知了标讯）对静态 HTTP 抓取有反爬，
      且站内搜索是 JS 渲染。发现层必须走搜索引擎的实时爬取，
      因此本脚本接受「外部传入的 URL 清单」，只负责详情页解析与合规过滤。

合规依据
  《招标投标法》《政府采购法》要求招标公告依法公示，属公共记录。
  公告中采购人主动公示的「报名邮箱 / 招标联系人」是供应商登记入口。
  本脚本只采集公示信息、保留来源 URL 供人工复核，不猜测、不补全被遮挡字段。

严格过滤
  service     = 律所/诉讼/委外催收采购   -> 同行，切勿联系
  audit       = 审计/核销类             -> 需会计师事务所资质
  erp_buying  = 甲方自建应收/账龄系统   -> 他们是买方，通常已选定厂商
  supplier_solicitation = 供应商征集/报名 -> 需企业资质，但仍可登记
  完整企业联系方式一律保留，不做脱敏
"""

import argparse
import csv
import datetime
import re
from pathlib import Path

import httpx

OUT_DIR = Path(r"F:\2026\24xs\99_产出\获客名单")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
# 采招网(bidcenter)对无 Referer 的请求返回 365 字节的诱饵页（真实内容 12-16 万字节）。
# 实测带一个搜索引擎 Referer 即可拿到完整正文。属于公开页面的正常访问头，
# 不绕过任何登录或付费墙。
REFERRER = {"Referer": "https://www.baidu.com/"}

# ---------------------------------------------------------------------------
# 种子 URL 全部来自搜索引擎实时检索结果，逐条对应真实公告。
# 抓取时以页面正文为准，若 URL 失效会在报告中显示 fail。
# ---------------------------------------------------------------------------
SEED_URLS = [
    "https://www.hcd-group.com/article/2059865244351729664",
    "https://www.ahrcu.com/anhuinongxin/xwzx/tzgg/cggg/2025122516305963495/index.shtml",
    "https://www.bidcenter.com.cn/newscontent-410378554-1.html",
    "https://www.bidcenter.com.cn/newscontent-407232686-1.html",
    "https://www.zhiliaobiaoxun.com/detail/600233223b128FC6E62d.html",
    "https://www.qianlima.com/bid-603414986.html",
    "https://www.bidcenter.com.cn/news-429603579-1.html",
    "https://www.bidcenter.com.cn/news-436769325-1.html",
    "https://www.bidcenter.com.cn/news-430114323-1.html",
]

# 聚合站自有服务联系方式（"郝工/标书代写/客服"），必须剔除，否则会当成采购人
AGGREGATOR_NOISE = re.compile(
    r"(郝工|标书代写|服务热线|咨询热线|客服|会员|注册|登录查看|"
    r"400-\d{3}-\d{4}|010-68960600|010-68960698|010-88123823|"
    r"1049263697|zjczw@163\.vip|"
    # 知了标讯运营方「北京百炼智能科技」的销售/客服总机，出现在每页页脚。
    # 实测青岛银行公告页里 采购人及监督电话 后紧跟的 ***[登录查看]*** 之后
    # 就是这个号，若不剔除会被当成银行采购电话。
    r"010-64933134|400-996-0039|400-688-2000)")

# 平台域名邮箱（不是采购人）
MAIL_NOISE = ("bidcenter", "qianlima", "zhiliao", "falv", "zhaobiao", "tujian",
              "tender", "example.com", "sina.com", "qq.com", "163.com",
              "126.com", "caitong", "auction", "360buy")

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# 手机 11 位，或固话 0xx-xxxxxxx / 0xxx-xxxxxxx。必须带分隔符或恰为 11 位，
# 否则会命中银行账号（如 010100100504）—— 这是上一轮抽取到的真实噪声。
PHONE_RE = re.compile(r"(?<!\d)(?:1[3-9]\d{9}|(?:0\d{2,3}-\d{7,8}))(?!\d)")

# 站点自身 JS 里的表单校验示例号 / 占位单位 / 付费墙标记
PLACEHOLDER_NOISE = re.compile(
    r"(如：|如:|errMsg|reg\.exec|请输入您的|示例|请输入手机号)")
PLACEHOLDER_CORP = ("指定设计院", "指定", "招标人", "采购人", "单位名称",
                    "某某", "某公司", "某单位", "略")
PAYWALL = ("登录查看", "注册/登录", "仅对千里马会员", "****", "点击查看")
MONEY_RE = re.compile(
    r"(?:最高限价|采购预算|预算金额|控制价|招标估价|限价|招标预算|项目预算)"
    r"[^\d元]{0,20}([\d,]+(?:\.\d+)?)\s*(万元|元)")

# 分类：先看强信号，避免「合同模板里出现『诉讼』二字」被误判为同行采购。
# 上一轮华昌达 ERP 采购公告就是被模板里的『诉讼』判成 service。
SERVICE_STRONG = ("律师事务所", "法律服务", "诉讼代理", "委外催收", "司法催收",
                  "全风险代理", "常年法律顾问", "催收代理", "催收服务采购")
SERVICE_WEAK = ("诉讼", "法律顾问", "律师")
AUDIT_HINT = ("专项审计", "会计师事务所", "核销审计", "审计机构", "执业证书")
SOLICIT = ("供应商征集", "供应商基本信息表", "资格预审", "注册供应商",
           "征集结果", "入围", "有意参与")
SYSTEM_STRONG = ("应收账款管理", "应收管理", "账龄", "回款分析", "催收管理",
                 "司库", "统一授信", "信用管理", "账务系统", "财务系统",
                 "应收账款", "授信")

CORP_RE = re.compile(
    r"([一-龥A-Za-z]{2,20}(?:股份有限公司|有限责任公司|有限公司|集团|"
    r"农村信用社|联合社|银行|研究院|设计院|控股))")

# 站点运营方 / 代理机构 / 平台商：这些不是采购人
NOT_PROCUREMENT = ("招标代理", "咨询", "项目管理", "信息", "网络科技", "易采",
                   "招标服务", "海诚通胜", "采招", "招标网", "科技有限")


def clean(html: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in [("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'),
                 ("&lt;", "<"), ("&gt;", ">")]:
        s = s.replace(a, b)
    return re.sub(r"[ \t\r\f\v]+", " ", s)


def classify(text: str) -> str:
    """强信号优先。弱信号仅在无强信号时生效。"""
    svc_strong = any(k in text for k in SERVICE_STRONG)
    sys_strong = any(k in text for k in SYSTEM_STRONG)
    # 同行判定需要「法律/催收服务」作为采购标的，而不是出现在合同条款里。
    # 判据：出现服务类强词，且同页没有把它写成系统采购模块。
    if svc_strong and not (sys_strong and "系统" in text and "平台" in text):
        return "service"
    if any(k in text for k in AUDIT_HINT):
        return "audit"
    if any(k in text for k in SOLICIT):
        return "supplier_solicitation"
    if sys_strong:
        return "erp_buying"
    if any(k in text for k in SERVICE_WEAK):
        return "service_weak"
    return "other"


def contact_block(text: str, raw: str = "") -> dict:
    """在「联系方式」区块内优先抽取，避免拿到页面中段任意号码。"""
    idx = text.rfind("联系方式")
    scope = text[idx:idx + 900] if idx > 0 else text

    # 邮箱：先扫「联系方式」区块，再扫全文，最后扫原始 HTML。
    # 关键点：采招网把采购人邮箱放在 script/JSON 块里，clean() 会把它删掉，
    # 只扫 clean 后的正文会漏掉 caishaohui@citicaibank.com 这类真实地址。
    emails, seen = [], set()

    def add_emails(hay: str, pre_check: bool = True) -> None:
        for m in EMAIL_RE.finditer(hay):
            e = m.group(0)
            low = e.lower()
            if low in seen or any(n in low for n in MAIL_NOISE):
                continue
            if pre_check:
                pre = hay[max(0, m.start() - 30):m.start()]
                if AGGREGATOR_NOISE.search(pre) or AGGREGATOR_NOISE.search(e):
                    continue
            seen.add(low)
            emails.append(e)

    add_emails(scope)
    add_emails(text)
    if raw:
        add_emails(raw, pre_check=False)  # 原始块无上下文，噪声词已在邮箱本身过滤

    # 电话：只认「贴着联系方式标签」的号码。裸号码在公告页里绝大多数是
    # 站点 JS 的表单示例号（errMsg='如：13611280101'）或银行账号。
    # raw 不参与电话抽取——raw 里的电话来自通用页脚，没有上下文。
    # 标签与号码之间允许夹一个人名，如「技术联系人 ：王工 15262566839」
    LABEL = re.compile(
        r"(?:联系电?话|电\s*话|电\s*话号码|手\s*机|移动电话|Tel|TEL|"
        r"联系方式|传\s*真|分机|邮\s*箱|E-?mail)"
        r"\s*[:：]?\s*(?:[一-龥A-Za-z]{0,4}\s*)?$")
    phones = []
    for hay in (scope, text):
        for m in PHONE_RE.finditer(hay):
            p = m.group(0).strip()
            if p in phones or AGGREGATOR_NOISE.search(p):
                continue
            pre = hay[max(0, m.start() - 24):m.start()]
            if not LABEL.search(pre):
                continue
            if PLACEHOLDER_NOISE.search(hay[max(0, m.start() - 60):m.start()]):
                continue
            phones.append(p)

    corp = ""
    for pat in [r"(?:招标人|采购人|招标单位|采购单位|建设单位|招标公司)\s*[:：]\s*"
                r"([^\s，,。;；、)（）]{4,30})"]:
        m = re.search(pat, scope)
        if m and not any(k in m.group(1) for k in NOT_PROCUREMENT):
            corp = m.group(1).strip()
            break
    if not corp:
        # 退到全文：取标题里出现过的第一个企业主体，而不是正文末尾的代理公司。
        best, pos = "", 10 ** 9
        for m in CORP_RE.finditer(text[:3000]):
            name = m.group(1)
            if any(k in name for k in NOT_PROCUREMENT):
                continue
            if m.start() < pos:
                best, pos = name, m.start()
        corp = best

    # 人名抽取：必须排除「联系」「电话」等被正则截断的伪人名。
    # 上一轮把「投标联系人：李丽」截成了「投标联系」。
    person = ""
    for pat in [r"(?:项目|采购|招标|投标)?联\s*系\s*人\s*[:：]\s*"
                r"([一-龥]{2,3}(?:先生|女士|老师|工|经理|总监|总)?)",
                r"联\s*系\s*人\s*[:：]\s*([一-龥]{2,3})"]:
        for m in re.finditer(pat, scope):
            cand = m.group(1).strip()
            # 伪人名：含「联系/电话/方式/地址/传真/邮箱/项目/采购/招标」
            if len(cand) < 2 or any(b in cand for b in (
                    "联系", "电话", "方式", "地址", "传真", "邮箱", "项目",
                    "采购", "招标", "投标", "信息", "如下", "详见")):
                continue
            person = cand
            break
        if person:
            break

    budget = ""
    m = MONEY_RE.search(text)
    if m:
        budget = f"{m.group(1)}{m.group(2)}"

    deadline = ""
    for pat in [r"(?:截止|开标|报名截止|投标截止)[^\d]{0,12}"
                r"((?:2026|2027)[-/年]\d{1,2}[-/月]\d{1,2})",
                r"((?:2026|2027)年\d{1,2}月\d{1,2}日)"]:
        m = re.search(pat, text)
        if m:
            deadline = m.group(1)
            break

    title = ""
    m = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    if m:
        title = re.sub(r"\s+", " ", clean(m.group(1))).strip()[:100]

    if corp and any(k in corp for k in PLACEHOLDER_CORP) or corp in ("****", ""):
        corp = ""
    # 邮箱域名必须与单位名有对应关系才算可信（citicaibank↔中信百信银行）。
    # 不做域名白名单猜测，只标记「域名可自证 / 无法自证」两档。
    domain_ok = ""
    if emails and corp:
        dom = emails[0].split("@")[-1].lower()
        core = re.sub(r"(股份|有限|责任|集团|银行|公司)", "", corp)
        stem = re.sub(r"[^a-z]", "", core.lower())
        domain_ok = "是" if (stem and stem in dom) or (
            core and len(core) >= 2 and core[:2] in dom) else "否"

    return {"标题": title, "单位": corp, "联系人": person,
            "邮箱": emails[0] if emails else "",
            "电话": phones[0] if phones else "",
            "邮箱域名自证": domain_ok,
            "含付费墙": "是" if any(w in scope for w in PAYWALL) else "否",
            "预算": budget, "截止": deadline}


def actionable(rec: dict) -> bool:
    """必须至少有一个人类可用的联系入口。

    若页面主体被付费墙遮挡（***[登录查看]***）且只剩平台客服电话，
    一律判为不可行动 —— 那种号码属于平台，不是采购人。
    """
    if not (rec.get("邮箱") or rec.get("电话")):
        return False
    if rec.get("含付费墙") == "是" and not rec.get("邮箱"):
        return False
    if not rec.get("单位"):
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls-file", help="每行一个公告 URL；不给则用内置种子")
    ap.add_argument("--out", help="输出 CSV 路径")
    args = ap.parse_args()

    if args.urls_file:
        urls = [l.strip() for l in
                Path(args.urls_file).read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
    else:
        urls = SEED_URLS

    stamp = datetime.date.today().strftime("%Y%m%d")
    out_csv = Path(args.out) if args.out else \
        OUT_DIR / f"招标联系人_{stamp}.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    rows, stat = [], {"ok": 0, "fail": 0}
    dist = {}
    now = datetime.datetime.now().isoformat(timespec="seconds")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=25) as c:
        for u in urls:
            hdr = {**REFERRER} if "bidcenter.com.cn" in u else {}
            # 某些站点的 302 目标 URL 含未编码的中文，httpx 带 cookie 重定向时会
            # 触发 UnicodeEncodeError（'ascii' codec）。逐请求清 cookie 即可。
            c.cookies.clear()
            try:
                r = c.get(u, headers=hdr)
                text = clean(r.text)
                if r.status_code != 200 or len(text) < 400:
                    print(f"  [fail] {r.status_code} len={len(text)}  {u[-56:]}")
                    stat["fail"] += 1
                    continue
            except Exception as e:
                print(f"  [fail] {type(e).__name__}  {u[-56:]}")
                stat["fail"] += 1
                continue

            cat = classify(text)
            dist[cat] = dist.get(cat, 0) + 1
            rec = contact_block(text, raw=r.text)
            rec.update({"分类": cat, "url": u, "抓取时间": now,
                        "可行动": "是" if actionable(rec) else "否"})
            rows.append(rec)
            stat["ok"] += 1
            tag = {"supplier_solicitation": "★可登记",
                   "erp_buying": "·自建系统",
                   "service": "×同行勿扰",
                   "audit": "×需审计资质"}.get(cat, "?")
            print(f"  {tag:10} {rec['单位'] or '(待确认)':22} "
                  f"{rec['联系人'] or '-':6} "
                  f"{rec['邮箱'] or rec['电话'] or '(无联系入口)':34} "
                  f"截止={rec['截止'] or '-'}")

    cols = ["单位", "联系人", "邮箱", "电话", "邮箱域名自证", "含付费墙",
            "标题", "分类", "可行动", "预算", "截止", "url", "抓取时间"]
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    act = [r for r in rows if r["可行动"] == "是"]
    print(f"\n[完成] {len(rows)} 条 -> {out_csv}")
    print(f"  抓取成功 {stat['ok']} / 失败 {stat['fail']}")
    print(f"  有可用联系入口: {len(act)}")
    print("  分类分布:", dist)
    for r in act:
        print(f"   * {r['单位']} | {r['联系人'] or '-'} | "
              f"{r['邮箱'] or '-'} | {r['电话'] or '-'} | {r['分类']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
