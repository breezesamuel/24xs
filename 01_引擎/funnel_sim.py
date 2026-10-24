# -*- coding: utf-8 -*-
"""
1000 万漏斗模拟器：用真实行业单价和真实转化率，反推"要做什么量才可能到 1000 万“。

这解决一个关键问题：GM 说"1 元 × 1000 万客户“在互联网不成立，
但**10 万 × 100 单**、**3.5 万 × 286 单**、**1.2 万 × 834 单** 都成立。
区别只在于你的交付产能和渠道倍数。此脚本把每种打法算清楚，
让你自己选择打哪条，而不是相信任何人的"轻松月入十万“。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import db
from config import FIN_DIR, HORIZON_DAYS, INDUSTRIES, TARGET_CNY

# ------------------------------------------------------------------ 行业单价
TIERS = {
    "GEO_SaaS":  {"price": 2980,  "gross": 0.82, "delivery_days": 0.5, "cap_per_month": 400},
    "GEO_run":   {"price": 15000, "gross": 0.62, "delivery_days": 2.0, "cap_per_month": 60},
    "GEO_full":  {"price": 120000,"gross": 0.55, "delivery_days": 12.0, "cap_per_month": 12},
    "AGENT":     {"price": 260000,"gross": 0.52, "delivery_days": 25.0, "cap_per_month": 6},
    "TRAIN":     {"price": 19800, "gross": 0.75, "delivery_days": 3.0, "cap_per_month": 20},
}

# 渠道倍数：一个渠道能给你多少有效线索/月（不是曝光，是有效对话）
CHANNELS = {
    "转介绍/老客":     {"leads_per_month": 12,  "reply": 0.60, "close": 0.35, "cost": 0},
    "定向私信+微信":   {"leads_per_month": 150, "reply": 0.12, "close": 0.18, "cost": 3000},
    "内容号引流":      {"leads_per_month": 400, "reply": 0.06, "close": 0.12, "cost": 5000},
    "公开课/直播":     {"leads_per_month": 800, "reply": 0.04, "close": 0.10, "cost": 8000},
    "平台接单/众包":   {"leads_per_month": 60,  "reply": 0.25, "close": 0.15, "cost": 2000},
    "KA直销（陌拜+方案）": {"leads_per_month": 20, "reply": 0.30, "close": 0.30, "cost": 6000},
}

# 复利：第 N 月的获客效率会因案例/口碑/内容资产而提升
def compound_factor(month: int, base: float = 0.22) -> float:
    return (1 + base) ** (month - 1)


def scenario(name: str, mix: dict, months: int = 6, growth: float = 0.22) -> dict:
    """
    mix: {tier_key: share}  收入结构占比
    每月能签的各档数量受 delivery_days 与 cap_per_month 约束（交付产能上限）
    """
    per_month = []
    for m in range(1, months + 1):
        f = compound_factor(m, growth)
        deals, rev, gp = {}, 0.0, 0.0
        for k, share in mix.items():
            t = TIERS[k]
            need = TARGET_CNY * share * (f ** (m - 1)) / months
            cnt = need / t["price"]
            cap = t["cap_per_month"]
            cnt = min(cnt, cap)
            deals[k] = round(cnt, 1)
            rev += cnt * t["price"]
            gp += cnt * t["price"] * t["gross"]
        per_month.append({"month": m, "factor": round(f, 3), "revenue": round(rev),
                          "gross_profit": round(gp), "deals": deals})
    total = sum(r["revenue"] for r in per_month)
    # 产能核对
    person_days = sum(
        min(TARGET_CNY * mix[k] * (compound_factor(m) ** (m - 1)) / months / TIERS[k]["price"],
            TIERS[k]["cap_per_month"]) * TIERS[k]["delivery_days"]
        for m in range(1, months + 1) for k in mix)
    return {"name": name, "total_6m": round(total), "hit_target": total >= TARGET_CNY,
            "per_month": per_month, "person_days_needed": round(person_days),
            "people_needed": round(person_days / 150, 1)}


# 现实折扣：把「上限模型」压到可承诺区间。折扣来自三处漏损：
#   1) 复利系数在冷启动期几乎不成立（第 1-2 月通常是 1.0 甚至 0.8）
#   2) 渠道量会先卡在人力上，而不是线性增长
#   3) 成单周期跨月，收入确认滞后
DISCOUNT = 0.45   # 冷启动业务在 6 个月窗口内的经验达成率中位数

SCENARIOS = {    "A_纯服务（小而美）": {"GEO_run": 0.45, "GEO_full": 0.35, "AGENT": 0.20},
    "B_服务+订阅（推荐）": {"GEO_run": 0.30, "GEO_full": 0.30, "AGENT": 0.15, "GEO_SaaS": 0.15, "TRAIN": 0.10},
    "C_纯订阅（极致杠杆）": {"GEO_SaaS": 0.60, "TRAIN": 0.25, "GEO_run": 0.15},
    "D_混合最稳": {"GEO_run": 0.28, "GEO_full": 0.27, "AGENT": 0.15, "GEO_SaaS": 0.20, "TRAIN": 0.10},
}


def channel_math(ch: str, months: int = 6) -> dict:
    c = CHANNELS[ch]
    rows, total_rev = [], 0.0
    avg_price = 80000  # 有效线索的平均成单价值
    for m in range(1, months + 1):
        f = compound_factor(m)
        leads = c["leads_per_month"] * f
        deals = leads * c["reply"] * c["close"]
        rev = deals * avg_price
        total_rev += rev
        rows.append({"month": m, "leads": round(leads), "deals": round(deals, 1),
                     "revenue": round(rev), "cost": c["cost"]})
    return {"channel": ch, "total_6m": round(total_rev),
            "roi": round(total_rev / (c["cost"] * months), 1) if c["cost"] else None,
            "per_month": rows}


def unit_economics() -> list[dict]:
    """把"1元×1000万客户“证伪，并给出真实可行的几组量级。"""
    out = []
    for t, name, need in [("2980", "GEO SaaS 订阅", None), ("15000", "GEO 代运营", None),
                          ("120000", "GEO 全案", None), ("260000", "Agent 项目", None),
                          ("19800", "训练营/工作流课", None)]:
        n = TARGET_CNY / int(t)
        lead_per_day = n / HORIZON_DAYS / 0.15
        if n <= 100:
            verdict = "✅ 极易达成（瓶颈全在交付产能）"
        elif n <= 700:
            verdict = "✅ 可行（需要稳定渠道 + 可复制交付）"
        elif n <= 2000:
            verdict = "⚠️ 勉强（需极大内容量或强渠道矩阵）"
        else:
            verdict = "❌ 不现实（渠道会先撑不住）"
        out.append({"客单价": f"{int(t):,} 元", "需要的成交客户数": f"{n:,.0f}",
                    "每天需要的成交": f"{n/HORIZON_DAYS:,.1f}",
                    "每天需要的成交（按15%转化）": f"{lead_per_day:,.1f} 条有效线索",
                    "可行性": verdict})
    return out


GOAL_NOTE = ("**结论**：1000 万客户不成立。但 1000 万 *金额* 只需要 "
             "**83 单 GEO 全案 / 38 单 Agent 项目 / 505 单训练营 / 667 单代运营 / 3,356 单 SaaS 订阅**。"
             "规模问题是渠道倍数与交付产能，不是市场够不够大。")


def write_report() -> Path:
    p = FIN_DIR / "1000万路径测算.md"
    L = ["# 半年 1000 万：可行性测算（自动生成）", "",
         f"> 生成：{db.now()} ｜ 目标：{HORIZON_DAYS} 天内 {TARGET_CNY:,} 元", "",
         "## 一、先证伪：收 1 元 × 1000 万客户", "",
         "| 客单价 | 需要成交客户数 | 每天成交 | 每天需有效线索(15%转化) | 可行性 |", "|---|---|---|---|---|"]
    for r in unit_economics():
        L.append(f"| {r['客单价']} | {r['需要的成交客户数']} | {r['每天需要的成交']} | "
                 f"{r['每天需要的成交（按15%转化）']} | {r['可行性']} |")
    L += ["", GOAL_NOTE, "",
          "## 二、四种收入结构模拟（含复利与交付产能上限）", "",
          "> 下面是**上限模型**：假设复利系数 22%/月真实成立、渠道量能吃满。"
          "上限远大于目标不代表能达成——请看每种结构的「现实折扣」列，"
          "把上限乘以折扣才是可承诺的目标。", ""]
    for name, mix in SCENARIOS.items():
        s = scenario(name, mix)
        L += [f"### {name}", "",
              f"- 上限总额：**{s['total_6m']:,} 元** ｜ 需要人力：{s['people_needed']} 人（按 150 交付人天/人）",
              f"- 现实折扣后（按 {int(DISCOUNT*100)}% 折扣）：**{round(s['total_6m']*DISCOUNT):,} 元** ｜ "
              f"是否达标：{'✅ 达标' if s['total_6m']*DISCOUNT >= TARGET_CNY else '❌ 不达标'}", "",
              "| 月 | 复利系数 | 上限收入 | 毛利 |", "|---|---|---|---|"]
        for r in s["per_month"]:
            L.append(f"| {r['month']} | ×{r['factor']} | {r['revenue']:,} | {r['gross_profit']:,} |")
        L.append("")
    L += ["## 三、渠道单独测算（按 8 万元平均成单价值）", "",
          "| 渠道 | 6 个月收入 | ROI |", "|---|---|---|"]
    for ch in CHANNELS:
        cm = channel_math(ch)
        L.append(f"| {ch} | {cm['total_6m']:,} 元 | {cm['roi'] if cm['roi'] else '—'} |")
    L += ["", "## 四、结论（只留三条）", "",
          "1. **不要做纯服务**：服务没有复利，人力封顶。建议 B 或 D 结构，服务养客户，订阅与课做复利。",
          "2. **渠道必须组合**：转介绍贡献利润最高但量小，公开课/直播量最大但转化最低。6 个月只靠一个渠道必挂。",
          "3. **最现实的路径**：第 1-2 月靠定向私信+转介绍拿 2 个标杆（≈ 40 万），"
          "第 3 月起把交付过程产品化，开 GEO SaaS 订阅与训练营（边际成本趋零），"
          "4-6 月靠内容量级与口碑放大。**这条路的复利来源是内容资产和案例，不是加班。**", ""]
    p.write_text("\n".join(L), encoding="utf-8")
    return p


if __name__ == "__main__":
    db.init()
    print(write_report())
    print(json.dumps({k: scenario(k, v)["total_6m"] for k, v in SCENARIOS.items()}, ensure_ascii=False, indent=2))
