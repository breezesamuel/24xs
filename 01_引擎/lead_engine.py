# -*- coding: utf-8 -*-
"""
潜客引擎：把"找客户“从运气变成流水线。

三件事：
  1) 名单   —— 按行业 × 城市 × 渠道 生成结构化目标池（可导入真实名单覆盖）
  2) 评分   —— ICP 分：越接近"已经在花钱、且已经痛“的排越前
  3) 话术   —— 每个潜客生成"一句话诊断 + 一个钩子“，避免群发垃圾

原则：单点突破。先打透 1 个城市 1 个行业，把案例做出来，再横向复制。
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

import db
from config import ENGINE, INDUSTRIES, LEAD_DIR

# 目标池模板：用"可搜索的实体特征“描述，便于人工/爬虫补全为真实主体。
# 故意不写死公司名——写死就会变成过期名单；写特征就能天天用。
PROSPECTS = {
    "home_improvement": [
        ("{city}家装工装公司", "本地", "抖音本地生活+美团开店", "老板", "近3个月有团购投放记录"),
        ("{city}全屋定制门店", "本地", "小红书+大众点评", "店长", "点评数<200 且无内容更新"),
        ("{city}装修设计工作室", "本地", "小红书", "设计师", "个人号粉丝<5000但有作品"),
        ("{city}软装/智能家居", "本地", "抖音", "老板", "客单价>15万"),
    ],
    "legal": [
        ("{city}民商事律所", "本地", "知乎+公众号", "主任", "主任有公开内容但更新不规律"),
        ("{city}刑事/婚姻家事所", "本地", "抖音", "主任", "抖音粉丝>1万但无留资入口"),
        ("{city}知识产权代理", "B2B", "官网+搜索引擎", "负责人", "官网最后更新>1年"),
        ("{city}企业法律顾问所", "B2B", "企查查+行业协会", "合伙人", "服务企业数>50"),
    ],
    "cross_border": [
        ("{city}跨境电商卖家", "B2B", "雨果网+亿邦", "运营负责人", "SKU>50 且客单价<200元"),
        ("{city}独立站建站服务商", "B2B", "官网+LinkedIn", "创始人", "服务客户>20家"),
        ("{city}海外仓/物流商", "B2B", "行业展会", "市场部", "有海外仓且有中文站"),
        ("{city}外贸工厂（自有品牌）", "B2B", "LinkedIn+Google", "外贸经理", "有英文官网无结构化数据"),
    ],
    "local_service": [
        ("{city}少儿培训机构", "本地", "抖音本地+美团", "校长", "在售课程>3门"),
        ("{city}健身工作室", "本地", "小红书+大众点评", "店长", "年卡销售为主"),
        ("{city}汽修/保养门店", "本地", "高德+抖音", "老板", "月均进厂>80台"),
        ("{city}宠物店/美容", "本地", "小红书", "店主", "有私域社群>200人"),
    ],
    "manufacturing": [
        ("{city}工业设备/零部件厂", "B2B", "行业门户+展会", "市场总监", "有海外询盘但响应慢"),
        ("{city}智能硬件OEM", "B2B", "LinkedIn", "业务负责人", "SKU>10"),
        ("{city}建材/五金出口商", "B2B", "Google+海关数据", "外贸负责人", "有出口权且有英文站"),
        ("{city}工厂型贸易商", "B2B", "阿里国际站", "运营", "广告ROAS下滑"),
    ],
}

CITIES = ["上海", "北京", "深圳", "杭州", "广州", "成都", "苏州", "武汉", "南京", "西安", "青岛", "厦门"]
FIRST = ["王", "李", "张", "刘", "陈", "杨", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡", "林", "郭"]
GIVEN = ["总", "经理", "工", "老师", "老板", "主任", "总监", "生"]

CHANNELS_EMAIL = ["官网留资邮箱", "企业邮箱推断"]
CHANNELS_SOCIAL = ["视频号", "抖音", "小红书", "知乎", "公众号", "LinkedIn"]


def _people(rng: random.Random) -> str:
    return f"{rng.choice(FIRST)}{rng.choice(GIVEN)}"


def icp_score(ind: dict, signal: str, tier_hint: str) -> tuple[float, str]:
    """
    ICP 分 = 付费能力 + 痛感强度 + 决策可达性 - 替代阻力
    返回 (分数, 分档)
    """
    score = 50.0
    reasons = []
    if ind["avg_ticket"] >= 2e5:
        score += 18; reasons.append("客单价高，ROI 可量化")
    elif ind["avg_ticket"] >= 8e4:
        score += 10; reasons.append("客单价中上，可算清回本周期")
    else:
        score += 2; reasons.append("客单价低，必须走标准化小包")
    if any(k in signal for k in ("下滑", "不规律", "无", "停更", "差评")):
        score += 16; reasons.append("存在明确可观察的痛点信号")
    else:
        score += 6
    if tier_hint in ("老板", "创始人", "主任", "店长", "校长", "店主"):
        score += 14; reasons.append("决策链短，可直接拍板")
    elif tier_hint in ("市场总监", "运营负责人", "业务负责人", "外贸负责人"):
        score += 9; reasons.append("需一级领导点头，但有预算权")
    else:
        score += 4; reasons.append("决策链长，需培育")
    if ind["sales_cycle_days"] <= 21:
        score += 10; reasons.append(f"销售周期短（{ind['sales_cycle_days']}天内），现金流快")
    else:
        score -= 4; reasons.append("销售周期长，需提前铺量")
    if ind.get("risk"):
        score -= 4; reasons.append("需额外处理：" + ind["risk"][:16])
    tier = "A" if score >= 78 else ("B" if score >= 62 else "C")
    return round(score, 1), tier


def build_pool(per_industry: int = 40, seed: int | None = None) -> dict:
    """生成「假设池」。

    重要：PROSPECTS 里的模板是**待检索的画像**，不是真实公司。
    这些行 verified=0，永远进不了 export_list 的触达队列 ——
    它们的价值是告诉人工/爬虫"该去搜什么样的公司"。
    真实公司只能从 import_csv() 进入（verified=1）。
    """
    db.init()
    if seed is not None:
        random.seed(seed)
    rng = random.Random(seed if seed is not None else 7)
    made, rows = 0, []
    for ind in INDUSTRIES:
        cands = []
        for tmpl, tier_hint, channel, role, signal in PROSPECTS[ind["key"]]:
            cands += [(tmpl.format(city=c), tier_hint, channel, role, signal) for c in CITIES]
        rng.shuffle(cands)
        for (comp, tier_hint, channel, role, signal) in cands[:per_industry]:
            score, tier = icp_score(ind, signal, tier_hint)
            scene = ind["ai_scenarios"][rng.randrange(len(ind["ai_scenarios"]))]
            rows.append({
                "ts": db.now(),
                "company": comp,
                "industry": ind["name"],
                "city": comp.split("市")[0][:3] if "市" in comp else comp,
                "channel": channel,
                # 画像没有真实联系人。写角色，不编人名——编出来的姓氏
                # （吴总/徐老师）会被误当成真人，这是触达事故的来源。
                "contact": f"（待查：{role}）",
                "icp_score": score,
                "tier": tier,
                "pain": signal,
                "angle": f"{scene[0]}：{scene[1]}（{ind['proof_metric']}）",
                "status": "hypothesis",
                "verified": 0,
            })
    rows.sort(key=lambda r: -r["icp_score"])
    made = 0
    with db.conn() as c:
        for r in rows:
            # INSERT OR IGNORE：company 上有唯一索引，重复运行不会翻倍
            cur = c.execute("INSERT OR IGNORE INTO leads(ts,company,industry,city,channel,contact,icp_score,tier,pain,angle,status,verified)"
                            " VALUES(:ts,:company,:industry,:city,:channel,:contact,:icp_score,:tier,:pain,:angle,:status,:verified)", r)
            made += cur.rowcount or 0
    db.log_run("lead.build", f"{made} hypothesis rows (verified=0, NOT outreachable)")
    # 返回全部候选的分档统计，new 反映真实新增
    return {"new": made, "of": len(rows),
            "A": sum(1 for r in rows if r["tier"] == "A"),
            "B": sum(1 for r in rows if r["tier"] == "B"),
            "C": sum(1 for r in rows if r["tier"] == "C")}


def import_csv(path: Path) -> int:
    """导入真实名单：只需 5 列 —— 公司/行业/城市/联系人/痛点。

    这是**唯一**能把 verified=1 真实主体的入口。
    """
    n = 0
    with Path(path).open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            comp = (row.get("公司") or row.get("company") or "").strip()
            if not comp:
                continue
            ind_key = next((i["name"] for i in INDUSTRIES if i["name"] in (row.get("行业") or "")), INDUSTRIES[0]["name"])
            ind = next(i for i in INDUSTRIES if i["name"] == ind_key)
            signal = (row.get("痛点") or "").strip()
            role = (row.get("角色") or "").strip() or "老板"
            score, tier = icp_score(ind, signal, role)
            with db.conn() as c:
                cur = c.execute("INSERT OR IGNORE INTO leads(ts,company,industry,city,channel,contact,icp_score,tier,pain,angle,status,verified)"
                                " VALUES(?,?,?,?,?,?,?,?,?,?,'new',1)",
                                (db.now(), comp, ind["name"], (row.get("城市") or "").strip(),
                                 (row.get("渠道") or "").strip(), (row.get("联系人") or "").strip(),
                                 score, tier, signal, row.get("备注", "")))
                n += cur.rowcount or 0
    db.log_run("lead.import", f"{n} verified leads")
    return n


def _is_placeholder(company: str, contact: str) -> bool:
    """挡住模板画像漏进触达队列。

    两道闸：
      1) 公司名里带模板括号（"XX外贸工厂（自有品牌）"）
      2) 联系人还是"（待查：…）"，即没有真人
    """
    if "（" in (company or "") and "）" in (company or ""):
        if any(k in company for k in ("自有品牌", "工厂", "门店", "工作室", "公司", "所")):
            return True
    c = (contact or "").strip()
    return c.startswith("（待查") or c.startswith("(待查")


def export_list(tier: str = "A", limit: int = 200) -> Path:
    """导出触达队列。

    **只导 verified=1 的真实主体。** 模板画像（verified=0）和残留占位
    一律不进队列——这是 60 条里 45 条虚构的根因。
    """
    rows = db.q("SELECT * FROM leads WHERE tier=? AND verified=1 ORDER BY icp_score DESC LIMIT ?", (tier, limit))
    blocked = [r for r in rows if _is_placeholder(r["company"], r["contact"])]
    if blocked:
        raise RuntimeError(
            f"export_list 拒绝导出：{len(blocked)} 行 verified=1 但仍是占位画像"
            f"（例：{blocked[0]['company']} / {blocked[0]['contact']}）。"
            f"先修正 import_csv 导入的真实名单。"
        )
    p = LEAD_DIR / f"名单_{tier}档_{db.today()}.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["公司", "行业", "城市", "联系人(角色)", "主渠道", "ICP分", "档位",
                    "可观察痛点信号", "切入角度", "状态", "首次触达时间", "是否回复", "成交额"])
        for r in rows:
            w.writerow([r["company"], r["industry"], r["city"], r["contact"], r["channel"],
                        r["icp_score"], r["tier"], r["pain"], r["angle"], r["status"],
                        r["first_touch_ts"] or "", r["reply"], r["deal_cny"]])
    return p


def export_hypotheses(tier: str = "A", limit: int = 200) -> Path:
    """导出「假设池」：这些是待检索画像，明确标注不是公司。

    用途是给人/爬虫当检索清单。**绝不可当触达队列。**
    """
    rows = db.q("SELECT * FROM leads WHERE tier=? AND verified=0 ORDER BY icp_score DESC LIMIT ?", (tier, limit))
    p = LEAD_DIR / f"假设池_{tier}档_{db.today()}.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["⚠非真实主体_检索画像", "行业", "城市模式", "待查角色", "建议渠道",
                    "ICP分", "档位", "可观察痛点信号", "切入角度"])
        for r in rows:
            w.writerow([r["company"], r["industry"], r["city"], r["contact"], r["channel"],
                        r["icp_score"], r["tier"], r["pain"], r["angle"]])
    return p


def pipeline() -> dict:
    """当日新假设池 + 导出三档（触达队列只含真实主体）。"""
    s = build_pool(per_industry=ENGINE["lead_daily_target"] * 5, seed=None)
    files = {t: str(export_list(t)) for t in ("A", "B", "C")}
    hyps = {t: str(export_hypotheses(t)) for t in ("A",)}
    return {"generated": s, "files": files, "hypotheses": hyps}


def funnel() -> dict:
    """潜客漏斗现状（真实落库数据）。"""
    def n(sql, a=()):
        return db.scalar(sql, a)
    total = n("SELECT COUNT(*) FROM leads")
    touched = n("SELECT COUNT(*) FROM leads WHERE first_touch_ts IS NOT NULL")
    replied = n("SELECT COUNT(*) FROM leads WHERE reply=1")
    deals = n("SELECT COUNT(*) FROM leads WHERE status='won'")
    won_amt = n("SELECT IFNULL(SUM(deal_cny),0) FROM leads WHERE status='won'")
    return {"leads": total, "touched": touched, "replied": replied, "won": deals, "won_cny": won_amt,
            "touch_rate": round(touched / total, 3) if total else 0,
            "reply_rate": round(replied / touched, 3) if touched else 0,
            "close_rate": round(deals / replied, 3) if replied else 0}


if __name__ == "__main__":
    print(pipeline())
    print(funnel())
