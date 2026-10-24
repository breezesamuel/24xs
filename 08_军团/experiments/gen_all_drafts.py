# -*- coding: utf-8 -*-
"""统一外发草稿生成器 —— 唯一入口。

之前有 5 个各自为政的 gen_*_eml.py，各自带一份硬编码公司名单和硬编码
报告文件名。后果是名单和报告两套命名规则各走各的，实测：
  - 24 封草稿里 18 封正文写"见附件"但**根本没有附件**
  - 有附件的 6 封附的是 .md，正文却说"我把 PDF 发您"
  - 21 封正文写"整改报价（6–15 万）"，与系统硬下限 221,000 冲突
  - 24 封都写"加微信 460123249（同 QQ）"，但微信从未配置过

本脚本改为：
  名单  = 真实名单_*.csv（唯一事实来源）
  报告  = 报告/真实客户审计/*.md（唯一事实来源，靠公司名模糊匹配）
  附件  = 报告转 HTML，自带样式，浏览器直接打开即可打印成 PDF

四条硬闸门，任何一条不过就不落盘：
  1. 收件人必须能从 CSV 解析出合法邮箱或电话
  2. 报告必须解析到真实存在的文件，解析不到就跳过并报错
  3. 附件必须非空
  4. 正文不得出现低于硬下限的报价，也不得冒充微信

用法：python -X utf8 gen_all_drafts.py            # 生成
      python -X utf8 gen_all_drafts.py --check    # 只体检不写
"""
from __future__ import annotations

import argparse
import csv
import email.message
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(r"F:\2026\24xs\01_引擎")))
sys.stdout.reconfigure(encoding="utf-8")

import phoneutil  # noqa: E402

ROOT = Path(r"F:\2026\24xs")
LEAD_DIR = ROOT / "99_产出" / "获客名单"
REPORT_DIR = ROOT / "99_产出" / "报告" / "真实客户审计"
EML_DIR = ROOT / "99_产出" / "外发草稿"
STAGE_DIR = ROOT / "99_产出" / "外发草稿" / "_staging"

# 官网归属核验结论。由 verify_domain_ownership.py 产出，生成草稿只读不联网 ——
# 联网核验和网络抖动是两回事，让生成流程依赖实时网络的话，某天断网
# 就会把所有线索一起阻断，没人分得清是真有问题还是没网。
SITE_VERDICT: dict = {}
_sv = LEAD_DIR / "域名归属核验.json"
if _sv.exists():
    import json as _json
    SITE_VERDICT = _json.loads(_sv.read_text(encoding="utf-8"))

DATE = "2026-09-30"
EMAIL_FROM = "460123249@qq.com"
QQ = "460123249"
FLOOR = 221_000

# 公司名里这些词在报告文件名里会被剥掉，做匹配时要对齐
STRIP = ("婚礼", "婚庆", "艺术", "中心", "会馆", "公司", "服务", "一站式",
         "少儿", "编程", "教育", "科技", "成长", "医院", "门诊", "口腔",
         "装饰", "工程", "设计", "宠物", "国际", "连锁", "集团", "有限",
         "美容", "培训", "学院", "宝贝", "计划", "成长中心")

INDUSTRY_TAIL = {
    "wedding": "婚礼顾问 / 市场部",
    "dental": "前台 / 市场部",
    "pet": "前台 / 市场部",
    "kidscode": "课程顾问 / 市场部",
    "decoration": "业务负责人 / 市场部",
}

QUERY = {
    "wedding": ["上海婚庆公司推荐", "上海婚礼策划多少钱", "上海草坪婚礼场地"],
    "dental": ["上海牙科诊所推荐", "上海种植牙多少钱", "上海洗牙价格"],
    "pet": ["上海宠物医院推荐", "上海宠物医院价格", "上海猫咪绝育多少钱"],
    "kidscode": ["上海少儿编程机构推荐", "上海少儿编程多少钱", "上海编程课哪家好"],
    "decoration": ["上海装修公司推荐", "上海装修多少钱一平", "上海全屋定制哪家好"],
}

# 搜索人群的叫法。这个必须按垂类走 —— 之前正文里写死了"备婚人群"，
# 结果给口腔诊所的信也在讲"备婚人群在 AI 里问上海婚庆公司推荐"。
AUDIENCE = {
    "wedding": "备婚人群",
    "dental": "有牙齿问题的上海市民",
    "pet": "养猫养狗的宠物主",
    "kidscode": "给孩子找编程课的家长",
    "decoration": "正在装修的业主",
}

# 报价闸门：与 audit_drafts.py 用同一套 dash 变体
DASHES = "\u002d\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFF0D\u30FC\u007E"
PRICE_PAT = re.compile(r"(\d+)\s*(?:[" + DASHES + r"]|到|至)\s*(\d+)\s*(万|w|W|千|k|K)")
WEHAT_PAT = re.compile(r"(?:加微|微信\s*[:：]?\s*|微信号\s*(?:是|为|:|：)?\s*)" + QQ + r"|同\s*QQ")


def norm(s: str) -> str:
    s = re.sub(r"[\s\u3000()（）()\[\]【】·、,，.。/\\\-—_]", "", s or "")
    for w in STRIP:
        s = s.replace(w, "")
    return s


# 行业列的取值来自各个 build_*_csv.py，彼此不一致：
#   wedding / pet_clinic / dental_clinic / kids_coding / home_improvement
# 而下面三张表统一用短 key。漏了归一化，24/27 封草稿会静默退回
# 通用文案（"本地客户在 AI 里问『本地服务推荐』"），客户一眼看出没做功课。
IND_ALIAS = {
    "wedding": "wedding", "wedding_planner": "wedding",
    "pet": "pet", "pet_clinic": "pet", "pet_hospital": "pet",
    "dental": "dental", "dental_clinic": "dental", "dental_hospital": "dental",
    "kidscode": "kidscode", "kids_coding": "kidscode", "kids": "kidscode",
    "coding": "kidscode", "education": "kidscode",
    "decoration": "decoration", "home_improvement": "decoration",
    "renovation": "decoration", "interior": "decoration",
}
# CSV 文件名 -> 短 key（行业列缺失时兜底）
FILE_HINT = {
    "婚庆": "wedding", "口腔": "dental", "宠物": "pet",
    "编程": "kidscode", "装修": "decoration",
}


def industry_of(fname: str, row: dict) -> str:
    raw = (row.get("行业") or "").strip().lower()
    if raw in IND_ALIAS:
        return IND_ALIAS[raw]
    for k, v in IND_ALIAS.items():
        if raw and k in raw:
            return v
    for k, v in FILE_HINT.items():
        if k in fname:
            return v
    return ""


def find_report(company: str) -> Path | None:
    """公司全名 -> 报告文件。报告名做过词条剥离，所以双向模糊匹配。"""
    target = norm(company)
    if not target:
        return None
    cands = list(REPORT_DIR.glob("*.md"))
    for p in cands:
        stem = norm(p.stem.replace("GEO审计_", "").rsplit("_", 1)[0])
        if stem == target:
            return p
    for p in cands:
        stem = norm(p.stem.replace("GEO审计_", "").rsplit("_", 1)[0])
        if target and (target in stem or stem in target):
            return p
    # 再退一步：报告正文里出现完整公司名
    for p in cands:
        try:
            head = p.read_text(encoding="utf-8")[:400]
        except OSError:
            continue
        if company and company in head:
            return p
    return None


def md_to_html(md: str, title: str) -> str:
    """极简 Markdown -> HTML。够用即可，不引第三方依赖。"""
    def esc(s: str) -> str:
        return html.escape(s, quote=False)

    def inline(s: str) -> str:
        s = esc(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        s = re.sub(r"(?<!\()\b((?:https?)://[^\s<）)]+)", r'<a href="\1">\1</a>', s)
        return s

    out, in_list, in_table = [], False, False

    def close_blocks():
        nonlocal in_list, in_table
        if in_list:
            out.append("</ul>")
            in_list = False
        if in_table:
            out.append("</table>")
            in_table = False

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_blocks()
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue                      # 分隔行
            if not in_table:
                close_blocks()
                out.append("<table>")
                in_table = True
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_blocks()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            continue
        if re.match(r"^\s*[-*]\s+", line):
            if not in_list:
                close_blocks()
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(re.sub(r'^\s*[-*]\s+', '', line))}</li>")
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            if not in_list:
                close_blocks()
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(re.sub(r'^\s*\d+\.\s+', '', line))}</li>")
            continue
        if line.startswith("---"):
            close_blocks()
            out.append("<hr>")
            continue
        close_blocks()
        out.append(f"<p>{inline(line)}</p>")

    close_blocks()

    css = """
  :root { color-scheme: light }
  * { box-sizing: border-box }
  body { font: 15px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
         max-width: 760px; margin: 0 auto; padding: 40px 24px; color: #1a1a1a;
         background: #fff }
  h1 { font-size: 25px; line-height: 1.35; margin: 0 0 24px;
       padding-bottom: 16px; border-bottom: 3px solid #e11d48 }
  h2 { font-size: 19px; margin: 34px 0 12px; padding-left: 11px;
       border-left: 4px solid #e11d48 }
  h3 { font-size: 16px; margin: 22px 0 8px }
  table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 14px }
  td { border: 1px solid #e5e5e5; padding: 9px 11px }
  tr:first-child td { background: #fafafa; font-weight: 600 }
  ul { padding-left: 22px; margin: 10px 0 }
  li { margin: 5px 0 }
  code { background: #f4f4f5; padding: 2px 6px; border-radius: 4px; font-size: 13px }
  a { color: #e11d48; word-break: break-all }
  strong { color: #111 }
  hr { border: 0; border-top: 1px solid #e5e5e5; margin: 30px 0 }
  p { margin: 10px 0 }
  @media print {
    body { padding: 0; max-width: none }
    h2 { page-break-after: avoid }
    table, li { page-break-inside: avoid }
  }
"""
    return (f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{css}</style></head>'
            f'<body>{"".join(out)}</body></html>')


def compose(company: str, ind: str, rep_html_name: str) -> tuple[str, str]:
    """返回 (主题, 正文)。口径统一在这里，所有垂类共用。"""
    role = INDUSTRY_TAIL.get(ind, "市场部")
    qs = QUERY.get(ind, ["本地服务推荐", "多少钱"])
    aud = AUDIENCE.get(ind, "本地客户")
    subject = f"【GEO 诊断】{company} — AI 搜不到贵司，附实测快检报告"
    body = f"""{role} 您好：

我做 AI 搜索可见度（GEO）诊断。最近实测了贵司官网，发现一个很具体的问题：

{aud}在 AI 里问「{qs[0]}」「{qs[1]}」这类问题的时候，
主流 AI 答案里基本不提贵司。

说直白点：这不是文案写得好不好的问题，而是贵司官网缺少 AI 能读懂的机器信号
（结构化数据、问答块、价格、案例），搜索引擎抓得到，但 AI 引用不了。

我已按公开官网实测生成《{company} AI 搜索可见度快检》（附件，HTML 格式，
浏览器直接打开即可，也可打印成 PDF），里面只有机器真检测到的缺口，
不含臆造内容，也不承诺排名。

不卖课、不推工具。如果觉得有用，我们按缺口项出整改报价（按项结算，
不达标不收尾款）。

直接回本邮件即可，或用 QQ {QQ} 找我。

不打扰了，祝生意兴隆。

——
GEO 诊断快检
mailto:{EMAIL_FROM}
"""
    return subject, body


def validate(body: str, subject: str, att_bytes: bytes | None, to_addr: str,
             has_phone: bool, ind: str) -> list[str]:
    errs = []
    if not ind:
        errs.append("垂类无法识别，会退回通用文案——宁可不发")
    if not to_addr and not has_phone:
        errs.append("无有效收件人（邮箱与电话均不可用）")
    m = PRICE_PAT.search(body)
    if m:
        hi = int(m.group(2)) * (10000 if m.group(3) in "万wW" else 1000)
        if hi < FLOOR:
            errs.append(f"报价 {m.group(0)} 上限低于硬下限 {FLOOR:,}")
    if WEHAT_PAT.search(body):
        errs.append("正文冒充微信（CONTACT_WECHAT 未配置）")
    if "见附件" in body or "附件" in subject:
        if not att_bytes:
            errs.append("正文承诺附件但附件为空")
    if att_bytes is not None and len(att_bytes) < 500:
        errs.append(f"附件过小（{len(att_bytes)}B），疑似空报告")
    # 正文必须真的用上了本垂类的搜索词，否则就是套模板
    for kw in QUERY.get(ind, [])[:1] + [AUDIENCE.get(ind, "\0")]:
        if kw != "\0" and kw not in body:
            errs.append(f"正文缺少本垂类关键词 {kw!r}")
    return errs


# 外地区号，用来提示"公司名写上海、电话却是外地"的存疑行
FOREIGN_AREA = {
    "010": "北京", "020": "广州", "021": "上海", "022": "天津", "023": "重庆",
    "024": "沈阳", "025": "南京", "027": "武汉", "028": "成都", "029": "西安",
    "0531": "济南", "0755": "深圳", "020": "广州",
}


def city_area_mismatch(city: str, phone: str) -> str | None:
    """公司名标上海、座机却是外地区号 -> 存疑，返回说明。"""
    if "上海" not in (city or "") or not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    m = re.match(r"(0\d{2,3})", digits)
    if not m:
        return None
    # 必须按最长区号优先试：01053822160 若先取 4 位会得到 "0105"，
    # 查不到归属就静默放过。真实区号是 3 位的 010。
    raw = m.group(1)
    code = None
    for n in (4, 3):
        cand = raw[:n]
        if cand in phoneutil.AREA_CODES:
            code = cand
            break
    if not code:
        return None
    owner = FOREIGN_AREA.get(code)
    if owner and owner != "上海":
        return f"名单城市=上海，但电话区号 {code} 属{owner}"
    return None


def dedupe(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """同一主体只留一行。

    主键用联系方式而不是公司名 —— 实测"宠爱国际连锁动物医院"和
    "宠爱国际连锁"归一化后并不相等（"动物"没被剥离），但邮箱、
    电话、官网、备案号全都一样，是同一家。只按名字去重会漏掉。
    """
    best: dict[str, dict] = {}
    notes: list[str] = []

    def quality(r: dict) -> int:
        return (2 if (r.get("邮箱") or "").strip() else 0) \
             + (1 if phoneutil.is_valid((r.get("电话") or "").strip()) else 0)

    def key_of(r: dict) -> str:
        mail = (r.get("邮箱") or "").strip().lower()
        if mail:
            return f"mail:{mail}"
        tel = (r.get("电话") or "").strip()
        if phoneutil.is_valid(tel):
            return f"tel:{phoneutil.normalize(tel)}"
        return f"name:{norm(r.get('公司') or '')}"

    for r in rows:
        k = key_of(r)
        if not k.split(":", 1)[1]:
            continue
        cur = best.get(k)
        if cur is None:
            best[k] = r
            continue
        same_mail = (r.get("邮箱") or "").strip() == (cur.get("邮箱") or "").strip()
        same_tel = (r.get("电话") or "").strip() == (cur.get("电话") or "").strip()
        if same_mail and same_tel:
            notes.append(f"重复行（联系方式完全一致）已合并: {cur['公司']} / {r['公司']}")
        elif quality(r) > quality(cur):
            notes.append(f"重复主体，改用联系方式更全的一条: {r['公司']}（原保留 {cur['公司']}）")
            best[k] = r
        else:
            notes.append(f"重复主体但联系方式不同，需人工判定: {cur['公司']} / {r['公司']}")
    return list(best.values()), notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只体检，不写文件")
    args = ap.parse_args()

    if not args.check:
        STAGE_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    csvs = [p for p in sorted(LEAD_DIR.glob("真实名单_*.csv")) if ".bak-" not in p.name]
    for csvp in csvs:
        with csvp.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                r["_src"] = csvp.name
                r["_ind"] = industry_of(csvp.name, r)
                rows.append(r)
    rows, notes = dedupe(rows)
    if notes:
        print("去重告警：")
        for n in notes:
            print(f"  · {n}")
        print()

    print(f"去重后真实名单 {len(rows)} 条")
    print("=" * 78)

    staged, blocked, used_names = [], [], set()
    for r in rows:
        company = (r.get("公司") or "").strip()
        raw_mail = (r.get("邮箱") or "").strip()
        raw_phone = (r.get("电话") or "").strip()
        mail = raw_mail if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]{2,}", raw_mail) else ""
        # 必须用 is_valid，不能用 normalize。
        # normalize 只清洗格式，0368738174 / 00300000009 这种网页噪音串
        # 能原样通过 normalize —— 上一版闸门就是这么漏的。
        phone = phoneutil.normalize(raw_phone) if phoneutil.is_valid(raw_phone) else ""
        ind = r["_ind"]

        warn = city_area_mismatch(r.get("城市", ""), phone)
        if warn:
            print(f"  [存疑] {company[:22]:24} {warn}")

        # 官网归属核验：报告写的是"抓取 <官网> 得出 N 分"。
        # 如果这个官网不是对方自己的站，那这份报告就是拿别人的网站
        # 去指认别人的问题 —— 发出去不是无效，是有害。
        # 实测三例：爱侣宠物医院集团 -> ruichen.com（南京瑞辰）、
        # 爱侣宠物医院 -> shanghaivet.com（上海爪爪）、
        # 宠瑞动物医疗 -> 35237241.1.net.cn（共享主机数字域名）。
        own = SITE_VERDICT.get(company)
        if own is None:
            blocked.append((company, "无官网归属核验结论，先跑 "
                                     "verify_domain_ownership.py"))
            continue
        if own["status"] != "ok":
            blocked.append((company, f"官网归属存疑（{own['status']}）："
                                     f"{own['reason']}"))
            continue

        rep = find_report(company)
        if rep is None:
            blocked.append((company, "报告解析不到，草稿不予生成"))
            continue

        md = rep.read_text(encoding="utf-8")
        title = company
        att_html = md_to_html(md, title)
        att_bytes = att_html.encode("utf-8")

        subject, body = compose(company, ind, rep.stem)
        errs = validate(body, subject, att_bytes, mail, bool(phone), ind)
        if errs:
            blocked.append((company, "; ".join(errs)))
            continue

        tail = re.sub(r"\D", "", phone)[-4:] or "0000"
        stem = re.sub(r"[^一-鿿A-Za-z0-9]", "", company)
        name = f"外发_{stem}_{tail}.eml"
        if name in used_names:                 # 尾号只取后4位，理论上会撞
            n = 2
            while f"外发_{stem}_{tail}_{n}.eml" in used_names:
                n += 1
            name = f"外发_{stem}_{tail}_{n}.eml"
            print(f"  [撞名] {company[:22]:24} 文件名已加后缀 -> {name}")
        used_names.add(name)

        msg = email.message.EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = mail
        msg["Subject"] = subject
        msg["X-Contact-Phone"] = phone or "pending"
        msg.set_content(body)
        msg.add_attachment(att_bytes, maintype="text", subtype="html",
                           filename=f"{title}_AI可见度快检.html")
        blob = msg.as_bytes()

        if not args.check:
            (STAGE_DIR / name).write_bytes(blob)
        staged.append((company, mail, phone, name, len(att_bytes)))

    for company, mail, phone, name, size in staged:
        print(f"  [OK]   {company[:22]:24} -> {mail or '仅电话':24} 附件 {size:,}B  {name}")
    print()
    for company, why in blocked:
        print(f"  [BLOCK] {company[:22]:24} {why}")

    print()
    print("=" * 78)
    print(f"可生成 {len(staged)} 封 / 阻断 {len(blocked)} 条 / 共 {len(rows)} 条")
    if blocked:
        print("被阻断的不会落盘——宁可少发，不可发错。")
    print("=" * 78)

    if not args.check:
        EML_DIR.mkdir(parents=True, exist_ok=True)
        for old in EML_DIR.glob("外发_*.eml"):
            old.unlink()
        n = 0
        for fp in sorted(STAGE_DIR.glob("外发_*.eml")):
            (EML_DIR / fp.name).write_bytes(fp.read_bytes())
            n += 1
        for fp in STAGE_DIR.glob("*.eml"):
            fp.unlink()
        print(f"已提交 {n} 封到 {EML_DIR}")

    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
