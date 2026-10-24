# -*- coding: utf-8 -*-
"""婚庆垂类：抓真实官网 + GEO 实测（v2，仅官方自有域名）

v1 的 5 个目标里有 2 个是第三方目录页（100ec.cn / 6a6a.net），
把目录页当"客户官网"来审计是失真的，v2 只保留公司自有域名。
"""
from __future__ import annotations

import gzip
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phoneutil  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

TARGETS = [
    ("摩可纳婚礼艺术中心", "https://www.imocona.com/", "上海", "十五座婚礼场馆/超20000㎡/花园洋房式"),
    ("圣拉维婚礼会所 C.LA.V", "https://www.slwwedding.com/", "上海", "一站式婚礼会所/婚宴酒店预订"),
    ("上海华盛婚礼会馆", "http://www.hsweds.com/", "上海", "连锁婚礼会馆/大众点评五星"),
    ("上海韵礼芳兮婚庆礼仪", "http://yunlifangxi.com/", "上海", "西式婚礼策划/司仪团队/闵行"),
    ("启蔻婚礼 CHOCO", "https://www.choco.com.cn/", "上海", "婚礼策划/多城覆盖"),
    ("格莱美婚礼宴会中心", "https://www.grammywedding.com/", "上海", "婚礼宴会中心"),
    ("圣诺莉婚礼艺术中心", "https://www.saintnolly.com/", "上海", "浦东/松江门店/一站式婚礼会所"),
    ("凯芙俪婚庆", "http://kfljiehun.com/", "全国", "一站式婚礼服务"),
    ("花嫁丽舍婚礼殿堂", "https://www.huajialishe.com/", "上海", "沪上市公司/4692万注册资本"),
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

RE_MOBILE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
RE_400 = re.compile(r"(400[-\s]?\d{3,4}[-\s]?\d{3,4})")
RE_EMAIL = re.compile(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,})")
RE_ICP = re.compile(
    r"([京沪粤津渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]"
    r"ICP备\d{6,10}号(?:-\d+)?)")
# <script>/<style>/注释里的数字串不是联系方式。实测 mocona / choco 的
# JS 里能抓出 06513492989、089888689418 这类根本不存在的话费号码，
# 必须先剥掉再抽。
RE_NOISE = re.compile(r"(?is)<(script|style|noscript)\b.*?</\1\s*>")
RE_COMMENT = re.compile(r"(?s)<!--.*?-->")
RE_TAG = re.compile(r"(?s)<[^>]+>")


def visible_text(html: str) -> str:
    """只返回用户真正能看到的文字，用于抽联系方式。"""
    s = RE_NOISE.sub(" ", html)
    s = RE_COMMENT.sub(" ", s)
    s = RE_TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s)


def extract_contacts(html: str) -> tuple[str, str, str]:
    """返回 (手机, 400, 邮箱)；只从可见文字里抽，且逐个校验合法性。"""
    vis = visible_text(html)
    mobiles = [x for x in RE_MOBILE.findall(vis) if phoneutil.is_valid(x)]
    t400 = [x for x in RE_400.findall(vis) if phoneutil.is_valid(x)]
    mails = [e for e in RE_EMAIL.findall(vis)
             if not e.endswith((".png", ".jpg", ".css", ".js", ".gif", ".webp", ".svg"))]
    seen, m400, mmail = set(), [], []
    for x in mobiles:
        if x not in seen:
            seen.add(x)
    for x in t400:
        k = re.sub(r"\D", "", x)
        if k not in [re.sub(r"\D", "", y) for y in m400]:
            m400.append(x)
    for x in mails:
        if x.lower() not in {y.lower() for y in mmail}:
            mmail.append(x)
    return (",".join(sorted(seen)[:3]) or "-",
            ",".join(m400[:2]) or "-",
            ",".join(sorted(set(mmail))[:2]) or "-")


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
            m = re.search(rb"charset=[\"']?([\w-]+)", raw[:2000], re.I)
            enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
            try:
                return r.status, raw.decode(enc, "ignore"), r.geturl()
            except (LookupError, UnicodeDecodeError):
                return r.status, raw.decode("utf-8", "ignore"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception:
        return 0, "", url


def audit(item):
    name, url, city, asset = item
    code, html, final = fetch(url)
    r = {"公司": name, "官网": url, "最终URL": final, "HTTP": code,
         "城市": city, "核心资产": asset}

    if code != 200 or not html:
        r["错误"] = "抓取失败"
        return r

    low = html.lower()
    text = re.sub(r"<[^>]+>", " ", html)

    # 防目录页：命中这些说明不是自有官网
    if any(k in low for k in ("cnpp.cn", "jiayubao", "91goodschool",
                              "peixunsj", "gaokao.cn", "edu84", "wancili",
                              "findingschool", "icp.bugscaner", "baike.baidu")):
        r["错误"] = "疑似第三方目录页，不作为官网"
        return r

    r["字数"] = len(text.split())
    r["有JSON-LD"] = "application/ld+json" in low
    schemas = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)
    r["Schema类型"] = ",".join(sorted(set(schemas)))[:70] or "-"
    r["有FAQ区块"] = bool(re.search(r"(faq|常见问题|问答|faqpage)", low))
    m_icp = RE_ICP.search(html)
    r["ICP"] = m_icp.group(1) if m_icp else "-"

    r["手机"], r["400"], r["邮箱"] = extract_contacts(html)

    # 婚庆特有的高意图词，看官网自己写没写
    r["有价格"] = bool(re.search(r"(价格|报价|套餐|预算|万元|元起)", text))
    r["有案例"] = bool(re.search(r"(案例|客片|婚礼实景|作品|婚礼花絮)", text))

    gaps = []
    if not r["有JSON-LD"]:
        gaps.append("无结构化数据")
    if "FAQPage" not in r["Schema类型"]:
        gaps.append("无FAQPage实体")
    if not r["有FAQ区块"]:
        gaps.append("无问答正文")
    if not r["有价格"]:
        gaps.append("无公开价格/套餐")
    if not r["有案例"]:
        gaps.append("无婚礼案例/客片")
    r["缺口"] = "、".join(gaps) or "结构化基本到位"
    r["缺口数"] = len(gaps)
    return r


def main():
    print(f"实测 {len(TARGETS)} 家婚庆官网 GEO 就绪度\n" + "=" * 78)
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
        print(f"   结构化={r['有JSON-LD']} FAQ区块={r['有FAQ区块']} "
              f"价格={r['有价格']} 案例={r['有案例']}")
        print(f"   ICP={r['ICP']}")
        print(f"   手机={r['手机']} 400={r['400']} 邮箱={r['邮箱']}")

    out = Path(r"C:\Users\46012\AppData\Local\Temp\opencode\geo_audit_wedding_v2.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n明细: {out}")
    ok = [r for r in rows if r["HTTP"] == 200 and not r.get("错误")]
    with_contact = [r for r in ok if r["手机"] != "-" or r["邮箱"] != "-" or r["400"] != "-"]
    print(f"可用官网 {len(ok)}/{len(rows)}；有联系方式 {len(with_contact)} 家")
    print(f"有 GEO 缺口(>=3项) {len([r for r in ok if r['缺口数'] >= 3])} 家")


if __name__ == "__main__":
    main()
