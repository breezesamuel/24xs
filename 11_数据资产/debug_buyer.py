# -*- coding: utf-8 -*-
"""调试 buyer 抽取失败：打印扁平化正文在 采购人/名称 附近的真实文本。"""
import re
import ssl
import sys
import urllib.request

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
from ccgp_pipeline import detail_text, _get  # noqa

URLS = [
    "http://www.ccgp.gov.cn/cggg/dfgg/gkzb/202610/t20261001_27439269.htm",
    "http://www.ccgp.gov.cn/cggg/dfgg/gkzb/202610/t20261001_27439268.htm",
]

for u in URLS:
    html = _get(u)
    t = detail_text(html)
    print("=" * 70)
    print(u)
    print("扁平正文 %d 字" % len(t))
    for kw in ["采购人信息", "采购人名称", "名称", "代理机构信息"]:
        for m in re.finditer(re.escape(kw), t):
            i = m.start()
            print("  [%s @%d] %r" % (kw, i, t[max(0, i - 60): i + 160]))
            break
    print()
    print("--- 尾部 900 字（联系信息通常在这）---")
    print(t[-900:])
    print()
