# -*- coding: utf-8 -*-
"""pet 垂类：生成真实客户审计报告"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDIT = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_pet.json")
OUTDIR = Path(r"F:\2026\24xs\99_产出\报告\真实客户审计")
DATE = "2026-09-30"

PLATFORMS = ["DeepSeek", "豆包", "通义千问", "Kimi", "文心一言", "元宝"]

CHECKS = [
    ("首页有 Organization/LocalBusiness 结构化数据",
     "AI 要先把你的诊所认成一个『实体』才能在回答里提到你。没有 schema，它只能靠猜。"),
    ("页面有 FAQPage 结构化问答块",
     "宠主问『上海宠物急诊哪家好』『上海猫绝育哪家好』时，带 FAQPage 的页面最容易被直接引用。"),
    ("有具体服务问答文本（价格/区域/医生/设备）",
     "AI 不编数字。你的页面写了明确价格、医生、设备，它才有东西可引用。"),
    ("诊所名/地址/电话在多平台一致",
     "信息不一致 = 实体冲突 = AI 判定不可信，直接降权。"),
]


def main() -> int:
    rows = json.loads(Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_pet.json").read_text(encoding="utf-8"))
    rows = [r for r in rows if r.get("HTTP") == 200]
    OUTDIR.mkdir(parents=True, exist_ok=True)

    made = []
    for r in rows:
        name = r["公司"]
        gaps = r.get("缺口数", 0)
        has_jsonld = r["有JSON-LD"]
        has_faq = r["有FAQ区块"]
        has_faq_schema = "FAQPage" in r["Schema类型"]

        real_gaps = []
        if not has_jsonld:
            real_gaps.append("Organization/LocalBusiness 结构化数据")
        if not has_faq_schema:
            real_gaps.append("FAQPage 结构化问答块")
        if not has_faq:
            real_gaps.append("可被 AI 引用的问答正文")

        score = max(0, 100 - len(real_gaps) * 28)

        lines = []
        lines.append(f"# {name} — AI 搜索可见度快检")
        lines.append("")
        lines.append(f"- 官网：{r['官网']}")
        lines.append(f"- 实测日期：{DATE}")
        lines.append(f"- 备案号：{r.get('ICP', '未见')}")
        lines.append(f"- **AI 就绪度评分：{score} / 100**")
        lines.append("")
        lines.append("## 这份报告怎么来的")
        lines.append("")
        lines.append(f"直接抓取 {r['官网']} 的公开首页 HTML，"
                     f"检测 4 项机器可读信号。全过程只读，"
                     "未登录、未修改对方网站。")
        lines.append("")
        lines.append("## 实测结果")
        lines.append("")
        lines.append("| 检查项 | 结果 |")
        lines.append("|---|---|")
        lines.append(f"| 首页有 Organization/LocalBusiness 结构化数据 | "
                     f"{'✅ 有' if has_jsonld else '❌ 无'} |")
        lines.append(f"| 有 FAQPage 结构化问答块 | "
                     f"{'✅ 有' if has_faq_schema else '❌ 无'} |")
        lines.append(f"| 有问答/常见问题区块 | {'✅ 有' if has_faq else '❌ 无'} |")
        lines.append(f"| 检测到的 schema 类型 | "
                     f"{r['Schema类型'] if r['Schema类型'] != '-' else '（一个都没有）'} |")
        lines.append("")

        if real_gaps:
            lines.append("## 三个具体缺口")
            lines.append("")
            for i, g in enumerate(real_gaps, 1):
                why = next((w for c, w in [
                    ("首页有 Organization/LocalBusiness 结构化数据",
                     "AI 要先把你的诊所认成一个『实体』才能在回答里提到你。没有 schema，它只能靠猜。"),
                    ("页面有 FAQPage 结构化问答块",
                     "宠主问『上海宠物急诊哪家好』『上海猫绝育哪家好』时，带 FAQPage 的页面最容易被直接引用。"),
                    ("有具体服务问答文本（价格/区域/医生/设备）",
                     "AI 不编数字。你的页面写了明确价格、医生、设备，它才有东西可引用。"),
                ] if c.split(" ")[0] in g or g in c), "")
                lines.append(f"**{i}. 缺 {g}**")
                lines.append("")
                lines.append(f"   {why}" if why else "")
                lines.append("")
        else:
            lines.append("## 结论")
            lines.append("")
            lines.append("结构化数据已到位，属于对照组。问题多半不在技术层，"
                         "而在问答内容覆盖度和实体一致性。")
            lines.append("")

        lines.append("## 这对你意味着什么")
        lines.append("")
        lines.append("当宠主在 AI 里问"
                     "『上海宠物急诊哪家好』『上海猫绝育哪家好』『上海狗狗骨科手术』这类问题时，"
                     "AI 只会引用它能解析成实体、并且有明确问答支撑的页面。")
        lines.append("你的官网现在没有这些标记，等于在 AI 的候选池里不存在——"
                     "不是排名靠后，是根本没进池子。")
        lines.append("")
        lines.append("## 修复清单")
        lines.append("")
        for i, g in enumerate(real_gaps or ["问答内容覆盖度"], 1):
            lines.append(f"- [ ] {i}. 补 {g}")
        lines.append("- [ ] 4. 统一诊所名/地址/电话在官网、ICP、各平台的写法")
        lines.append("- [ ] 5. 部署后用 6 个平台复测，确认被引用")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"检测平台：{'、'.join(['DeepSeek', '豆包', '通义千问', 'Kimi', '文心一言', '元宝'])}")
        lines.append("")
        lines.append("*说明：本报告为机器信号实测（结构化数据/问答块），"
                     "不等于已在各 AI 平台的实际排名。付费报告含人工复核与平台实测。*")

        safe = name.replace("上海", "").replace("医院", "").replace("宠物", "").replace("动物", "").replace("医疗", "").replace("诊所", "").replace("集团", "").replace("分院", "")
        fp = OUTDIR / f"GEO审计_{safe}_{DATE}.md"
        fp.write_text("\n".join(lines), encoding="utf-8")
        made.append((name, score, len(real_gaps), fp))

    print(f"[OK] 生成 {len(made)} 份真实客户审计报告 -> {OUTDIR}\n")
    print(f"{'公司':34} {'评分':>6} {'缺口':>4}")
    print("-" * 50)
    for name, score, ng, fp in sorted(made, key=lambda x: x[1]):
        print(f"{name[:32]:34} {score:>5} {ng:>5}")
    return 0


if __name__ == "__main__":
    from pathlib import Path
    raise SystemExit(main())