# -*- coding: utf-8 -*-
"""看详情页真实 DOM 结构，据此写正确的抽取器。"""
import re
import ssl
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
      "Referer": "http://www.ccgp.gov.cn/"}

u = "http://www.ccgp.gov.cn/cggg/dfgg/gkzb/202610/t20261001_27439269.htm"
raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25,
                             context=CTX).read()
s = raw.decode("utf-8", "ignore")

print("原始长度 %d" % len(s))
i = s.find("采购人")
print("\n=== '采购人' 首次出现位置 %d 上下文 1400 字符 ===" % i)
print(repr(s[max(0, i - 300): i + 1100]))

print("\n=== 查找 v_news_content / 正文容器 ===")
for pat in [r'id="v_news_content"', r'class="v_news_content"',
            r'class="vF_detail_main"', r'<div[^>]*class="[^"]*(content|detail)[^"]*"']:
    m = re.search(pat, s)
    print("  %-40s %s" % (pat, m.start() if m else "未命中"))

print("\n=== 是否含表格(采购人常在表格里) ===")
print("  <table 出现次数:", len(re.findall(r"<table", s, re.I)))
print("  <td 出现次数:", len(re.findall(r"<td", s, re.I)))
print("  采购人 出现次数:", len(re.findall(r"采购人", s)))
print("  预算 出现次数:", len(re.findall(r"预算", s)))
print("  金额 出现次数:", len(re.findall(r"金额", s)))
