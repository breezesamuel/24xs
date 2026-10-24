# -*- coding: utf-8 -*-
"""audit_drafts 检测器的回归测试。

这个文件存在的原因：PRICE_PAT 最初只写了 ASCII 连字符 '-',
而草稿正文里真实用的是 EN DASH (U+2013)，导致"报价低于硬下限"
这项检查对真实文本**完全失效**——它报"无问题"，但 24 封草稿
全都写着 6–15 万。

防回归就是把这些 dash 变体逐个钉死。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

from audit_drafts import PRICE_PAT, WEHAT_PAT, norm_to_yuan  # noqa: E402

FLOOR = 221_000


def hits_price(s: str) -> bool:
    return bool(PRICE_PAT.search(s))


def hits_wechat(s: str) -> bool:
    return any(p.search(s) for p in WEHAT_PAT)


CASES_PRICE = [
    # (文本, 应当命中, 说明)
    ("整改报价（6-15 万）", True, "ASCII 连字符"),
    ("整改报价（6\u201315 万）", True, "EN DASH U+2013 ← 真实草稿用的就是这个"),
    ("整改报价（6\u201415 万）", True, "EM DASH U+2014"),
    ("整改报价（6\u201015 万）", True, "HYPHEN U+2010"),
    ("整改报价（6\u201115 万）", True, "NON-BREAKING HYPHEN U+2011"),
    ("整改报价（6\u201215 万）", True, "FIGURE DASH U+2012"),
    ("整改报价（6\u221215 万）", True, "MINUS SIGN U+2212"),
    ("整改报价（6\uff0d15 万）", True, "全角连字符 U+FF0D"),
    ("整改报价（6到15 万）", True, "中文『到』"),
    ("整改报价（6至15 万）", True, "中文『至』"),
    ("整改报价（6~15 万）", True, "波浪号"),
    ("6 万起", True, "起价也算报价"),
    ("60,000 起", False, "纯数字无单位不是本检查的范围"),
    ("按缺口项出整改报价（按项结算）", False, "不给具体数字 = 合规"),
    ("不达标不收尾款", False, "无关句"),
]

CASES_WECHAT = [
    ("加微信 460123249（同 QQ）", True, "原文"),
    ("微信：460123249", True, "冒号形式"),
    ("微信号是 460123249", True, "是字形式"),
    ("加微 460123249", True, "省略『信』"),
    ("用 QQ 460123249 找我", False, "QQ 是真实渠道，不算冒充"),
    ("mailto:460123249@qq.com", False, "邮箱是真实渠道"),
]


def main() -> int:
    fails = []
    print("=" * 74)
    print("PRICE_PAT 回归（每种 dash 变体都必须命中）")
    print("=" * 74)
    for text, want, why in CASES_PRICE:
        got = hits_price(text)
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] want={want!s:5} got={got!s:5} {why}")
        if not ok:
            fails.append(f"PRICE {text!r}")

    print()
    print("=" * 74)
    print("WEHAT_PAT 回归（QQ/邮箱不算冒充微信）")
    print("=" * 74)
    for text, want, why in CASES_WECHAT:
        got = hits_wechat(text)
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] want={want!s:5} got={got!s:5} {why}")
        if not ok:
            fails.append(f"WECHAT {text!r}")

    print()
    print("=" * 74)
    print("norm_to_yuan 换算")
    print("=" * 74)
    for n, unit, want in [(15, "万", 150_000), (221, "万", 2_210_000),
                          (50, "k", 50_000), (3, "万", 30_000)]:
        got = norm_to_yuan(n, unit)
        ok = got == want
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}{unit} -> {got:,} (期望 {want:,})")
        if not ok:
            fails.append(f"NORM {n}{unit}")

    print()
    print("=" * 74)
    if fails:
        print(f"[FAIL] {len(fails)} 项回归失败")
        for f in fails:
            print(f"       - {f}")
        print("=" * 74)
        return 1
    total = len(CASES_PRICE) + len(CASES_WECHAT) + 3
    print(f"[OK] {total}/{total} 回归通过")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
