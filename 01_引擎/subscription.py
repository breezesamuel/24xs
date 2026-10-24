# -*- coding: utf-8 -*-
"""订阅规则引擎 —— 定价、额度、推荐奖励的唯一数据源。

为什么单独一个模块
------------------
定价和推荐规则如果散在 HTML 和各脚本里，改一处漏一处，最后就会出现
"页面写 60 元、后台按 150 元扣、推荐奖励发 3 个月"这种对外口径不一致。
这里定一份，页面从它渲染、后台从它结算、验收也从它核对。

产品边界（重要）
----------------
订阅是**纯自动化快检，零人工交付**：脚本抓公开首页、检测结构化数据
信号、生成报告。单次边际成本只有几次 HTTP 请求。

所以 finance.quote_floor() 那个 ¥192,000 的报价硬下限**不适用于订阅** ——
那是给 40 人天的咨询交付算的。两件事必须分开，否则要么把咨询卖便宜了，
要么把订阅定到用户付不起。

收款通道
--------
支付宝转账 + 人工确认开通。不接支付 API，因此不需要商户资质、
不做程序化扣款，也就没有"扣款成功但未开通"的对账问题。
代价是开通要人工，量大了会顶不住 —— 到那时再上支付宝开放平台。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------- 主体信息
# 订阅走个人账户（小额），咨询项目走公司对公并开发票。
# 两个通道分开，不要用个人账户收咨询款 —— 那个金额开不出公司发票。
ENTITY_COMPANY = "上海丙大山智能科技有限公司"
ENTITY_PERSON = "廖献云"

PAY_ALIPAY = "supi24@163.com"

# 工行对公/个人账户信息（咨询项目用，订阅页不展示）
BANK = {
    "开户行": "中国工商银行",
    "账号": "6222031001026162672",
    "开户姓名": ENTITY_PERSON,
    "网点号": "2993",
    "银行机构代码": "102290029937",
    "网点名称": "徐汇长桥支行",
    "网点地址": "上海市罗香路37号",
}

# ------------------------------------------------------------ 定价（中/英）
# period: month / quarter / year；months: 折算月数，用于额度核算
PLANS = {
    "cn": {
        "currency": "CNY",
        "symbol": "¥",
        "plans": {
            "month": {"label": "月付", "price": 60, "months": 1, "uses": 60},
            "quarter": {"label": "季付", "price": 150, "months": 3, "uses": 120},
            "year": {"label": "年付", "price": 500, "months": 12, "uses": 400},
        },
    },
    "en": {
        "currency": "USD",
        "symbol": "$",
        "plans": {
            "month": {"label": "Monthly", "price": 9.9, "months": 1, "uses": 60},
            "quarter": {"label": "Quarterly", "price": 25, "months": 3, "uses": 120},
            "year": {"label": "Yearly", "price": 99, "months": 12, "uses": 400},
        },
    },
}

# ------------------------------------------------------- 单次付费（不是订阅）
# 官网"免费测 AI 可见度"的付费解锁档：一次性整改报告。
# 它不是订阅，不给额度，只给报告，所以不放在 PLANS 里（那边按月计额度）。
# 但价格仍必须在这里维护，alipay_pay 从这里读，改价只改一处。
ONE_OFF = {
    "report": {
        "label": "完整整改报告",
        "price_cny": 99,
        "subject": "AI 可见度体检 · 完整整改报告",
    },
}

# --------------------------------------------------------------- 免费额度
# 每个账号 10 次免费使用，注册即给，用完必须付费。
FREE_USES = 10

# 一个账号同时订阅多个套餐时，取额度最大的那个，不叠加。
# 叠加会让"季付年付"的定价失去意义 —— 大家都买最便宜的单月再自己叠加。

# ------------------------------------------------------------- 推荐奖励
# 规则（按你确认的口径，中英文一致）：
#   邀 1 人 且 该人实付 ≥ 1 个月  ->  奖励 1 个月额度
#   邀 3 人 且 3 人全部实付 ≥ 1 个季度  ->  奖励 3 个月额度
#   邀 10 人 且 10 人全部实付年费  ->  奖励 1 年额度
#
# 关键设计：奖励按**被邀请人实际付费的档位**判定，不按邀请人的档位。
# 否则只要拉够人头、让被邀请人都买最便宜的月付，就能拿到年费奖励。
REFERRAL_TIERS = [
    {"invites": 1, "min_paid_months": 1, "reward_months": 1,
     "title_zh": "邀请 1 位并成功支付 1 个月以上",
     "title_en": "Refer 1 friend who pays for 1 month+",
     "reward_zh": "奖励 1 个月使用额度", "reward_en": "1 month free credit"},
    {"invites": 3, "min_paid_months": 3, "reward_months": 3,
     "title_zh": "邀请 3 位且均成功支付季度套餐",
     "title_en": "Refer 3 friends who each pay for a quarter",
     "reward_zh": "奖励 3 个月使用额度", "reward_en": "3 months free credit"},
    {"invites": 10, "min_paid_months": 12, "reward_months": 12,
     "title_zh": "邀请 10 位且均成功支付年费套餐",
     "title_en": "Refer 10 friends who each pay for a year",
     "reward_zh": "奖励 1 年使用额度", "reward_en": "1 year free credit"},
]

# 每个被邀请人只能为其邀请人贡献一次奖励（同一人不可重复刷奖励）


def plan_price(lang: str, period: str) -> float:
    return PLANS[lang]["plans"][period]["price"]


def plan_symbol(lang: str) -> str:
    return PLANS[lang]["symbol"]


def plan_uses(period: str) -> int:
    return PLANS["cn"]["plans"][period]["uses"]


def uses_for_months(months: int, uses_per_month: int = 20) -> int:
    """折算额度。默认每月 20 次，纯自动化跑批远不到这个数。"""
    return months * uses_per_month


def referral_progress(payments: list[dict]) -> dict:
    """根据被邀请人的付费记录，算当前推荐进度与已达成的档位。

    payments: [{"paid_months": int, "currency": "CNY", "amount": float}, ...]
    只统计已确认到账（confirmed=True 由调用方过滤）的记录。
    """
    got = []
    for t in REFERRAL_TIERS:
        # 达标人数 = 付费月数 >= 该档门槛的人数，且总邀请数达标
        enough = sum(1 for p in payments if p["paid_months"] >= t["min_paid_months"])
        if len(payments) >= t["invites"] and enough >= t["invites"]:
            got.append(t)
    next_tier = next((t for t in REFERRAL_TIERS
                      if not any(g is t for g in got)), None)
    return {"achieved": got, "next": next_tier,
            "referred": len(payments)}


def public_pricing() -> dict:
    """给页面用的公开定价/规则，不含任何账户或密钥信息。"""
    return {
        "free_uses": FREE_USES,
        "plans": {lg: {"currency": PLANS[lg]["currency"],
                       "symbol": PLANS[lg]["symbol"],
                       "items": [
                           {"period": k, "label": v["label"],
                            "price": v["price"], "uses": v["uses"],
                            "months": v["months"]}
                           for k, v in PLANS[lg]["plans"].items()]}
                   for lg in PLANS},
        "referrals": REFERRAL_TIERS,
        "pay_alipay": PAY_ALIPAY,
    }


def render_pricing_table_md() -> str:
    """Markdown 定价表，给 README / 站内说明用，保持与代码一致。"""
    lines = ["| 套餐 | 中文价 | 英文价 | 额度 |", "|---|---|---|---|"]
    for period in ("month", "quarter", "year"):
        cn = PLANS["cn"]["plans"][period]
        en = PLANS["en"]["plans"][period]
        lines.append(f"| {cn['label']} | ¥{cn['price']} | ${en['price']} "
                     f"| {cn['uses']} 次 |")
    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 70)
    print("  订阅定价（纯自动化快检，零人工交付）")
    print("=" * 70)
    print(f"  注册赠送免费使用 {FREE_USES} 次")
    print()
    print(render_pricing_table_md())
    print()
    print("  推荐奖励：")
    for t in REFERRAL_TIERS:
        print(f"    - {t['title_zh']} -> {t['reward_zh']}")
    print()
    print("  收款：支付宝转账 + 人工确认开通（无自动扣款）")
    print(f"  收款账号：{PAY_ALIPAY}（个人 / {ENTITY_PERSON}）")
    print(f"  咨询项目走公司对公：{ENTITY_COMPANY}")
    print("=" * 70)
