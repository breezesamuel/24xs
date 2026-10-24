# -*- coding: utf-8 -*-
"""宠物医院垂类：抓真实官网 + GEO 实测"""
from __future__ import annotations

import json
import re
import sys
import gzip
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")

TARGETS = [
    ("上海佩兹动物医疗", "http://www.pawivs.com/"),
    ("宠爱国际连锁动物医院", "https://www.chongaipet.com/"),
    ("上海爱侣宠物医院", "http://shanghaivet.com/"),
    ("上海宠伊宠物诊所", "http://www.chongyipet.com/"),
    ("上海爱辰宠物医院", "http://aichenpet.com/"),
    ("上海爱侣宠物医院集团", "https://www.ruichen.com/"),
    ("宠爱国际连锁", "https://www.chongaipet.com/index.html"),
    ("上海爱辰宠物医院", "http://aichenpet.com/"),
    ("上海爱侣宠物医院梅川分院", "https://www.ruichen.com/content/details_17_682.html"),
    ("上海宠瑞动物医疗", "https://35237241.1.net.cn/"),
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

RE_MOBILE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
RE_LAND = re.compile(r"(?<!\d)(0\d{2,3}[-\s]?\d{7,8})(?!\d)")
RE_400 = re.compile(r"(400[-\s]?\d{3}[-\s]?\d{4})")
RE_EMAIL = re.compile(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,})")
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
    r["字数"] = len(re.sub(r"<[^>]+>", " ", html).split())
    r["有JSON-LD"] = "application/ld+json" in low
    schemas = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)
    r["Schema类型"] = ",".join(sorted(set(schemas)))[:70] or "-"
    r["有FAQ区块"] = bool(re.search(r"(faq|常见问题|问答|faqpage)", low))
    r["有ICP备案"] = bool(RE_ICP.search(html))
    r["ICP"] = (RE_ICP.search(html).group(1) if RE_ICP.search(html) else "-")

    phones = set(RE_MOBILE.findall(html)) | set(
        re.sub(r"[-\s]", "", x) for x in RE_LAND.findall(html))
    r["手机"] = ",".join(sorted(phones)[:3]) or "-"
    r["400"] = ",".join(sorted(set(RE_400.findall(html)))[:2]) or "-"
    emails = [e for e in RE_EMAIL.findall(html) if not e.endswith((".png", ".jpg", ".css", ".js"))]
    r["邮箱"] = ",".join(sorted(set(emails))[:2]) or "-"

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
    print(f"实测 {len(TARGETS)} 家宠物医院官网 GEO 就绪度\n" + "=" * 78)
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
        print(f"   手机={r['手机']} 400={r['400']} 邮箱={r['邮箱']}")

    out = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_pet.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n明细: {out}")
    ok = [r for r in rows if r["HTTP"] == 200]
    print(f"可访问 {len(ok)}/{len(rows)}；有联系方式 {len([r for r in ok if r['手机'] != '-' or r['邮箱'] != '-' or r['400'] != '-'])} 家")


if __name__ == "__main__":
    from pathlib import Path
    main()