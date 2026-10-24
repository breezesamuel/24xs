# -*- coding: utf-8 -*-
"""审计所有外发草稿里的两处致命问题。

1. 冒充微信：CONTACT_WECHAT 未配置，却在正文里承诺"加微信 460123249"
2. 报价冲突：正文承诺 6-15 万，但系统硬下限是 221,000

这两种话发出去不是丢单，是让客户以为我们在骗他。
"""
from __future__ import annotations

import email
import email.policy
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

EML_DIR = Path(r"F:\2026\24xs\99_产出\外发草稿")
FLOOR = 221_000
QQ = "460123249"

# 文件名里认垂类的关键词 -> 短 key（与 gen_all_drafts.FILE_HINT 对应）
FILE_HINT = {
    "婚庆": "wedding", "婚礼": "wedding",
    "口腔": "dental", "齿": "dental", "牙": "dental",
    "宠物": "pet", "动物": "pet",
    "编程": "kidscode", "编程猫": "kidscode", "星球": "kidscode",
    "装修": "decoration", "装饰": "decoration", "设计": "decoration",
}

# 任何暗示"这个数字是我的微信号"的写法
WEHAT_PAT = [
    re.compile(r"微信\s*[:：]?\s*" + QQ),
    re.compile(r"加微" + r"\s*[信号]?" + r"[^。\n]{0,6}" + QQ),
    re.compile(r"微信号\s*(?:是|为|:|：)?\s*" + QQ),
    re.compile(r"同\s*QQ"),
    re.compile(r"(?:V|v)信\s*" + QQ),
]
# 任何给出具体金额区间/起价的承诺。
#
# 两个必须踩过的坑：
# 1. 中文排版里"6–15 万"用的是 EN DASH U+2013，不是 ASCII '-'。
#    最初只写了 ASCII 连字符，导致这项检查对真实草稿**完全失效**——
#    它报"无问题"，但 24 封草稿全都写着 6–15 万。
# 2. 单位在区间**之后**（`6–15 万`），不是两侧都有（`6万-15万`）。两种都得认。
DASHES = "\u002d\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFF0D\u30FC\u007E"
_UNIT = "(?:万|w|W|千|k|K)"
PRICE_PAT = re.compile(
    # 形式 A：6–15 万 / 6 到 15 千      （单位在后）
    r"(\d+)\s*(?:[" + DASHES + r"]|到|至)\s*(\d+)\s*" + _UNIT +
    # 形式 B：6万–15万                   （单位两侧都有）
    r"|(\d+)\s*" + _UNIT + r"\s*(?:[" + DASHES + r"]|到|至)\s*(\d+)\s*" + _UNIT +
    # 形式 C：6 万起
    r"|(\d+)\s*" + _UNIT + r"\s*起"
)


def load(fp: Path) -> str:
    msg = email.message_from_bytes(fp.read_bytes(), policy=email.policy.default)
    parts = []
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and p.get_content_disposition() != "attachment":
                parts.append(str(p.get_content()))
    else:
        parts.append(str(msg.get_content()))
    return "\n".join(parts)


def norm_to_yuan(n: int, unit: str | None) -> int:
    """6 万 -> 60000；6 千 -> 6000。unit 缺失时按元处理。"""
    if not unit:
        return n
    return n * 10000 if unit in "万wW" else n * 1000


def main() -> int:
    files = sorted(EML_DIR.glob("*.eml"))
    if not files:
        print(f"[!] {EML_DIR} 下没有 .eml")
        return 1

    wx_bad, price_bad, price_list = [], [], []
    for fp in files:
        body = load(fp)
        hits_wx = [p.pattern for p in WEHAT_PAT if p.search(body)]
        m = PRICE_PAT.search(body)
        price_txt = None
        if m:
            if m.group(1):                       # 形式 A：6–15 万（两端共用末尾单位）
                lo = norm_to_yuan(int(m.group(1)), m.group(3))
                hi = norm_to_yuan(int(m.group(2)), m.group(3))
            elif m.group(4):                     # 形式 B：6万–15万
                lo = norm_to_yuan(int(m.group(4)), m.group(5))
                hi = norm_to_yuan(int(m.group(6)), m.group(7))
            else:                                 # 形式 C：6 万起
                lo = hi = norm_to_yuan(int(m.group(8)), m.group(9))
            price_txt = f"{lo:,}~{hi:,}" if lo != hi else f"{lo:,}"
            price_list.append((fp.name, lo, hi, price_txt))
            if hi < FLOOR:
                price_bad.append((fp.name, price_txt))
        if hits_wx:
            wx_bad.append((fp.name, len(hits_wx)))

    print(f"扫描 {len(files)} 封草稿\n")
    print("=" * 74)
    print(f"[A] 冒充微信（CONTACT_WECHAT 未配置却承诺微信联系）")
    print("=" * 74)
    if wx_bad:
        for n, c in wx_bad:
            print(f"  [FAIL] {n}  ({c} 处)")
        print(f"\n  => {len(wx_bad)}/{len(files)} 封含假微信承诺")
    else:
        print("  [OK] 无")

    print()
    print("=" * 74)
    print(f"[B] 报价低于硬下限 ¥{FLOOR:,}")
    print("=" * 74)
    if price_list:
        for n, lo, hi, txt in price_list:
            flag = "FAIL" if hi < FLOOR else "OK  "
            print(f"  [{flag}] {txt:>18}  {n}")
        if price_bad:
            print(f"\n  => {len(price_bad)} 封报价上限低于下限 ¥{FLOOR:,}")
    else:
        print("  [OK] 草稿正文未出现具体金额承诺（报价只在谈判时口头给）")

    print()
    print("=" * 74)
    print("[C] 垂类串味（正文必须用上本垂类的搜索词与受众词）")
    print("=" * 74)
    # 直接引用生成器的表，不再手写一份关键词清单 ——
    # 手写那份和生成器的表各走各的，检查就成了自欺。
    from gen_all_drafts import AUDIENCE, QUERY, industry_of  # noqa: E402

    vert_bad = 0
    for fp in files:
        body = load(fp)
        stem = re.sub(r"^外发_|_[\d]{4}(?:_\d+)?\.eml$", "", fp.stem)
        ind = next((v for k, v in FILE_HINT.items() if k in stem), None)
        if not ind:
            # 名称里认不出垂类，就用正文里的搜索词反推
            ind = next((k for k, qs in QUERY.items()
                        if any(q in body for q in qs)), "")
        if not ind:
            print(f"  [FAIL] {fp.name}  垂类无法判定")
            vert_bad += 1
            continue
        missing = [q for q in QUERY.get(ind, [])[:1] if q not in body]
        aud = AUDIENCE.get(ind, "")
        if aud and aud not in body:
            missing.append(aud)
        if missing:
            print(f"  [FAIL] {fp.name}  缺 {missing}")
            vert_bad += 1
    if not vert_bad:
        print(f"  [OK] {len(files)} 封垂类一致，无串味")
    else:
        print(f"  => {vert_bad}/{len(files)} 封串味或缺垂类关键词")

    print()
    print("=" * 74)
    bad = len(wx_bad) + len(price_bad) + vert_bad
    print(f"结论：{bad} 处问题 / 共 {len(files)} 封")
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
