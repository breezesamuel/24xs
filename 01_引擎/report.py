# -*- coding: utf-8 -*-
"""
日报引擎：把库里所有真实数据汇成一张 3 分钟能看完的看板。
一个不看的报表就是废纸，所以这里只保留能触发动作的数字。
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import db
import finance
import funnel_sim
import geo_audit
import lead_engine
from config import OUT_DIR, REPORT_DIR, TARGET_CNY

# ------------------------------------------------------------------ 今日动作引擎
PHASES = [
    (0, 14, "打地基", "别急着卖。先跑通 1 套可复用交付包 + 1 份能验证的诊断报告。"),
    (15, 44, "打样", "把标杆客户做出来。案例比说服力强。"),
    (45, 89, "复制", "SOP 冻结，开始加人加渠道，同一交付卖第二次。"),
    (90, 134, "放量", "渠道倍数是关键变量。此阶段只优化获客成本。"),
    (135, 179, "收钱", "回款、续约、年框、转介绍。现金优先于营收。"),
]


def phase_of(day: int) -> tuple[str, str]:
    for a, b, name, note in PHASES:
        if a <= day <= b:
            return name, note
    return PHASES[-1][2], PHASES[-1][3]


def _today_tasks(day: int) -> list[dict]:
    ph, _ = phase_of(day)
    base = [
        {"phase": ph, "title": "扫 GEO 探测表 30 题，回填提及结果", "owner": "运营", "cny_target": 0},
        {"phase": ph, "title": "触达 A 档名单 60 条（私信+邮件各半）", "owner": "销售", "cny_target": 0},
        {"phase": ph, "title": "发布 2 条内容（1 短内容卡 + 1 GEO 语料）", "owner": "内容", "cny_target": 0},
        {"phase": ph, "title": "推进在谈客户：每个至少推进一个决策要素", "owner": "销售", "cny_target": 0},
    ]
    if day < 15:
        base[0]["title"] = "冻结 1 个行业的交付 SOP 与报价，跑通 1 次全流程"
        base[3]["title"] = "签下 1 个愿意付全款的标杆（哪怕 1.5 万）"
    elif day < 45:
        base[3]["title"] = "把标杆案例写成可对外的 1 页纸 + 30 秒视频"
    elif day < 90:
        base[2]["title"] = "上线 GEO SaaS 订阅的付费通道（先收 2980 的年费）"
    elif day < 135:
        base[1]["title"] = "新增 1 个获客渠道（平台/直播/众包），做到 400 有效线索/月"
    else:
        base[1]["title"] = "全部精力转向回款与续约，不再接受长账期"
    return base


def snapshot() -> dict:
    db.init()
    f = lead_engine.funnel()
    p = finance.progress()
    corpus = db.scalar("SELECT COUNT(*) FROM corpus")
    words = db.scalar("SELECT IFNULL(SUM(word_count),0) FROM corpus")
    probes = db.scalar("SELECT COUNT(*) FROM geo_probes")
    day = p["day_index"]
    ph, ph_note = phase_of(day)
    return {
        "date": date.today().isoformat(), "day_index": day, "phase": ph, "phase_note": ph_note,
        "money": p, "funnel": f, "assets": {"corpus_files": corpus, "corpus_chars": words, "geo_probes": probes},
        "tasks": _today_tasks(day),
    }


def render(s: dict | None = None) -> Path:
    s = s or snapshot()
    m, f, a = s["money"], s["funnel"], s["assets"]
    bar_w = 40
    ratio = min(1.0, m["received"] / m["target"]) if m["target"] else 0
    filled = int(bar_w * ratio)
    bar = "█" * filled + "░" * (bar_w - filled)
    L = [
        f"# 每日看板 · {s['date']}（第 {s['day_index']}/{finance.HORIZON_DAYS} 天 · {s['phase']}期）", "",
        f"## 钱（唯一目标：{finance.HORIZON_DAYS} 天 {TARGET_CNY:,} 元）", "",
        f"```\n{bar}  {ratio:.1%}\n```", "",
        f"| 指标 | 值 |", "|---|---|",
        f"| 已进账 | {m['received']:,} 元 |",
        f"| 已支出 | {m['spent']:,} 元 |",
        f"| 净额 | {m['net']:,} 元 |",
        f"| 距目标缺口 | {m['gap']:,} 元 |",
        f"| 按天进度本应达成 | {m['should_have_by_now']:,} 元 |",
        f"| 领先/落后 | {m['ahead_or_behind']:+,} 元 |",
        f"| 剩余 {m['days_left']} 天，日均需进账 | **{m['daily_need_remaining']:,} 元/天** |",
        f"| 近 30 天实际日均 | {m['actual_daily_30d']:,} 元/天 |",
        f"| 是否在轨 | {'✅ 在轨' if m['on_pace'] else '❌ 落后，必须调整渠道或提价'} |",
        f"| 目标日 | {m['payout_date']} |", "",
        "## 漏斗（潜客 → 回款）", "",
        "| 环节 | 数量 | 转化 |", "|---|---|---|",
        f"| 潜客池 | {f['leads']:,} | — |",
        f"| 已触达 | {f['touched']:,} | {f['touch_rate']:.1%} |",
        f"| 有回复 | {f['replied']:,} | {f['reply_rate']:.1%}（分母=已触达） |",
        f"| 已成交 | {f['won']:,} | {f['close_rate']:.1%}（分母=有回复） |",
        f"| 成交金额 | {f['won_cny']:,} 元 | — |", "",
        "**健康线参考**：触达→回复 ≥8%，回复→成交 ≥15%。低于此线说明问题在话术或人群，不在渠道量。", "",
        "## 资产（复利存量，只增不减）", "",
        f"- 内容语料文件：{a['corpus_files']} 个 / {a['corpus_chars']:,} 字符",
        f"- GEO 探测样本：{a['geo_probes']:,} 条（这些是下个月复利的数据基础）", "",
        "## 今日动作（做完这 4 件就够了）", "",
        "| # | 动作 | 负责 |", "|---|---|---|"]
    for i, t in enumerate(s["tasks"], 1):
        L.append(f"| {i} | {t['title']} | {t['owner']} |")
    L += ["", f"> 阶段提醒：**{s['phase']}** — {s['phase_note']}", ""]
    p = REPORT_DIR / f"每日看板_{s['date']}.md"
    p.write_text("\n".join(L), encoding="utf-8")
    (REPORT_DIR / "最新看板.md").write_text("\n".join(L), encoding="utf-8")
    return p


if __name__ == "__main__":
    print(render())
