# -*- coding: utf-8 -*-
"""把 kidscode 实测结果转成 verified CSV 并入库"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDIT = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_kidscode_v2.json")
OUT = Path(r"F:\2026\24xs\99_产出\获客名单\真实名单_上海少儿编程_2026-09-30.csv")

NAMED = {
    "妙小程少儿编程": "招生顾问",
    "码高教育": "课程顾问",
    "编玩边学": "课程顾问",
    "斯坦星球科创编程": "市场部",
    "码趣学院": "招生老师",
    "小码王少儿编程": "客服中心",
    "大师码科技成长中心": "招生主管",
    "编程猫": "客服中心",
}

FIELDS = ["公司", "官网", "联系人", "电话", "邮箱", "微信",
          "行业", "城市", "痛点", "来源", "备注"]

NOTES = {
    "妙小程少儿编程":
        "在线少儿编程平台，400热线，但官网零结构化，搜『上海少儿编程在线』AI 不提妙小程",
    "码高教育":
        "北京总部、专精特新企业、信奥赛强项，官网零结构化，搜『北京信奥赛培训』AI 不提码高",
    "编玩边学":
        "ISTE国际认证、SPO合作、Green STEM独家，官网零结构化，搜『ISTE认证少儿编程』AI 不提编玩边学",
    "斯坦星球科创编程":
        "140+学习中心、STEM&AIGC课程体系、自研Circle Bit硬件，官网零结构化，搜『上海STEM教育』AI 不提斯坦星球",
    "码趣学院":
        "海外名校团队、PBL项目式教学、CodingMarch品牌，官网零结构化，搜『上海少儿编程PBL』AI 不提码趣",
    "小码王少儿编程":
        "浙ICP备案、已有FAQ区块但无FAQPage schema，搜『杭州少儿编程』AI 不充分引用小码王",
    "大师码科技成长中心":
        "结构化已到位（含EducationalOrganization/FAQPage/PostalAddress），作为对照组",
    "编程猫":
        "头部品牌、结构化已到位（含Brand/Course/EducationalOrganization/FAQPage），作为对照组",
}

def main() -> int:
    rows = json.loads(Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_kidscode_v2.json").read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)

    kept = []
    for r in rows:
        if r.get("HTTP") != 200:
            print(f"[SKIP] 不可访问: {r['公司']}")
            continue

        mobiles = [x for x in (r.get("手机", "-")).split(",") if x and x != "-"]
        lands = [x for x in (r.get("400", "-")).split(",") if x and x != "-"]
        nums = mobiles + lands
        phone = nums[0] if nums else ""
        extra = " / ".join(nums[1:]) if len(nums) > 1 else ""

        emails = [x for x in (r.get("邮箱", "-")).split(",") if x and x != "-"]
        email = emails[0] if emails else ""
        wx = ""

        contact = NAMED.get(r["公司"], "官网客服/招生顾问")
        reach = [x for x in (phone, email, wx) if x]
        if not reach:
            print(f"[SKIP] 无公开联系方式: {r['公司']}")
            continue

        tier_note = "对照组-结构化已达标" if r.get("缺口数", 0) == 0 else \
                    f"实测缺口{r['缺口数']}项"

        kept.append({
            "公司": r["公司"],
            "官网": r["官网"],
            "联系人": contact,
            "电话": phone,
            "邮箱": email,
            "微信": wx,
            "行业": "kids_coding",
            "城市": "上海",
            "痛点": NOTES.get(r["公司"], r.get("缺口", "")),
            "来源": "公开官网实测 geo_kidscode_audit_v2.py",
            "备注": f"{tier_note} | ICP={r.get('ICP','-')}"
                    + (f" | 备用号码 {extra}" if extra else ""),
        })

    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(kept)

    print(f"[OK] 写入 {len(kept)} 行 -> {OUT}\n")
    for k in kept:
        tag = "对照组" if "对照组" in k["备注"] else "可触达"
        print(f"  [{tag}] {k['公司']}")
        print(f"        {k['电话'] or '-'} | {k['邮箱'] or '-'} | {k['痛点'][:34]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())