# -*- coding: utf-8 -*-
"""对真实官网做 GEO 就绪度实测。
只抓公开首页，不登录、不绕过任何东西、不写任何东西。
"""
from __future__ import annotations

import gzip
import json
import re
import socket
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")

TARGETS = [
    ("上海百姓装潢有限公司", "https://shbx.com.cn/"),
    ("上海千州装饰设计工程有限公司", "http://www.shqianzhou.com/"),
    ("上海心越装潢设计有限公司", "http://www.xinyuezh.com/"),
    ("上海兜欢喜装饰", "https://www.douhuanxi.com/"),
    ("上海知贤装饰设计有限公司", "https://www.zhixianzs.com/"),
    ("上海高吉建筑装饰工程有限公司", "http://shgaoji.com/"),
    ("上海紫业装饰设计工程有限公司", "https://www.ziyehk.cn/"),
    ("上海市室内装饰行业协会", "https://www.snzsxh.com/"),
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

RE_MOBILE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
RE_LAND = re.compile(r"(?<!\d)(0\d{2,3}[-\s]?\d{7,8})(?!\d)")
RE_400 = re.compile(r"(400[-\s]?\d{3}[-\s]?\d{4})")
RE_WX = re.compile(r"(?:微信|weixin|wechat|wx)[\s:：]*([a-zA-Z][-_a-zA-Z0-9]{5,19})", re.I)
RE_QQ = re.compile(r"([1-9]\d{7,10})@qq\.com")
RE_ICP = re.compile(r"([京沪粤津渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]ICP备\d{6,10}号(?:-\d+)?)")


def fetch(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip, deflate",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            enc = "utf-8"
            m = re.search(rb"charset=[\"']?([\w-]+)", raw[:2000], re.I)
            if m:
                enc = m.group(1).decode("ascii", "ignore")
            try:
                return r.status, raw.decode(enc, "ignore"), r.geturl()
            except (LookupError, UnicodeDecodeError):
                return r.status, raw.decode("utf-8", "ignore"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception:
        return 0, "", url


def audit(item):
    name, url = item
    code, html, final = fetch(url)
    r = {"公司": name, "官网": url, "最终URL": final, "HTTP": code}

    if code != 200 or not html:
        r["错误"] = "抓取失败"
        return r

    low = html.lower()

    # --- GEO 就绪度实测 ---
    r["字数"] = len(re.sub(r"<[^>]+>", " ", html).split())
    r["有JSON-LD"] = "application/ld+json" in low
    schemas = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)
    r["Schema类型"] = ",".join(sorted(set(schemas)))[:70] or "-"
    r["有FAQ区块"] = bool(re.search(r"(faq|常见问题|问答|faqpage)", low))
    r["有llms.txt"] = False   # 单独探测，见下
    r["含AI优化信号"] = ",".join(sorted(set(re.findall(
        r'(ld\+json|faqpage|speakable|mainentity|questions?answer)', low)))) or "-"
    r["有ICP备案"] = bool(RE_ICP.search(html))
    r["ICP"] = (RE_ICP.search(html).group(1) if RE_ICP.search(html) else "-")

    # --- 公开联系方式（官网自己公示的，用于正当商务联络） ---
    phones = set(RE_MOBILE.findall(html)) | set(
        re.sub(r"[-\s]", "", x) for x in RE_LAND.findall(html))
    r["手机"] = ",".join(sorted(phones)[:3]) or "-"
    r["400"] = ",".join(sorted(set(RE_400.findall(html)))[:2]) or "-"
    r["微信"] = ",".join(sorted(set(RE_WX.findall(html)))[:3]) or "-"
    r["QQ邮箱"] = ",".join(sorted(set(RE_QQ.findall(html)))[:2]) or "-"

    # --- GEO 缺口打分：越缺越值得做 ---
    gaps = []
    if not r["有JSON-LD"]:
        gaps.append("无结构化数据")
    if not r["有FAQ区块"]:
        gaps.append("无FAQ/问答块")
    if "FAQPage" not in r["Schema类型"]:
        gaps.append("AI不认FAQ实体")
    r["缺口"] = "、".join(gaps) or "结构化基本到位"
    r["缺口数"] = len(gaps)
    return r


def main():
    print(f"实测 {len(TARGETS)} 家真实官网的 GEO 就绪度\n" + "=" * 78)
    rows = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(audit, TARGETS):
            rows.append(r)

    rows.sort(key=lambda x: -x.get("缺口数", 0))
    for r in rows:
        print(f"\n■ {r['公司']}")
        print(f"   HTTP {r['HTTP']}  {r['官网']}")
        if r.get("错误"):
            print(f"   !! {r['错误']}")
            continue
        print(f"   缺口({r['缺口数']}): {r['缺口']}")
        print(f"   结构化={r['有JSON-LD']} schema={r['Schema类型']} FAQ={r['有FAQ区块']}")
        print(f"   ICP={r['ICP']}")
        print(f"   手机={r['手机']} 400={r['400']}")
        print(f"   微信={r['微信']} QQ邮箱={r['QQ邮箱']}")

    out = r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_real.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 78)
    print(f"明细: {out}")
    ok = [r for r in rows if r["HTTP"] == 200]
    print(f"可访问 {len(ok)}/{len(rows)}；有联系方式的 "
          f"{len([r for r in ok if r['手机'] != '-' or r['微信'] != '-' or r['QQ邮箱'] != '-'])} 家")


if __name__ == "__main__":
    main()
