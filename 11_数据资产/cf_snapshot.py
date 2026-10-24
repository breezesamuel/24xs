# -*- coding: utf-8 -*-
"""用【线上 Cloudflare 边缘引擎】重跑基准，让网站上挂的数字 = 用户实际点出来的数字。

为什么要这样：网站上写「平均 42.2 分」，但按钮调用的是边缘 Function。
如果两个引擎跑出的数不一样，网站就是在展示自己工具跑不出来的结论 —— 那是欺骗。
边缘是真的从 AI 爬虫所在网络出发，严格说比国内本机更接近"AI 会不会抓到你"。

本脚本：
  1. 调 https://geo-audit-cn.pages.dev/api/audit 逐站体检（浏览器 UA，否则被 CF 1010 拦）
  2. 落盘 cf_results.json
  3. 打印与本地结果的差异，差异大的人工看
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(r"F:\2026\24xs")
ENDPOINT = "https://geo-audit-cn.pages.dev/api/audit"
BUA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def call(url: str, tries: int = 3):
    q = ENDPOINT + "?url=" + urllib.parse.quote(url, safe="")
    for i in range(tries):
        req = urllib.request.Request(q, headers={"User-Agent": BUA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=75) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if i == tries - 1:
                return {"url": url, "error": f"{type(e).__name__}: {str(e)[:60]}"}
    return {"url": url, "error": "unknown"}


def main() -> None:
    local = json.loads((ROOT / "99_产出" / "GEO体检报告" / "results.json").read_text(encoding="utf-8"))
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        edge = list(ex.map(lambda r: call(r["url"]), local))

    print(f"{'本地':>4} {'边缘':>4}  {'行业':<8} 网址")
    diffs = []
    for lo, ed in zip(local, edge):
        es = ed.get("score", "ERR")
        ind = ed.get("industry", "")
        mark = ""
        if isinstance(es, int) and es != lo["score"]:
            mark = "  <-- 差异"
            diffs.append((lo["url"], lo["score"], es))
        print(f"{lo['score']:>4} {str(es):>4}  {ind:<8} {lo['url']}{mark}")

    scored = [e for e in edge if isinstance(e.get("score"), int)]
    skip = [e for e in edge if not isinstance(e.get("score"), int) or e.get("unreachable") or e.get("waf_blocked")]
    usable = [e for e in scored if not e.get("unreachable") and not e.get("waf_blocked")]
    avg = round(sum(e["score"] for e in usable) / max(1, len(usable)), 1)
    print(f"\n边缘可打分 {len(usable)}/{len(edge)}  平均 {avg}")
    print(f"差异 {len(diffs)} 处")

    out = ROOT / "11_数据资产"
    (out / "cf_results.json").write_text(
        json.dumps(edge, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {out / 'cf_results.json'}")


if __name__ == "__main__":
    main()