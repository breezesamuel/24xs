# -*- coding: utf-8 -*-
"""导入「已核验」名单。

背景：offline_lead_gen.py 产出的是 random 生成的假公司/假联系人，
证据链接是 f"#result_{random.randint(1,50)}"，CSV 里连电话邮箱字段都没有。
那份东西不能发。本脚本只接受你手工整理的真实名单。

用法：
    python -X utf8 import_verified_leads.py --csv 我的名单.csv
    python -X utf8 import_verified_leads.py --csv 我的名单.csv --dry-run
    python -X utf8 import_verified_leads.py --csv 我的名单.csv --template

必需列（中文或英文表头都认）：
    公司 / company        必填
    官网 / site           必填 —— 用作真实性交叉校验的锚点
    联系人 / contact      必填
    联系方式 / phone 或 email 或 wechat   至少有一个，且要像真的
可选：
    行业 / industry、城市 / city、痛点 / pain、来源 / source、备注

安全约束：
  - 任何一行校验不过就整批拒绝，不做"部分导入"（半真半假的名单比没有更危险）
  - 只写 leads 表，status='new_verified'，绝不自动发送
  - 幂等：同公司已存在则跳过，不重复入库
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "01_引擎"))
sys.stdout.reconfigure(encoding="utf-8")

COL_ALIASES = {
    "company":  ["公司", "公司名称", "company", "企业", "企业名称"],
    "site":     ["官网", "网址", "网站", "site", "url", "homepage", "product"],
    "contact":  ["联系人", "contact", "称呼", "对接人"],
    "phone":    ["电话", "手机", "phone", "mobile", "tel", "联系电话"],
    "email":    ["邮箱", "邮件", "email", "mail", "电子邮箱"],
    "wechat":   ["微信", "wechat", "weixin", "wx"],
    "industry": ["行业", "industry", "赛道"],
    "city":     ["城市", "city", "地区", "所在地"],
    "pain":     ["痛点", "pain", "问题", "需求"],
    "source":   ["来源", "source", "出处", "怎么找到的"],
    "note":     ["备注", "note", "remark", "说明"],
}

REQUIRED = ("company", "site", "contact")

# 明显不是真实公司/联系方式的痕迹。
# 含"某某"是必须的：导入器自己生成的模板行就是"上海某某装饰工程有限公司"，
# 如果它能通过校验，说明校验形同虚设。
FAKE_HINTS = ("XX", "某某", "某公司", "示例", "样例", "测试", "test", "demo",
              "公司A", "公司B", "abc", "aaa")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[A-Za-z]{2,}(\.[A-Za-z]{2,})?$")
# 电话改用 phoneutil（真实区号白名单 + 座机必须带分隔符），
# 旧的 ^0\d{2,3}[-\s]?\d{7,8}$ 会放行 06513492989 这种网页噪音。
import phoneutil  # noqa: E402
WECHAT_RE = re.compile(r"^[a-zA-Z][-_a-zA-Z0-9]{5,19}$")

TEMPLATE_FIELDS = ["公司", "官网", "联系人", "电话", "邮箱", "微信",
                   "行业", "城市", "痛点", "来源", "备注"]


def norm_key(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "").replace("﻿", "")


def map_headers(fieldnames: list[str]) -> dict[str, str]:
    got = {norm_key(f): f for f in fieldnames if f}
    out: dict[str, str] = {}
    for canon, aliases in COL_ALIASES.items():
        for a in aliases:
            if norm_key(a) in got:
                out[canon] = got[norm_key(a)]
                break
    return out


def row_value(row: dict, colmap: dict, canon: str) -> str:
    src = colmap.get(canon)
    return (row.get(src, "") or "").strip() if src else ""


def validate(rows: list[dict]) -> tuple[list[dict], list[str]]:
    ok, errs = [], []
    seen: set[str] = set()
    for i, r in enumerate(rows, start=2):   # 2 = 表头后第一行
        bad = []

        company = r["company"]
        if not company:
            bad.append("公司名为空")
        elif any(h in company for h in FAKE_HINTS):
            bad.append(f"公司名含疑似占位/示例字样: {company!r}")
        if company in seen:
            bad.append(f"文件内重复公司: {company}")
        seen.add(company)

        site = r["site"]
        if not site:
            bad.append("官网为空（无法交叉校验真实性）")
        elif not re.match(r"^https?://", site, re.I):
            bad.append(f"官网需带 http(s):// : {site!r}")

        if not r["contact"]:
            bad.append("联系人为空")

        reach = [r["phone"], r["email"], r["wechat"]]
        reach = [x for x in reach if x]
        if not reach:
            bad.append("电话/邮箱/微信 至少填一个")
        else:
            if r["email"] and not EMAIL_RE.match(r["email"]):
                bad.append(f"邮箱格式不对: {r['email']!r}")
            if r["phone"] and not phoneutil.is_valid(r["phone"]):
                bad.append(f"电话格式不对: {r['phone']!r}")
            if r["wechat"] and not WECHAT_RE.match(r["wechat"]):
                bad.append(f"微信号格式不对: {r['wechat']!r}")

        if bad:
            errs.append(f"  第 {i} 行 [{company or '?'}]：\n    - " + "\n    - ".join(bad))
        else:
            r["_line"] = i
            ok.append(r)
    return ok, errs


def write_template(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(TEMPLATE_FIELDS)
        w.writerow(["上海某某装饰工程有限公司", "https://www.example-a.com", "王总",
                    "13800138000", "", "", "home_improvement", "上海",
                    "问『上海装修公司推荐』只提竞品", "企查查人工搜索", "示例行，导入前请删除"])
    print(f"[OK] 已生成模板: {path}")
    print("     填好后删掉示例行再导入。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--template", type=Path)
    a = ap.parse_args()

    if a.template:
        write_template(a.template)
        return 0
    if not a.csv:
        ap.print_help()
        return 2
    if not a.csv.exists():
        print(f"[FAIL] 文件不存在: {a.csv}")
        return 1

    with a.csv.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("[FAIL] CSV 为空")
        return 1

    colmap = map_headers(list(rows[0].keys()))
    missing = [c for c in REQUIRED if c not in colmap]
    if missing:
        print(f"[FAIL] 缺少必需列: {missing}")
        print(f"       实际表头: {list(rows[0].keys())}")
        print("       先跑 --template 拿标准表头")
        return 1

    parsed = [{c: row_value(row, colmap, c) for c in COL_ALIASES} for row in rows]
    ok, errs = validate(parsed)

    print(f"读到 {len(rows)} 行：合格 {len(ok)}，不合格 {len(errs)}")
    if errs:
        print("\n不合格明细：")
        for e in errs:
            print(e)
        print("\n[FAIL] 整批拒绝导入。")
        print("       名单必须真实且完整——半真半假的名单比没有名单更危险，")
        print("       发错人、发到无关公司会直接毁掉域名信誉和品牌。")
        return 1

    if a.dry_run:
        print("\n[DRY-RUN] 不写库。合格名单预览：")
        for r in ok[:10]:
            print(f"  {r['company']} | {r['site']} | {r['contact']} | "
                  f"{r['phone'] or r['email'] or r['wechat']}")
        if len(ok) > 10:
            print(f"  ... 共 {len(ok)} 家")
        return 0

    import db  # 延迟导入，dry-run 时不需要
    db.init()
    ins = dup = 0
    with db.conn() as c:
        for r in ok:
            exists = c.execute("SELECT id FROM leads WHERE company=? LIMIT 1",
                               (r["company"],)).fetchone()
            if exists:
                dup += 1
                continue
            c.execute("""INSERT OR IGNORE INTO leads
                (ts,company,industry,city,channel,contact,icp_score,tier,pain,angle,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (db.now(), r["company"], r["industry"] or "", r["city"] or "",
                 r["wechat"] or r["email"] or r["phone"] or "",
                 f"{r['contact']} / {r['phone']} {r['email']} {r['wechat']}".strip(),
                 90.0, "A", r["pain"] or "", f"来源: {r['source'] or '手工'}", "new_verified"))
            ins += 1
    db.log_run("lead.import_verified", f"imported={ins} dup={dup} src={a.csv.name}")

    print(f"\n[OK] 已入库 {ins} 家（跳过已存在 {dup} 家）")
    print("     status=new_verified，未进入任何自动发送队列。")
    print("     下一步：人工核验一遍再决定是否触达。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
