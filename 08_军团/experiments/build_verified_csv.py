# -*- coding: utf-8 -*-
"""把 geo_real_audit 的实测结果转成「已核验」名单 CSV。
只写官网自己公示的商务联系方式；过滤 JS 变量名等假微信号。
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDIT = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_real.json")
OUT = Path(r"F:\2026\24xs\99_产出\获客名单\真实名单_上海装修_2026-09-30.csv")

# 搜索结果里人工核对的联系人（官网正文写明"联系人/对接"的）
NAMED = {
    "上海心越装潢设计有限公司": "陈经理",
    "上海知贤装饰设计有限公司": "任经理",
    "上海紫业装饰设计工程有限公司": "Perry",
}

# JS 变量名 / 组件名，不是微信号
WX_JUNK = {"mediaid", "shareicon", "gc4uqq", "weixin", "wechat", "wx",
           "appid", "openid", "channel", "default", "undefined"}

# 已实测的结构化缺口 + 官网自述卖点，合成痛点描述
NOTES = {
    "上海千州装饰设计工程有限公司":
        "官网无任何 JSON-LD，AI 无法解析为实体；无问答块",
    "上海心越装潢设计有限公司":
        "官网无结构化数据；主推20年装修但AI搜『崇明装修公司』不被引用",
    "上海兜欢喜装饰":
        "无 FAQPage schema；靠吉美装饰背书但AI检索不到品牌实体",
    "上海高吉建筑装饰工程有限公司":
        "腾云建站模板站，零结构化数据，纯视觉稿，AI完全不可读",
    "上海百姓装潢有限公司":
        "国企背景但无结构化数据；『上海装修公司推荐』类问题不被AI引用",
    "上海市室内装饰行业协会":
        "协会官网无结构化数据；会员单位批量缺AI可读信息",
    "上海知贤装饰设计有限公司":
        "结构化已到位，作为标杆对照组（AI可解析）",
    "上海紫业装饰设计工程有限公司":
        "结构化已到位，作为标杆对照组（AI可解析）",
}

FIELDS = ["公司", "官网", "联系人", "电话", "邮箱", "微信",
          "行业", "城市", "痛点", "来源", "备注"]


def clean_wx(raw: str) -> str:
    out = []
    for w in (x.strip() for x in raw.split(",")):
        if not w or w.lower() in WX_JUNK:
            continue
        if not re.fullmatch(r"[a-zA-Z][-_a-zA-Z0-9]{5,19}", w):
            continue
        out.append(w)
    return ",".join(out)


def main() -> int:
    rows = json.loads(AUDIT.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)

    kept = []
    for r in rows:
        if r.get("HTTP") != 200:
            print(f"[SKIP] 不可访问: {r['公司']}")
            continue

        # 多个号码用 "/" 分隔；导入器只接受单号
        mobiles = [x for x in (r.get("手机", "-")).split(",") if x and x != "-"]
        land = [x for x in (r.get("400", "-")).split(",") if x and x != "-"]
        nums = mobiles + land
        # 手���上留一个最能打通的：优先手机
        phone = nums[0] if nums else ""
        extra = " / ".join(nums[1:])
        qq = r.get("QQ邮箱", "-")
        email = f"{qq}@qq.com" if qq != "-" else ""
        wx = clean_wx(r.get("微信", "-"))

        contact = NAMED.get(r["公司"], "官网客服")
        reach = [x for x in (phone, email, wx) if x and x != "-"]
        if not reach:
            print(f"[SKIP] 无公开联系方式: {r['公司']}")
            continue

        # 已经把结构化做好的，不是目标客户，标为对照组
        tier_note = "对照组-结构化已达标" if r.get("缺口数", 0) == 0 else \
                    f"实测缺口{r['缺口数']}项"

        kept.append({
            "公司": r["公司"],
            "官网": r["官网"],
            "联系人": contact,
            "电话": phone if phone != "-" else "",
            "邮箱": email,
            "微信": wx,
            "行业": "home_improvement",
            "城市": "上海",
            "痛点": NOTES.get(r["公司"], r.get("缺口", "")),
            "来源": "公开官网实测 geo_real_audit.py",
            "备注": f"{tier_note} | ICP={r.get('ICP','-')}"
                    + (f" | 备用号码 {extra}" if extra else ""),
        })

    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(kept)

    print(f"[OK] 写入 {len(kept)} 行 -> {OUT}")
    print()
    for k in kept:
        tag = "对照组" if "对照组" in k["备注"] else "可触达"
        print(f"  [{tag}] {k['公司']}")
        print(f"        {k['电话'] or '-'} | wx={k['微信'] or '-'} | {k['痛点'][:34]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
