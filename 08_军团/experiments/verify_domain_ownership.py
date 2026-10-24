# -*- coding: utf-8 -*-
"""域名归属核验：确认名单里的官网确实是这家公司自己的站。

为什么必须单独一道闸门
----------------------
报告写的是"抓取 <官网> 得到 AI 就绪度 N 分"，然后据此告诉对方
"你的官网没有结构化数据"。如果这个官网根本不是对方的站，那这份报告
就是拿别人的网站去指认别人的问题 —— 发出去不是无效，是有害。

实测已经抓到三例：
  CSV「上海爱侣宠物医院集团」-> ruichen.com 首页自称「瑞诚(南京)宠物医院集团」
  CSV「上海爱侣宠物医院」    -> shanghaivet.com 首页自称「上海爪爪宠物医院」
  CSV「上海宠瑞动物医疗」    -> 35237241.1.net.cn（数字前缀共享主机），自称「宠熙」

设计要点
--------
1. 联网核验和网络抖动是两种事，所以本脚本**只负责产出一份证据文件**，
   不让生成草稿去依赖实时网络 —— 否则某天网络抖一下，全部线索被阻断，
   没人分得清是真有问题还是没网。
2. 判定保守：宁可标 needs_review 让人看，也不自作主张放行。
3. 自动化判不了的一律走 人工豁免名单，并且豁免必须写明理由，可追溯。

输出：99_产出/获客名单/域名归属核验.json
      { "公司": {"status": ok|mismatch|unreachable|needs_review,
                 "site":..., "title":..., "reason":...} }
      status = ok 或在人工豁免名单里，才允许生成草稿。
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"F:\2026\24xs")
LEAD_DIR = ROOT / "99_产出" / "获客名单"
VERDICT = LEAD_DIR / "域名归属核验.json"
OVERRIDE = LEAD_DIR / "域名归属_人工豁免.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)

# 地域 / 行业 / 组织形式的通用词。剥掉之后剩下的才是"这家店特有"的部分。
GENERIC = ("上海市", "上海", "北京", "深圳", "广州", "市",
           "有限公司", "有限责任公司", "股份", "集团", "公司", "连锁", "国际",
           "动物医疗", "宠物医院", "宠物诊所", "宠物", "兽医",
           "口腔", "齿科", "牙科", "医院", "门诊部", "诊所", "医学",
           "装饰", "设计", "工程", "装潢", "建筑", "装饰工程",
           "协会", "行业", "商会",
           "少儿编程", "编程", "教育", "科技", "信息",
           "艺术中心", "宴会中心", "婚礼", "婚庆", "策划", "服务")


def core_name(company: str) -> str:
    """剥掉通用词，得到公司最有辨识度的部分。"""
    s = company
    for g in GENERIC:
        s = s.replace(g, "")
    return re.sub(r"[（）()\s\-—_·、,，]", "", s)


def fetch(url: str, tries: int = 2, timeout: int = 20) -> tuple[str, str]:
    """返回 (title, 错误说明)。title 为空且无错误说明 = 抓到了但没有 title。"""
    last = ""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(400_000)
            try:
                html = raw.decode("utf-8")
            except UnicodeDecodeError:
                html = raw.decode("gbk", "replace")
            m = TITLE_RE.search(html)
            title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
            return title, ""
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:
            last = type(e).__name__
        if i + 1 < tries:
            time.sleep(2)
    return "", last


def verdict_for(company: str, site: str) -> dict:
    title, err = fetch(site)
    core = core_name(company)
    host = re.sub(r"^https?://", "", site).split("/")[0]
    host_core = re.sub(r"^(www|www\d|m)\.", "", host.split(".")[0])

    rec = {"site": site, "title": title, "error": err,
           "core": core, "host": host}

    if err:
        rec.update(status="unreachable",
                   reason=f"官网抓取失败（{err}），无法核实归属")
        return rec

    if re.match(r"^[\d.]+\.", host):
        rec.update(status="mismatch",
                   reason="数字前缀域名，是共享主机/建站平台的默认站点，"
                          "不是品牌自有域名")
        return rec

    hay = re.sub(r"[（）()\s\-_·|]", "", title + " " + host)

    # 先用"去掉地域前缀的完整公司名"对牌。
    # 这一步不能省：编程猫 剥掉通用词后只剩"猫"一个字，
    # 而"编程"恰恰是品牌名的一部分，剥了就永远匹配不上。
    full = re.sub(r"^(上海市|上海|北京|深圳|广州)", "", company)
    full = re.sub(r"[（）()\s\-—_·、,，]", "", full)
    if len(full) >= 2 and full in hay:
        rec.update(status="ok", reason=f"页面自称与公司名一致（匹配 {full}）")
        return rec

    # 再用剥完通用词的核心名逐级缩短。品牌名通常位于公司全称的前缀，
    # 所以从长到短找第一个命中的。
    #
    # 只认 3 个字以上的命中。两个字的（"爱侣""千州"）在中文里太容易
    # 撞车，认它等于放行一堆别人的站 —— ruichen.com 上就挂着一条
    # 「上海爱侣宠物医院」的收录条目，命中"爱侣"两个字，
    # 但那明显是南京瑞辰集团的站。
    MIN_CORE = 3
    if len(core) >= MIN_CORE:
        for n in range(len(core), MIN_CORE - 1, -1):
            if core[:n] in hay:
                rec.update(status="ok",
                           reason=f"页面自称与公司名一致（匹配 {core[:n]}）")
                return rec

    if not title:
        rec.update(status="needs_review",
                   reason="页面抓到了但取不到 title（可能整站由 JS 渲染），"
                          "需要人工确认归属")
        return rec

    rec.update(status="mismatch",
               reason=f"页面自称『{title[:40]}』与公司名『{company}』对不上")
    return rec


def main() -> int:
    overrides = {}
    if OVERRIDE.exists():
        overrides = json.loads(OVERRIDE.read_text(encoding="utf-8"))

    leads = []
    for p in sorted(LEAD_DIR.glob("真实名单_*.csv")):
        if ".bak-" in p.name:
            continue
        with p.open(encoding="utf-8-sig", newline="") as f:
            leads += list(csv.DictReader(f))

    # 同一公司多行只核一次
    seen, todo = set(), []
    for r in leads:
        c = (r.get("公司") or "").strip()
        s = (r.get("官网") or "").strip()
        if c and s and (c, s) not in seen:
            seen.add((c, s))
            todo.append((c, s))

    print(f"待核验 {len(todo)} 个站点（去重后）\n")
    out = {}
    for i, (company, site) in enumerate(todo, 1):
        rec = verdict_for(company, site)
        ov = overrides.get(company)
        if rec["status"] != "ok" and ov and ov.get("approve"):
            rec["status"] = "ok"
            rec["override"] = True
            rec["reason"] = (f"[人工豁免] {ov.get('reason', '未写理由')} "
                             f"（原判定：{rec['reason']}）")
        out[company] = rec
        flag = {"ok": "OK  ", "mismatch": "不符", "unreachable": "不可达",
                "needs_review": "待确认"}.get(rec["status"], "??  ")
        print(f"[{i:>2}/{len(todo)}] {flag} {company:<26} {site[:44]}")
        print(f"          {rec['reason']}")

    VERDICT.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    counts: dict[str, int] = {}
    for rec in out.values():
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1

    print()
    print("=" * 78)
    print("  归属核验结果")
    print("=" * 78)
    for k in ("ok", "needs_review", "mismatch", "unreachable"):
        if counts.get(k):
            print(f"  {k:<14} {counts[k]:>3} 家")
    blocked = sum(v for k, v in counts.items() if k != "ok")
    print(f"  {'-> 不可外发':<14} {blocked:>3} 家")
    print()
    print(f"证据已写入 {VERDICT}")
    if blocked:
        print(f"其中需要在 {OVERRIDE.name} 里写明理由才能放行。")
    print("=" * 78)
    print(f"核验时间 {datetime.now():%Y-%m-%d %H:%M:%S}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
