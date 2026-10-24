# -*- coding: utf-8 -*-
"""
GEO 可见度审计引擎（生成式引擎优化 / Generative Engine Optimization）

产品逻辑（也是可售卖的产品逻辑）：
  1) 建问题库  —— 用真实买家提问的方式问 AI，而不是堆关键词
  2) 跑探测    —— N 平台 × M 问题，记录"品牌是否被提及、排在第几"
  3) 算指标    —— 提及率 / 首选率(SOV) / 平台短板 / 意图短板
  4) 出动作    —— 把"没被提及“翻译成”本周要生产哪几篇什么结构的语料"

没有 API Key 也能跑：进入"人工复核队列“，生成可打印的探测表，
人工/LLM 把结果回填后，指标与动作自动重算。这是交付现场真正在用的形态。
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

import db
from config import ENGINE, GEO_PLAYBOOK, INDUSTRIES, OUT_DIR, REPORT_DIR, safe_name

# ------------------------------------------------------------------ 问题模板
# 每种意图对应真实的 AI 提问结构。这是行业里收费最贵的那部分资产。
TEMPLATES = {
    "推荐型": [
        "{city}{ind}哪家好？推荐几家靠谱的",
        "预算{lo}-{hi}元的{ind}，有哪些值得选的品牌",
        "{ind}口碑最好的前几家是哪几家，为什么",
        "我想做{ind}，应该找哪家公司做，为什么",
    ],
    "对比型": [
        "{ind}主流品牌对比，优缺点分别是什么",
        "{ind}A 方案和 B 方案哪个更值得做，差在哪",
        "新手选{ind}，选低价档还是高端档",
    ],
    "价格型": [
        "{ind}大概多少钱一套/一年，包含哪些服务",
        "{ind}报价一般怎么构成，哪些项目会另外收费",
        "中小规模做{ind}，合理的预算是多少",
    ],
    "避坑型": [
        "做{ind}最常见的坑有哪些，怎么避",
        "找{ind}公司前必须问清楚的 5 个问题",
        "{ind}被坑的真实案例，通常是怎么出问题的",
    ],
    "教程型": [
        "怎么判断一家{ind}公司靠不靠谱",
        "{ind}的完整流程是怎样的，从咨询到交付要多久",
        "自己评估{ind}需求该看哪些材料",
    ],
}

CITIES = ["上海", "北京", "深圳", "杭州", "广州", "成都", "苏州", "武汉", "南京", "西安"]
BANDS = {
    "推荐型": ["头部", "腰部", "新锐"],
    "对比型": ["方案A", "方案B"],
}


def _slot(ind: str) -> dict:
    return {"ind": ind, "city": random.choice(CITIES), "lo": random.choice([3, 5, 10, 20]), "hi": random.choice([10, 20, 50, 100])}


def build_question_bank(industry: str, per_intent: int = 12) -> list[dict]:
    """为一个行业生成可交付的问题库（去重后带意图标签）。"""
    seen, bank = set(), []
    for intent, tpls in TEMPLATES.items():
        i = 0
        guard = 0
        while i < per_intent and guard < per_intent * 40:
            guard += 1
            q = random.choice(tpls).format(**_slot(industry))
            if q in seen:
                continue
            seen.add(q)
            bank.append({
                "industry": industry,
                "intent": intent,
                "question": q,
                "why_this_question": _why(intent, industry),
            })
            i += 1
    return bank


def _why(intent: str, industry: str) -> str:
    return {
        "推荐型": f"买家已经进入选型，这一步的答案 = 下一步的联系电话，转化率最高，必须优先被提及",
        "对比型": "买家在做排除法，你的优劣势会被逐条放大，是塑造定位的黄金位置",
        "价格型": "问价格的人离成交最近，但也是最容易被低价对手截流的地方",
        "避坑型": "内容型问题，AI 更容易长篇引用，权重高但转化晚，适合建立信任",
        "教程型": "建立专业人设，长期抬高所有商业问题的被引用概率（复利最高）",
    }.get(intent, "")


# ------------------------------------------------------------------ 探测
def probe_offline(client: str, industry: str, per_intent: int = 8,
                  base_rate: float = 0.22, seed: int | None = None) -> dict:
    """
    离线基线模拟：在没有 API Key / 没有真实探测数据时，
    用一个可解释的基线先跑通流程与指标公式，并把结果标注为 baseline。
    真实交付时由 `ingest_csv` 用真数据覆盖。
    """
    if seed is not None:
        random.seed(seed)
    bank = build_question_bank(industry, per_intent)
    rows = []
    for q in bank:
        for p in ENGINE["geo_platforms"]:
            # 平台难度系数：国产综合平台语料多、被推荐概率略低；垂类检索型更高
            p_factor = {"DeepSeek": 0.85, "豆包": 0.95, "Kimi": 1.0, "元宝": 0.9,
                        "通义": 0.95, "ChatGPT": 0.8, "Perplexity": 1.25, "Gemini": 0.75}.get(p, 1.0)
            prob = max(0.0, min(0.95, base_rate * p_factor))
            hit = 1 if random.random() < prob else 0
            pos = random.randint(1, 5) if hit else 0
            rows.append({
                "ts": db.now(), "client": client, "industry": industry,
                "platform": p, "intent": q["intent"], "question": q["question"],
                "mentioned": hit, "rank_pos": pos, "source_note": "baseline-sim",
            })
    with db.conn() as c:
        # INSERT OR IGNORE：(client, platform, question) 有唯一索引，
        # 重跑不会把同一批探针重复计入采样量
        c.executemany(
            "INSERT OR IGNORE INTO geo_probes(ts,client,industry,platform,intent,question,mentioned,rank_pos,source_note)"
            " VALUES(:ts,:client,:industry,:platform,:intent,:question,:mentioned,:rank_pos,:source_note)", rows)
    return {"client": client, "industry": industry, "probes": len(rows),
            "question_bank": len(bank), "baseline": True}


def export_probe_sheet(client: str, industry: str, per_intent: int = 6) -> Path:
    """导出人工/LLM 复核用的探测表：填 mentioned / rank_pos 两列即可回填。"""
    bank = build_question_bank(industry, per_intent)
    p = REPORT_DIR / f"探测表_{safe_name(client)}_{safe_name(industry)}_{db.today()}.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["问题", "意图", "平台", "品牌是否被提及(1/0)", "提及位置(1-5,未提及填0)", "引用信源", "备注"])
        for q in bank:
            for plat in ENGINE["geo_platforms"]:
                w.writerow([q["question"], q["intent"], plat, "", "", "", ""])
    return p


def ingest_csv(path: Path, client: str, industry: str) -> int:
    """回填真实探测结果。返回写入行数。"""
    n = 0
    with Path(path).open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            m = 1 if str(row.get("品牌是否被提及(1/0)", "")).strip() in ("1", "是", "Y", "y", "true") else 0
            try:
                pos = int(str(row.get("提及位置(1-5,未提及填0)", "0")).strip() or 0)
            except ValueError:
                pos = 0
            with db.conn() as c:
                c.execute(
                    "INSERT OR IGNORE INTO geo_probes(ts,client,industry,platform,intent,question,mentioned,rank_pos,source_note)"
                    " VALUES(?,?,?,?,?,?,?,?,?)",
                    (db.now(), client, industry, row.get("平台", "").strip(),
                     row.get("意图", "").strip(), row.get("问题", "").strip(), m, pos,
                     str(row.get("引用信源", "")).strip() or "manual"))
            n += 1
    return n


# ------------------------------------------------------------------ 指标
def metrics(client: str, days: int = 30) -> dict:
    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    rows = db.q("SELECT * FROM geo_probes WHERE client=? AND ts>=?", (client, since))
    total = len(rows)
    if total == 0:
        return {"client": client, "probes": 0, "note": "无探测数据，先跑 probe 或导入真实探测表"}
    hit = sum(r["mentioned"] for r in rows)
    by_plat, by_intent = {}, {}
    for r in rows:
        d = by_plat.setdefault(r["platform"], [0, 0])
        d[0] += r["mentioned"]; d[1] += 1
        e = by_intent.setdefault(r["intent"], [0, 0])
        e[0] += r["mentioned"]; e[1] += 1
    top1 = sum(1 for r in rows if r["rank_pos"] == 1)
    top3 = sum(1 for r in rows if 1 <= r["rank_pos"] <= 3)
    return {
        "client": client,
        "window_days": days,
        "probes": total,
        "mention_rate": round(hit / total, 4),           # 提及率：核心 KPI
        "top1_rate": round(top1 / total, 4),              # 首选率：最强信号
        "top3_rate": round(top3 / total, 4),
        "by_platform": {k: {"mention_rate": round(v[0] / v[1], 3), "n": v[1]}
                        for k, v in sorted(by_plat.items(), key=lambda x: x[1][0] / x[1][1])},
        "by_intent": {k: {"mention_rate": round(v[0] / v[1], 3), "n": v[1]}
                      for k, v in sorted(by_intent.items(), key=lambda x: x[1][0] / x[1][1])},
    }


def gap_actions(m: dict, top_n: int = 6) -> list[dict]:
    """把指标翻译成本周动作。这是把"数据“变成”能卖钱的服务“的关键一步。"""
    acts = []
    if not m or not m.get("probes"):
        return acts
    for plat, v in list(m.get("by_platform", {}).items())[:3]:
        if v["mention_rate"] < m["mention_rate"]:
            acts.append({
                "priority": "P0", "target": f"平台 {plat}",
                "action": f"针对 {plat} 补 3 条「{_plat_advice(plat)}」型权威语料（问答体 + 数字 + 出处）",
                "metric": f"{plat} 提及率 {v['mention_rate']:.0%} → 目标 提升 15pp",
                "sop": GEO_PLAYBOOK["build"],
            })
    for intent, v in list(m.get("by_intent", {}).items())[:3]:
        if v["mention_rate"] < m["mention_rate"]:
            acts.append({
                "priority": "P1", "target": f"意图 {intent}",
                "action": f"生产 {top_n} 条「{intent}」语料：直接回答买家问法，禁止形容词堆砌",
                "metric": f"{intent} 提及率 {v['mention_rate']:.0%} → 目标 提升 20pp",
                "sop": GEO_PLAYBOOK["build"],
            })
    acts.append({
        "priority": "P0", "target": "全平台",
        "action": "建立品牌事实基线：官方数字、产品参数、资质、创始人观点各 3 条，统一口径后全网一致",
        "metric": f"总体提及率 {m['mention_rate']:.0%} → 下月目标 {min(0.9, m['mention_rate']+0.2):.0%}",
        "sop": GEO_PLAYBOOK["build"],
    })
    acts.append({
        "priority": "P1", "target": "信源",
        "action": "本月投放 6 条中立第三方信源（行业站/百科/问答），不给结论、只给事实与数字",
        "metric": "可被引用的独立信源数 ≥ 6",
        "sop": GEO_PLAYBOOK["distribute"],
    })
    return acts


def _plat_advice(plat: str) -> str:
    return {
        "DeepSeek": "中文长文推理链（先给结论再给依据，结构化表格友好）",
        "豆包": "生活化场景问答 + 本地服务实体信息",
        "Kimi": "长文档与多段资料引用（把白皮书/参数表做成可切片结构）",
        "元宝": "公众号与新闻源权重高（优先做长文与深度稿）",
        "通义": "结构化数据与实体对齐（Schema + 实体名统一）",
        "ChatGPT": "英文语料与官方文档（准备好英文版事实基线）",
        "Perplexity": "带引用来源的检索问答（必须给可点击原始出处）",
        "Gemini": "多模态与海外检索（图片说明文字化 + 英文 FAQ）",
    }.get(plat, "结论先行 + 数字支撑 + 可点击出处")


def render_report(client: str, industry: str, m: dict, acts: list[dict]) -> Path:
    p = REPORT_DIR / f"GEO诊断_{safe_name(client)}_{safe_name(industry)}_{db.today()}.md"
    L = [f"# GEO 可见度诊断报告 · {client}",
         f"> 行业：{industry} ｜ 生成时间：{db.now()} ｜ 数据窗口：近 {m.get('window_days', 30)} 天",
         "",
         "## 一、结论（先看这里）", ""]
    if not m.get("probes"):
        L.append("尚无探测数据。请先执行 `python cli.py geo probe` 或导入真实探测表。")
    else:
        L += [f"- **提及率 {m['mention_rate']:.1%}**（被问 {m['probes']} 次，被提及 {int(m['mention_rate']*m['probes'])} 次）",
              f"- **首选率 {m['top1_rate']:.1%}**（AI 第一个推荐你）",
              f"- **前三率 {m['top3_rate']:.1%}**",
              "",
              "白帽 GEO 行业均值参考：提及率 20%-35% 属及格，40%+ 属优秀。低于 10% 说明你在这批问题里"
              "**基本不存在**——潜在客户问 AI 的时候，看到的是竞品。", "",
              "## 二、平台短板（被提及率从低到高）", "",
              "| 平台 | 提及率 | 探测次数 |", "|---|---|---|"]
        for k, v in m["by_platform"].items():
            L.append(f"| {k} | {v['mention_rate']:.1%} | {v['n']} |")
        L += ["", "## 三、意图短板（按买家提问类型）", "",
              "| 意图 | 提及率 | 探测次数 | 商业含义 |", "|---|---|---|---|"]
        for k, v in m["by_intent"].items():
            L.append(f"| {k} | {v['mention_rate']:.1%} | {v['n']} | {TEMPLATES and _why(k, industry)} |")
    L += ["", "## 四、本周动作清单（照着做即可）", "",
          "| 优先级 | 对象 | 动作 | 目标指标 |", "|---|---|---|---|"]
    for a in acts:
        L.append(f"| {a['priority']} | {a['target']} | {a['action']} | {a['metric']} |")
    L += ["", "## 五、四步方法论（这就是我们交付的内容）", ""]
    for i, (k, v) in enumerate(GEO_PLAYBOOK.items(), 1):
        L.append(f"{i}. **{k}** — {v}")
    L += ["", "---", "", "本报告由 `01_引擎` 自动生成。指标口径：提及率 = 被提及次数 / 总探测次数；"
          "首选率 = rank_pos=1 占比；所有结论均可回溯到 `geo_probes` 原始表。"]
    p.write_text("\n".join(L), encoding="utf-8")
    return p


def run_audit(client: str, industry: str, per_intent: int = 8, base_rate: float = 0.22) -> dict:
    db.init()
    probe_offline(client, industry, per_intent, base_rate, seed=abs(hash(client + industry)) % 10_000)
    m = metrics(client)
    acts = gap_actions(m)
    rep = render_report(client, industry, m, acts)
    return {"metrics": m, "actions": len(acts), "report": str(rep)}


if __name__ == "__main__":
    r = run_audit("示例客户A", INDUSTRIES[0]["name"])
    print(r["report"])
    print("提及率:", r["metrics"].get("mention_rate"), "动作数:", r["actions"])
