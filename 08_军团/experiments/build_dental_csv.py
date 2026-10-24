# -*- coding: utf-8 -*-
"""把 dental 实测结果转成 verified CSV 并入库"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDIT = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_dental.json")
OUT = Path(r"F:\2026\24xs\99_产出\获客名单\真实名单_上海口腔_2026-09-30.csv")

NAMED = {
    "上海夕阳红口腔门诊部": "前台/预约组",
    "上海汇尚口腔": "预约专员",
    "上海市同济口腔医院": "预约中心",
}

FIELDS = ["公司", "官网", "联系人", "电话", "邮箱", "微信",
          "行业", "城市", "痛点", "来源", "备注"]

NOTES = {
    "上海摩尔口腔医院集团":
        "连锁大牌但官网零结构化，搜『上海种植牙哪家好』AI 不提摩尔",
    "上海夕阳红口腔门诊部":
        "专注中老年修复 5 万+ 例，官网纯文本，AI 无法解析实体",
    "上海鑫齿口腔医院":
        "连锁品牌、免费热线 400，但官网无 JSON-LD，AI 完全不识别",
    "上海市同济口腔医院":
        "三甲公立、权威背书，官网却无任何结构化数据，极大浪费品牌资产",
    "上海汇尚口腔":
        "静安核心区、多电话多邮箱，官网无 FAQPage，『静安种植牙』问法不被引用",
    "华尔康口腔":
        "16 家分院、400+ 人团队，官网无 schema，搜『上海正畸专家』AI 不见华尔康",
    "齐白雅口腔":
        "结构化已到位（含 Dentist/FAQPage/GeoCoordinates），作为对照组",
}

def main() -> int:
    rows = json.loads(AUDIT.read_text(encoding="utf-8"))
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
        wx = ""  # dental 无微信公开

        contact = NAMED.get(r["公司"], "官网客服/预约组")
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
            "行业": "dental_clinic",
            "城市": "上海",
            "痛点": NOTES.get(r["公司"], r.get("缺口", "")),
            "来源": "公开官网实测 geo_dental_audit.py",
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