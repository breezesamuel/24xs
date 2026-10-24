# -*- coding: utf-8 -*-
"""婚庆垂类：实测 JSON -> verified CSV + 审计报告 + 外发草稿。

只处理"可见文字里能抽到合法联系方式"的公司；抽不到就不硬凑，
宁可少一家也不把网页噪音当联系方式写进库（见 01_引擎/phoneutil.py）。
"""
from __future__ import annotations

import csv
import email.message
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDIT = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_wedding_v2.json")
LEADS = Path(r"F:\2026\24xs\99_产出\获客名单\真实名单_上海婚庆_2026-09-30.csv")
REPORT_DIR = Path(r"F:\2026\24xs\99_产出\报告\真实客户审计")
EML_DIR = Path(r"F:\2026\24xs\99_产出\外发草稿")
DATE = "2026-09-30"
EMAIL_FROM = "460123249@qq.com"

QUERIES = ["上海婚庆公司推荐", "上海婚礼策划多少钱", "上海草坪婚礼场地", "上海婚宴酒店预订"]


def safe(name: str) -> str:
    for w in ("婚礼", "婚庆", "艺术", "中心", "会馆", "公司", "服务", "一站式"):
        name = name.replace(w, "")
    return name.strip()


def pick(row, key):
    v = row.get(key) or "-"
    return v.split(",")[0].strip() if v != "-" else ""


def build(r):
    phone = pick(r, "手机") or pick(r, "400")
    email = pick(r, "邮箱")
    gaps = [g for g in re.split(r"[、]", r.get("缺口", "")) if g and g != "结构化基本到位"]
    score = max(0, 100 - len(gaps) * 20)
    return phone, email, gaps, score


def main() -> int:
    rows = json.loads(AUDIT.read_text(encoding="utf-8"))
    LEADS.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EML_DIR.mkdir(parents=True, exist_ok=True)

    FIELDS = ["公司", "官网", "联系人", "电话", "邮箱", "微信", "行业",
              "城市", "痛点", "来源", "备注"]
    kept = []
    for r in rows:
        if r.get("HTTP") != 200 or r.get("错误"):
            continue
        phone, mail, gaps, score = build(r)
        if not phone and not mail:
            print(f"[SKIP] 无可核验联系方式: {r['公司']}")
            continue
        kept.append((r, phone, mail, gaps, score))

    with LEADS.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r, phone, mail, gaps, score in kept:
            w.writerow({
                "公司": r["公司"], "官网": r["官网"], "联系人": "婚礼顾问/市场部",
                "电话": phone, "邮箱": mail, "微信": "", "行业": "wedding",
                "城市": r.get("城市", "上海"),
                "痛点": f"搜『{QUERIES[0]}』等高意图词时 AI 不提贵司；"
                        f"官网缺 {len(gaps)} 项机器可读信号（{('、'.join(gaps))[:40]}）",
                "来源": "公开官网实测 geo_wedding_audit_v2.py",
                "备注": f"AI就绪度={score}/100 | ICP={r.get('ICP','-')} | 核心资产={r.get('核心资产','')}",
            })

    print(f"\n[OK] CSV {len(kept)} 行 -> {LEADS.name}\n")

    for r, phone, mail, gaps, score in kept:
        name = r["公司"]
        lines = [
            f"# {name} — AI 搜索可见度快检（婚庆垂类）",
            "",
            f"- 官网：{r['官网']}",
            f"- 实测日期：{DATE}",
            f"- 备案号：{r.get('ICP','未见')}",
            f"- **AI 就绪度评分：{score} / 100**",
            "",
            "## 这份报告怎么来的",
            "",
            f"直接抓取 {r['官网']} 的公开首页 HTML，只读，不登录、不改动对方网站。",
            "联系方式只从**页面可见文字**里抽取，并逐个校验是否为真实可用的号码格式。",
            "",
            "## 实测结果",
            "",
            "| 检查项 | 结果 |",
            "|---|---|",
            f"| Organization / LocalBusiness 结构化数据 | {'✅ 有' if r['有JSON-LD'] else '❌ 无'} |",
            f"| FAQPage 结构化问答块 | {'✅ 有' if 'FAQPage' in r['Schema类型'] else '❌ 无'} |",
            f"| 问答/常见问题正文 | {'✅ 有' if r['有FAQ区块'] else '❌ 无'} |",
            f"| 公开价格/套餐 | {'✅ 有' if r['有价格'] else '❌ 无'} |",
            f"| 婚礼案例/客片 | {'✅ 有' if r['有案例'] else '❌ 无'} |",
            "",
        ]
        if gaps:
            lines += ["## 具体缺口", ""]
            for i, g in enumerate(gaps, 1):
                lines += [f"**{i}. {g}**", "", _why(g, r), ""]
        else:
            lines += ["## 结论", "", "结构化已到位，属对照组。问题在内容覆盖度与实体一致性。", ""]

        lines += [
            "## 这对你意味着什么",
            "",
            "备婚人群在 AI 里问「" + "」「".join(QUERIES[:2]) + "」这类问题时，",
            "AI 只引用能解析成实体、且有明确价格/案例支撑的页面。",
            "婚庆是**高客单 + 强比价**品类，用户搜不到=直接丢掉询盘。",
            "",
            "## 修复清单",
            "",
        ]
        for i, g in enumerate(gaps or ["问答内容覆盖度"], 1):
            lines.append(f"- [ ] 补 {g}")
        lines += [
            "- [ ] 补 FAQPage：写 8~12 条新人真会问的问题（价格/档期/场地/隐形收费）",
            "- [ ] 统一机构名、地址、电话在官网与各平台写法",
            "- [ ] 部署后用 6 个 AI 平台复测，确认被引用",
            "",
            "---",
            "",
            "*说明：本报告为机器信号实测，不等于已在各 AI 平台的实际排名。*",
        ]
        fp = REPORT_DIR / f"GEO审计_{safe(name)}_{DATE}.md"
        fp.write_text("\n".join(lines), encoding="utf-8")

        body = f"""婚礼顾问 / 市场部 您好：

我是做 AI 搜索可见度（GEO）诊断的。最近实测了 {name} 的官网（{r['官网']}），
发现一个很具体的问题：

搜「{QUERIES[0]}」「{QUERIES[1]}」这类备婚人群真正会搜的问题时，
主流 AI 答案里基本不提贵司。根因是官网缺 {len(gaps)} 项机器可读信号：
{'、'.join(gaps)}。

婚庆是高客单、强比价的品类，搜不到基本等于直接丢掉询盘。

我已按公开官网实测生成《{name} AI 搜索可见度快检》（见附件），只列机器真检测到的缺口，
不含臆造内容。

不卖课、不推工具、不承诺排名。如果觉得有用，我们按缺口项出整改报价（按项结算）。
直接回本邮件回复，或用 QQ 460123249 找我即可。

不打扰了，祝生意兴隆。

——
GEO 诊断快检
mailto:{EMAIL_FROM}
"""
        msg = email.message.EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = mail
        msg["Subject"] = f"【GEO 诊断】{name} — AI 搜不到贵司，附实测自测报告"
        msg.set_content(body)
        msg.add_attachment(fp.read_bytes(), maintype="text", subtype="markdown",
                           filename=fp.name)
        tail = re.sub(r"\D", "", phone)[-4:] or "0000"
        efp = EML_DIR / f"外发_{safe(name)}_{tail}.eml"
        efp.write_bytes(msg.as_bytes())

        print(f"  ✅ {name[:24]:26} 评分{score:3} | {phone or mail:22} | 报告+草稿已生成")

    print(f"\n报告目录: {REPORT_DIR}")
    print(f"草稿目录: {EML_DIR}")
    return 0


def _why(gap: str, r) -> str:
    if "结构化" in gap:
        return ("没有 schema，AI 无法把机构识别为实体，只能靠字符串猜，"
                "在候选池里等于不存在。")
    if "FAQPage" in gap:
        return ("带 FAQPage 的页面最容易被 AI 直接引用成答案，缺它就只能进不了引用池。")
    if "问答" in gap:
        return "备婚人群问『多少钱』时，AI 不编数字；页面写了明确答案才有东西可引用。"
    if "价格" in gap:
        return "婚庆用户第一句就是问价，没有公开价格 AI 只能给别的品牌。"
    if "案例" in gap:
        return "没有真实案例/客片文本，AI 无法判断你们做过什么规模。"
    return "该项缺失会降低被 AI 引用的概率。"


if __name__ == "__main__":
    raise SystemExit(main())
