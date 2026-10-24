# -*- coding: utf-8 -*-
"""
财务引擎：唯一作用是让"1000万“变成一个每天可核对的数字。

设计原则：
  · 只有一个目标：180 天 1000 万进账
  · 只看三个数：已进账 / 本月应进账 / 距目标缺口
  · 每天自动算"按当前速度能不能到“，到不了就提前报警，不等 180 天结束才发现
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

import db
from config import COST, FIN_DIR, HORIZON_DAYS, START_DATE, TARGET_CNY


# ------------------------------------------------------------------ 记账
def income(client: str, item: str, amount: float, kind: str = "首付款", note: str = "") -> None:
    with db.conn() as c:
        c.execute("INSERT INTO money_in(ts,client,item,amount,kind,note) VALUES(?,?,?,?,?,?)",
                  (db.now(), client, item, amount, kind, note))
    db.log_run("finance.income", f"{client} {item} {amount}")


def expense(item: str, amount: float, note: str = "") -> None:
    with db.conn() as c:
        c.execute("INSERT INTO money_out(ts,item,amount,note) VALUES(?,?,?,?)", (db.now(), item, amount, note))
    db.log_run("finance.expense", f"{item} {amount}")


# ------------------------------------------------------------------ 交付成本
def delivery_cost(pm_days: int, arch_days: int, writer_days: int, dev_days: int, ops_days: int,
                  tokens_k: int = 0) -> dict:
    """按人天 + Token 算真实成本 → 决定报价下限。这是报价的底线依据。"""
    lines = {
        "项目管理": pm_days * COST["pm_daysalary"],
        "架构设计": arch_days * COST["arch_daysalary"],
        "内容主笔": writer_days * COST["writer_daysalary"],
        "开发": dev_days * COST["dev_daysalary"],
        "运营": ops_days * COST["ops_daysalary"],
        "API/Token": tokens_k * COST["api_cny_per_1k_token"],
    }
    direct = sum(lines.values())
    overhead = direct * 0.18          # 管理/差旅/工具/风险准备
    return {"lines": lines, "direct": round(direct), "overhead": round(overhead),
            "total_cost": round(direct + overhead), "hours": pm_days + arch_days + writer_days + dev_days + ops_days}


def quote_floor(cost: dict, gross_margin: float = 0.55) -> int:
    """报价下限：成本 / (1 - 毛利率)，向上取整到千元。"""
    import math
    return int(math.ceil(cost["total_cost"] / (1 - gross_margin) / 1000) * 1000)


# ------------------------------------------------------------------ 进度
def _day_index() -> int:
    s = date.fromisoformat(START_DATE)
    return (date.today() - s).days


def progress() -> dict:
    got = db.scalar("SELECT IFNULL(SUM(amount),0) FROM money_in WHERE kind!='退款'")
    spent = db.scalar("SELECT IFNULL(SUM(amount),0) FROM money_out")
    passed = max(0, _day_index())
    left = max(1, HORIZON_DAYS - passed)
    elapsed_ratio = min(1.0, passed / HORIZON_DAYS)
    should_have = TARGET_CNY * elapsed_ratio
    # 若按线性节奏，剩下每天需要进账多少
    daily_need = (TARGET_CNY - got) / left
    # 实际日均（近30天）
    since = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")
    recent = db.scalar("SELECT IFNULL(SUM(amount),0) FROM money_in WHERE ts>=? AND kind!='退款'", (since,))
    actual_daily = recent / 30
    return {
        "day_index": passed, "days_left": left, "elapsed_ratio": round(elapsed_ratio, 4),
        "target": TARGET_CNY, "received": round(got), "spent": round(spent), "net": round(got - spent),
        "gap": round(TARGET_CNY - got),
        "should_have_by_now": round(should_have),
        "ahead_or_behind": round(got - should_have),
        "daily_need_remaining": round(daily_need),
        "actual_daily_30d": round(actual_daily),
        "on_pace": actual_daily >= daily_need if daily_need > 0 else True,
        "payout_date": (date.fromisoformat(START_DATE) + timedelta(days=HORIZON_DAYS)).isoformat(),
    }


def monthly_plan() -> list[dict]:
    """把 1000 万拆成 6 个月，标出每月必须拿到的钱与必须签的单数。"""
    from config import INDUSTRIES
    avg = sum(i["avg_ticket"] for i in INDUSTRIES) / len(INDUSTRIES)
    # 复利节奏：第1-2月打地基（低），中段放量，末段冲刺
    weights = [0.06, 0.10, 0.16, 0.20, 0.22, 0.26]
    rows, cum = [], 0
    for m, w in enumerate(weights, 1):
        amt = TARGET_CNY * w
        cum += amt
        rows.append({"month": m, "target_cny": round(amt), "cumulative": round(cum),
                     "deals_needed_at_avg": round(amt / avg, 1),
                     "focus": ["打地基：签 2 个标杆 + 跑通交付 SOP", "复制：签 4-6 个 + 招 1 名交付",
                               "放量：上渠道/合伙人，单月 6-8 单", "规模化：把交付品标准化，人效翻倍",
                               "冲刺：年框客户 + 复购", "收尾：回款 + 续约 + 转介绍裂变"][m - 1]})
    return rows


def write_plan_csv() -> Path:
    rows = monthly_plan()
    p = FIN_DIR / "月度目标拆解.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    return p


def runway_cost(months: int = 6) -> dict:
    """最低生存成本：一个人 + 工具 + 模型。用来算"最坏能撑多久“。"""
    items = {"人（1 名交付，兼销售/运营）": 25000, "大模型 API（国产混合）": 3000,
             "SaaS 工具与数据": 2000, "注册/差旅/杂项": 3000}
    m = sum(items.values())
    return {"monthly": m, "months": months, "total_6m": m * months, "items": items}


if __name__ == "__main__":
    db.init()
    import json
    print(json.dumps(progress(), ensure_ascii=False, indent=2))
    dc = delivery_cost(6, 8, 12, 10, 10, 200)
    print("交付成本:", dc)
    print("报价下限(毛利55%):", quote_floor(dc))
    print("6个月最低生存成本:", runway_cost())
    print(write_plan_csv())
