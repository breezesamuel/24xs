# -*- coding: utf-8 -*-
"""把 pet 实测结果转成 verified CSV 并入库"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDIT = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_pet.json")
OUT = Path(r"F:\2026\24xs\99_产出\获客名单\真实名单_上海宠物医院_2026-09-30.csv")

NAMED = {
    "上海佩兹动物医疗": "预约组",
    "上海爱侣宠物医院": "预约中心",
    "上海爱侣宠物医院集团": "总部预约",
    "上海爱侣宠物医院梅川分院": "梅川分院预约",
    "上海宠瑞动物医疗": "陈海欢",
    "宠爱国际连锁动物医院": "客服中心",
    "上海宠伊宠物诊所": "预约专员",
}

FIELDS = ["公司", "官网", "联系人", "电话", "邮箱", "微信",
          "行业", "城市", "痛点", "来源", "备注"]

NOTES = {
    "上海佩兹动物医疗":
        "24h急诊、ICU、CT/MRI齐全，但官网零结构化，搜『上海宠物急诊』AI 不提佩兹",
    "上海爱侣宠物医院":
        "创始1993年、8家分院、40+兽医师，官网零结构化，『上海宠物医院推荐』AI 不引用爱侣",
    "上海爱侣宠物医院集团":
        "瑞辰华诺集团官网有 Organization schema 但无 FAQPage，旗下分院 AI 不可见",
    "上海爱侣宠物医院梅川分院":
        "梅川分院详情页无结构化，搜『普陀宠物医院梅川』AI 不显示",
    "上海宠瑞动物医疗":
        "24h急诊ICU、骨科/牙科强项，官网零结构化，搜『松江宠物骨科』AI 不提宠瑞",
    "宠爱国际连锁动物医院":
        "已有 Organization+ContactPoint schema，但缺 FAQPage，『上海AAHA认证宠物医院』AI 不引用",
    "上海宠伊宠物诊所":
        "浦东大型综合诊所，有 BreadcrumbList+Organization，缺 FAQPage，『浦东宠物医院』AI 不显示",
}

def main() -> int:
    rows = json.loads(Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_pet.json").read_text(encoding="utf-8"))
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
            "行业": "pet_clinic",
            "城市": "上海",
            "痛点": NOTES.get(r["公司"], r.get("缺口", "")),
            "来源": "公开官网实测 geo_pet_audit.py",
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