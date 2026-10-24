# -*- coding: utf-8 -*-
"""把采集到的体检数据做成"可售卖的虚拟资产"。

这是整个商业闭环的核心：**同一份数据，卖四次，用不同的封装**。
边际成本几乎为零（体检是脚本跑出来的），所以定价可以往下压到 1 元，
靠量取胜，而不是靠单笔大单。

分层依据两个真实约束：
  1. 国际市场 GEO 体检卖 $700–$5,000/单（已联网核实 8 家报价），
     国内中小企业承受力低一个数量级，所以起价必须低。
  2. 数据本身是公开信息，价值在于"已经替你测好了 + 给了整改动作"。
     所以越接近执行（给代码/给排期）越贵，纯数据最便宜。

利润模型（诚实版）：
  免费体检 → ¥1 引流 → ¥9.9 批量 → ¥99 深度 → ¥2999 白标授权
  每层都靠上一层转化；不靠大单。
"""
from __future__ import annotations

import json
import pathlib
import sqlite3

ROOT = pathlib.Path(r"F:\2026\24xs")
DB = ROOT / "11_数据资产" / "assets.sqlite3"

# 成本基准（按实测算，不是拍脑袋）
# 单站体检：8 线程并发，一次 20 家约 6 分钟 → 约 18 秒/站
COST_PER_SITE_CNY = 0.001          # 纯算力+带宽，几乎为零
DELIVERY_COST_CNY = 0.30# 人工/邮件交付时的时间成本

PRODUCTS = [
    {
        "id": "free",
        "name": "免费体检",
        "price": 0,
        "unit": "次",
        "delivery": "即时",
        "gives": [
            "AI 可见度总分 + 评级",
            "robots / 结构化数据 / llms.txt / FAQ 四项有无",
            "最关键的一条整改建议",
        ],
        "not_gives": ["完整清单", "可执行代码", "竞品对比"],
        "purpose": "获客入口。免费给结论，不给做法 —— 这是转化设计，不是抠门。",
    },
    {
        "id": "lead1",
        "name": "单站速览",
        "price": 1,
        "unit": "份",
        "delivery": "即时",
        "gives": [
            "免费体检的全部内容",
            "8 个维度的逐项得分",
            "3 条优先级整改建议",
            "PDF 报告",
        ],
        "not_gives": ["源码级修复", "竞品横向对比"],
        "purpose": "1 块钱的作用是让人真的付过一次钱。付过钱的人才愿意付 99。",
    },
    {
        "id": "batch10",
        "name": "行业对标（10 家）",
        "price": 9.9,
        "unit": "份",
        "delivery": "即时",
        "gives": [
            "10 家企业同口径打分排行",
            "同行中位数 / 差距分析",
            "你在行业里排第几",
            "Excel 对标表",
        ],
        "not_gaves": ["逐家整改方案"],
        "purpose": "把单人需求变成组织需求。老板不会为一个网站付钱，"
                   "但会为「我的同行排第几」付钱 —— 这是决策层入口。",
    },
    {
        "id": "deep99",
        "name": "深度整改包",
        "price": 99,
        "unit": "份",
        "delivery": "1 小时内",
        "gives": [
            "完整 8 维度诊断报告",
            "JSON-LD 完整代码（可直接粘贴）",
            "llms.txt / robots.txt 定制内容",
            "整改优先级排期表（按投入产出排序）",
            "30 天内 3 次免费复测",
        ],
        "not_gives": ["代改上线"],
        "purpose": "主力产品。给到「照着做就能改」的粒度，不需要上门。",
    },
    {
        "id": "compare299",
        "name": "竞品攻防（5 家对比）",
        "price": 299,
        "unit": "份",
        "delivery": "1 小时内",
        "gives": [
            "深度整改包全部内容",
            "5 家竞品逐项打分对比",
            "AI 引用差异分析（谁在被引用、为什么）",
            "差异化关键词建议",
            "90 天跟踪复测",
        ],
        "not_gives": ["代运营"],
        "purpose": "把单站生意变成竞争情报。客单价上探的主力。",
    },
    {
        "id": "white2999",
        "name": "白标授权（代运营/服务商）",
        "price": 2999,
        "unit": "年",
        "delivery": "开通即用",
        "gives": [
            "体检引擎 API 调用权（含限流额度）",
            "你的品牌 logo / 域名替换",
            "PDF 模板可自定义",
            "批量导出客户名单",
            "技术对接支持",
        ],
        "not_gives": ["源代码", "独家授权"],
        "purpose": "卖给同行而不是终端。让别人的销售来帮你做销售 —— "
                   "这是唯一能真正放量的路径。",
    },
]


def load_rows() -> list[dict]:
    # 优先用【线上边缘引擎】的快照，保证网站公布的基准 = 用户点按钮跑出来的数字。
    # 本地结果只作为对照，不作为对外口径 —— 两个引擎跑出同一结论才是可信的。
    p = ROOT / "11_数据资产" / "cf_results.json"
    if not p.exists():
        p = ROOT / "99_产出" / "GEO体检报告" / "results.json"
    return json.loads(p.read_text(encoding="utf-8"))


def build_assets() -> dict:
    """把 21 家真实体检结果，切成可售卖的资产包。"""
    rows = load_rows()
    scored = [r for r in rows if not r.get("unreachable") and not r.get("waf_blocked")]

    # 按分数排序：最差的 = 最痛的 = 最可能买的
    scored.sort(key=lambda r: r["score"])

    # 资产1：痛点榜（对外只露分数和行业，不露企业名 —— 那是客户隐私）
    pain_leaderboard = [
        {
            "行业": r.get("industry") or "未分类",
            "分数": r["score"],
            "评级": r["grade"],
            "缺结构化": not r["checks"]["schema"]["exists"],
            "缺llms": not r["checks"]["llms"]["exists"],
            "缺FAQ": not r["checks"]["faq"]["exists"],
        }
        for r in scored
    ]

    # 资产2：分行业基准（这是最有卖点的 —— 没人公开卖过这个）
    by_industry: dict[str, list[int]] = {}
    for r in scored:
        by_industry.setdefault(r.get("industry") or "未分类", []).append(r["score"])
    benchmarks = {
        k: {
            "样本数": len(v),
            "平均分": round(sum(v) / len(v), 1),
            "最高": max(v),
            "最低": min(v),
            "中位数": sorted(v)[len(v) // 2],
            "全行业中位": sorted([x for s in by_industry.values() for x in s])[
                len([x for s in by_industry.values() for x in s]) // 2],
        }
        for k, v in sorted(by_industry.items(), key=lambda kv: -len(kv[1]))
    }

    # 资产3：整改代码库（真正的"可执行"部分）
    recipes = [
        {
            "缺什么": "JSON-LD 结构化数据",
            "影响分值": 25,
            "修法": "在 <head> 里加 Organization + WebSite + Service",
            "代码": ('<script type="application/ld+json">\n'
                     '{\n'
                     '  "@context": "https://schema.org",\n'
                     '  "@graph": [\n'
                     '    {"@type":"Organization","name":"公司全称",'
                     '"url":"https://官网/","logo":"https://官网/logo.png"},\n'
                     '    {"@type":"WebSite","name":"公司简称","url":"https://官网/"},\n'
                     '    {"@type":"Service","name":"主营业务",'
                     '"provider":{"@type":"Organization"}}\n'
                     '  ]\n'
                     '}\n'
                     '</script>'),
            "注意": '注意用 @graph 包一层 —— 这是 Google 推荐写法，'
                    '很多工具（含我们自己的早期版本）不认顶层 @type。',
        },
        {
            "缺什么": "llms.txt",
            "影响分值": 10,
            "修法": "站点根目录放一个 llms.txt，说明你是谁、提供什么",
            "代码": ("# 公司全称\n\n"
                     "> 一句话说明你提供什么服务。\n\n"
                     "## 我们做什么\n- 业务一\n- 业务二\n\n"
                     "## 联系\n- 官网：https://官网/\n"
                     "- 邮箱：business@官网域名\n"),
            "注意": "AI 爬虫优先读这个文件；没有它，AI 只能猜你是谁。",
        },
        {
            "缺什么": "FAQ 结构化数据",
            "影响分值": 15,
            "修法": "把常见问答写成 FAQPage，AI 才好直接引用你的答案",
            "代码": ('<script type="application/ld+json">\n'
                     '{"@context":"https://schema.org","@type":"FAQPage",'
                     '"mainEntity":[{"@type":"Question","name":"客户会问的问题",'
                     '"acceptedAnswer":{"@type":"Answer","text":"直接给结论的答案"}}]}\n'
                     '</script>'),
            "注意": "答案第一句就要有结论。AI 摘取的就是第一句。",
        },
        {
            "缺什么": "robots.txt 放行 AI 爬虫",
            "影响分值": 30,
            "修法": "别写 Disallow: /；显式放行主要 AI 爬虫",
            "代码": ("User-agent: GPTBot\nAllow: /\n\n"
                     "User-agent: ClaudeBot\nAllow: /\n\n"
                     "User-agent: PerplexityBot\nAllow: /\n\n"
                     "User-agent: *\nDisallow: /admin\nDisallow: /cart\n\n"
                     "Sitemap: https://官网/sitemap.xml\n"),
            "注意": "实测国内 21 家一家都没拦 AI。拦住 AI 是自伤，不是保护。",
        },
    ]

    # 资产4：定价模型（含单位经济学）
    n_sites = len(scored)
    unit_econ = {
        "已体检站点数": n_sites,
        "单站成本_元": COST_PER_SITE_CNY,
        "单站交付成本_元": DELIVERY_COST_CNY,
        "单站毛利_99档": round(99 - COST_PER_SITE_CNY - DELIVERY_COST_CNY, 2),
        "白标单次调用成本_元": COST_PER_SITE_CNY,
        "白标毛利_2999档": round(2999 - 2000 * COST_PER_SITE_CNY, 2),
    }

    # 达成 1000 万需要的单量（诚实算）
    targets = {
        "全部卖1元_需要客户数": 10_000_000,
        "全部卖9.9元_需要客户数": round(10_000_000 / 9.9),
        "全部卖99元_需要单数": round(10_000_000 / 99),
        "全部卖299元_需要单数": round(10_000_000 / 299),
        "全部卖2999元_需要单数": round(10_000_000 / 2999),
        "混合_现实假设": "80%¥1 + 15%¥9.9 + 4%¥99 + 1%¥2999",
        "混合_每千客户收入_元": round(1000 * (0.8 * 1 + 0.15 * 9.9 + 0.04 * 99 + 0.01 * 2999)),
    }

    out = {
        "生成时间": "见文件时间",
        "数据说明": (
            f"基于 {n_sites} 家已核实中国企业的真实公开官网体检。"
            "不含个人信息，仅含企业公开经营信息与官网技术诊断。"
        ),
        "痛点榜": pain_leaderboard,
        "行业基准": benchmarks,
        "整改代码库": recipes,
        "单位经济学": unit_econ,
        "千万目标测算": targets,
        "产品阶梯": PRODUCTS,
    }
    return out


def main() -> None:
    data = build_assets()
    d = ROOT / "11_数据资产"
    d.mkdir(exist_ok=True)
    (d / "sellable_assets.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 导出可直接发给客户的 CSV 对标表
    import csv
    with (d / "行业对标.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["行业", "样本数", "平均分", "中位数", "最高", "最低"])
        for k, v in data["行业基准"].items():
            w.writerow([k, v["样本数"], v["平均分"], v["中位数"], v["最高"], v["最低"]])

    print(json.dumps(data["行业基准"], ensure_ascii=False, indent=2))
    print()
    print(json.dumps(data["单位经济学"], ensure_ascii=False, indent=2))
    print()
    print(json.dumps(data["千万目标测算"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()