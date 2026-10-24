# -*- coding: utf-8 -*-
"""订阅后台（本机运行）—— 把申请变成可用的额度。

流程：
  1. 线上 /api/order 收到申请，写进函数日志
  2. `vercel logs` 把申请捞出来，`orders import` 落库
  3. 你在支付宝核对到账，`orders confirm <编号>` 标记已付款
  4. `users activate <邮箱> <套餐>` 开通，发放额度
  5. 额度余量、推荐进度都落库；站点只读展示

为什么确认到账这一步不能省
--------------------------
收款是支付宝转账，系统看不到钱进来。把"提交申请"当成"已付款"，
就等于免费送额度；等钱到了再补确认，中间几天会被反复薅。
所以 confirm 必须由人来做，而且要记确认人和时间。

为什么额度要落在本机而不是站点
------------------------------
Vercel 函数无状态，重启即丢。要让额度活过重启就得引入外部数据库，
那是另一个需要计费和配额的依赖。眼下量级（人工确认）撑得住本机 SQLite，
先把商业闭环跑通；量起来了再迁。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"F:\2026\24xs")
eng = next(ROOT.glob("01_*"))
sys.path.insert(0, str(eng))
sys.stdout.reconfigure(encoding="utf-8")

import subscription as S  # noqa: E402

DB = ROOT / "99_产出" / "_data" / "subscription.sqlite3"
# 注意：字段值可能为空（比如没填推荐码），所以用 \S* 而不是 \S+。
# 用 \S+ 时 `ref= site=` 这种空值会把后面的字段整体错位，
# 结果是整行匹配不上，申请被静默漏掉 —— 少一条订单就少一次发货。
ORDER_RE = re.compile(r"\[ORDER\]\s+id=(\S+)\s+plan=(\S+)\s+lang=(\S+)\s+"
                      r"ref=(\S*)\s+site=(\S*)\s+email=(\S+)")


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def conn() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id   TEXT PRIMARY KEY,
            email      TEXT NOT NULL,
            plan       TEXT NOT NULL,
            lang       TEXT DEFAULT 'cn',
            ref_code   TEXT DEFAULT '',
            site       TEXT DEFAULT '',
            status     TEXT NOT NULL DEFAULT 'pending_payment',
            amount     REAL,
            created_at TEXT,
            confirmed_at TEXT,
            confirmed_by TEXT,
            -- fulfilled：钱已收且额度/报告已交付。分开于 status，
            -- 因为"收到钱"和"开通成功"是两个会各自失败的动作。
            -- 只看 status='paid' 会在开通崩溃后永久吞掉未交付的订单。
            fulfilled  INTEGER NOT NULL DEFAULT 0,
            note       TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            email        TEXT PRIMARY KEY,
            plan         TEXT,
            uses_total   INTEGER NOT NULL DEFAULT 0,
            uses_left    INTEGER NOT NULL DEFAULT 0,
            ref_code     TEXT UNIQUE,
            referred_by  TEXT,
            activated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS referral_payments (
            email        TEXT NOT NULL,
            paid_months  INTEGER NOT NULL,
            amount       REAL,
            currency     TEXT,
            PRIMARY KEY (email)
        );
        CREATE TABLE IF NOT EXISTS referral_awards (
            email     TEXT NOT NULL,
            tier_invites INTEGER NOT NULL,
            months    INTEGER NOT NULL,
            awarded_at TEXT NOT NULL,
            PRIMARY KEY (email, tier_invites)
        );
    """)
    # 迁移：老库没有 fulfilled/note。CREATE TABLE IF NOT EXISTS 不会补列，
    # 缺列会让后面所有 SELECT/UPDATE 报 no such column。
    have = {r[1] for r in c.execute("PRAGMA table_info(orders)")}
    for col, ddl in (("fulfilled", "INTEGER NOT NULL DEFAULT 0"),
                     ("note", "TEXT")):
        if col not in have:
            c.execute(f"ALTER TABLE orders ADD COLUMN {col} {ddl}")
    c.commit()
    return c


# ------------------------------------------------------------------ 申请
ALIPAY_ORDER_RE = re.compile(r"\[ALIPAY-ORDER\]\s+no=(\S+)\s+plan=(\S+)\s+"
                             r"cents=(\d+)\s+lang=(\S+)\s+ref=(\S*)\s+"
                             r"email=(\S+)")
ALIPAY_PAID_RE = re.compile(r"\[ALIPAY-PAID\]\s+no=(\S+)")


def import_alipay(paths: list[Path]) -> int:
    """从 Vercel 日志导入支付宝订单 + 已付款记录，然后给已付款的开通额度。

    只有同时出现 [ALIPAY-ORDER]（谁买的买什么）和 [ALIPAY-PAID]
    （该单经支付宝查询确认已到账）的订单才会开通。
    """
    c = conn()
    orders: dict[str, dict] = {}
    paid: list[str] = []
    for p in paths:
        if not p.exists():
            print(f"  [跳过] 找不到 {p}")
            continue
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = ALIPAY_ORDER_RE.search(ln)
            if m:
                no, plan, cents, lang, ref, email = m.groups()
                orders[no] = {"plan": plan, "cents": int(cents), "lang": lang,
                              "ref": "" if ref == "-" else ref, "email": email}
                continue
            m = ALIPAY_PAID_RE.search(ln)
            if m:
                paid.append(m.group(1))

    # 所有下单记录先落 pending_payment —— 绝不能因为"日志里有这一行"
    # 就当成已付款。之前就是在这里直接写 'paid'，结果只付 0.01 被支付宝
    # 拒付的订单在台账里也显示为 paid，看起来像真客户。
    for no, o in orders.items():
        c.execute(
            "INSERT OR IGNORE INTO orders "
            "(order_id,email,plan,lang,ref_code,site,status,created_at,amount) "
            "VALUES (?,?,?,?,?,?, 'pending_payment', ?, ?)",
            (no, o["email"], o["plan"], o["lang"], o["ref"], "alipay", now(),
             o["cents"] / 100))
    c.commit()
    print(f"  订单 {len(orders)} 条，其中支付宝确认到账 {len(set(paid))} 条")

    n = 0
    # 第一步：只把"支付宝确认到账"的单标成 paid。收到钱是事实，不能因为
    # 后面开通失败就丢掉这次到账记录。
    for no in dict.fromkeys(paid):
        if no not in orders:
            print(f"  [跳过] {no} 已到账但找不到下单记录，无法确定买给谁")
            continue
        c.execute(
            "UPDATE orders SET status='paid', confirmed_at=?, confirmed_by='alipay' "
            "WHERE order_id=? AND status<>'paid'",
            (now(), no))
    c.commit()

    # 第二步：交付清单从库里读，不从内存列表推。这样上次开通崩溃留下的
    # 半成品单（paid 但未交付）这次会被捡起来重试 —— 靠 fulfilled 判重，
    # 不靠 status，避免"已付款"把未交付的单永久跳过。
    todo = list(c.execute(
        "SELECT * FROM orders WHERE status='paid' AND fulfilled=0 "
        "ORDER BY confirmed_at"))

    for o in todo:
        no = o["order_id"]
        # 一次性报告不占额度，不能走 activate()（它按月套餐查 PLANS，
        # 传 report 会 KeyError）。只标记已交付，由人工发报告。
        if o["plan"] in S.ONE_OFF:
            _fulfill_oneoff(c, no, o)
            continue
        try:
            activate(o["email"], o["plan"], "alipay-notify", o["ref_code"])
        except Exception as e:
            # activate 失败绝不能把 fulfilled 置 1，否则下次重试会被跳过，
            # 钱收了额度却永远不开。保持未交付，等下次导入日志重试。
            print(f"  [失败] {no} {o['email']} 开通出错：{e}")
            print("        该单保持未交付，重新导入日志即可重试开通。")
            continue
        c.execute("UPDATE orders SET fulfilled=1 WHERE order_id=?", (no,))
        c.commit()
        n += 1
    print(f"  本次开通 {n} 个账号")
    return n


def _fulfill_oneoff(c, no: str, o) -> None:
    """一次性报告单：记录交付，不动额度。o 是 orders 表的行。"""
    label = S.ONE_OFF[o["plan"]]["label"]
    c.execute("UPDATE orders SET fulfilled=1, note=? WHERE order_id=?",
              (f"一次性报告 {label}，人工发送", no))
    c.commit()
    amt = o["amount"]
    print(f"  [报告单] {no} {o['email']} {o['plan']} "
          f"{amt:g}元 → 标记已交付，请人工发送报告")


def import_log(paths: list[Path]) -> int:
    """从 vercel logs 文本里解析 [ORDER] 行落库。已存在的忽略。

    解析失败必须报错而不是安静跳过 —— 之前用 \\S+ 匹配空值时整行匹配不上，
    两条申请只导进一条，日志里看不出任何异常，订单就这么丢了。
    """
    c = conn()
    n = 0
    raw_hits = 0
    unmatched: list[str] = []
    for p in paths:
        if not p.exists():
            print(f"  [跳过] 找不到 {p}")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = [ln for ln in text.splitlines() if "[ORDER]" in ln]
        raw_hits += len(lines)
        got = 0
        for ln in lines:
            m = ORDER_RE.search(ln)
            if not m:
                unmatched.append(ln.strip()[:120])
                continue
            got += 1
            oid, plan, lang, ref, site, email = m.groups()
            cur = c.execute(
                "INSERT OR IGNORE INTO orders "
                "(order_id,email,plan,lang,ref_code,site,status,created_at) "
                "VALUES (?,?,?,?,?,?, 'pending_payment', ?)",
                (oid, email, plan, lang,
                 "" if ref == "-" else ref, "" if site == "-" else site, now()))
            n += cur.rowcount
        if got != len(lines):
            print(f"  [注意] {p.name}: {len(lines)} 行里只解析出 {got} 行")
    c.commit()
    print(f"  日志中申请 {raw_hits} 条，新导入 {n} 条"
          f"（已存在的不重复计）")
    if unmatched:
        print(f"  [失败] 有 {len(unmatched)} 行无法解析，这些订单会被漏掉：")
        for u in unmatched[:5]:
            print(f"       {u}")
        return -1
    return n


def list_orders(status: str | None) -> None:
    c = conn()
    sql = "SELECT * FROM orders"
    args: tuple = ()
    if status:
        sql += " WHERE status=?"
        args = (status,)
    sql += " ORDER BY created_at DESC"
    rows = c.execute(sql, args).fetchall()
    if not rows:
        print("  （没有记录）")
        return
    print(f"  {'订单编号':<22} {'邮箱':<26} {'套餐':<8} {'金额':>8}  状态")
    print("  " + "-" * 84)
    for r in rows:
        amt = f"{r['amount']:g}" if r["amount"] else "-"
        print(f"  {r['order_id']:<22} {r['email']:<26} {r['plan']:<8} {amt:>8}  "
              f"{r['status']}")


def confirm(order_id: str, who: str) -> None:
    """人工核对到账后标记已付款。"""
    c = conn()
    row = c.execute("SELECT * FROM orders WHERE order_id=?",
                    (order_id,)).fetchone()
    if not row:
        print(f"  [失败] 找不到订单 {order_id}")
        return
    if row["status"] == "confirmed":
        print(f"  已确认过，不重复记账：{order_id}")
        return
    plan = row["plan"]
    lang = row["lang"] or "cn"
    price = S.plan_price(lang, plan)
    c.execute("UPDATE orders SET status='confirmed', amount=?, "
              "confirmed_at=?, confirmed_by=? WHERE order_id=?",
              (price, now(), who, order_id))
    c.commit()
    print(f"  已确认 {order_id}  金额 {S.plan_symbol(lang)}{price:g}  确认人 {who}")


# ------------------------------------------------------------------ 用户
def _ref_code(email: str) -> str:
    import hashlib
    h = hashlib.sha256(email.lower().encode()).hexdigest()[:6].upper()
    return "GEO" + h


def _resolve_ref(c: sqlite3.Connection, code: str) -> str | None:
    """把推荐码换成邀请人的邮箱。

    referred_by 里存邮箱，不存推荐码。存推荐码的话后面算奖励时
    `WHERE email=<推荐码>` 会一行都匹配不上，奖励记成"已发放"却没真发出去，
    而且因为已记录就再也不会补发 —— 这种错最难查。
    """
    code = code.strip()
    if not code:
        return None
    row = c.execute("SELECT email FROM users WHERE ref_code=?",
                    (code,)).fetchone()
    if row is None:
        print(f"  [注意] 推荐码 {code} 不存在，按无推荐人处理")
        return None
    return row["email"]


def activate(email: str, plan: str, who: str, ref: str = "") -> None:
    """开通订阅并发放额度；同时记录本次付费供推荐奖励判定。"""
    c = conn()
    email = email.strip().lower()
    uses = S.plan_uses(plan)
    months = S.PLANS["cn"]["plans"][plan]["months"]
    price_cny = S.plan_price("cn", plan)

    row = c.execute("SELECT email FROM users WHERE email=?", (email,)).fetchone()
    if row is None:
        # 两个码不能混：
        #   ref_code     = 这个账号**自己**的推荐码（别人拿它来推荐自己）
        #   referred_by  = 邀请人的**邮箱**（他的奖励发给这个人）
        inviter = _resolve_ref(c, ref)
        c.execute("INSERT INTO users (email,plan,ref_code,referred_by,"
                  "activated_at) VALUES (?,?,?,?,?)",
                  (email, plan, _ref_code(email), inviter, now()))
    # 同一人换更贵的套餐时，只补差价对应的增量，不叠加
    old = c.execute("SELECT uses_total, uses_left FROM users WHERE email=?",
                    (email,)).fetchone()
    add = max(0, uses - (old["uses_total"] if old else 0))
    c.execute("UPDATE users SET plan=?, uses_total=uses_total+?, "
              "uses_left=uses_left+? WHERE email=?",
              (plan, add, add, email))
    c.execute("INSERT OR REPLACE INTO referral_payments "
              "(email,paid_months,amount,currency) VALUES (?,?,?,?)",
              (email, months, price_cny, "CNY"))
    c.commit()
    print(f"  已开通 {email}  套餐 {plan}  新增额度 {add} 次  "
          f"推荐码 {_ref_code(email)}")
    _recompute_referrals(c, email)


def add_free(email: str, n: int, who: str) -> None:
    c = conn()
    email = email.strip().lower()
    row = c.execute("SELECT uses_left, ref_code FROM users WHERE email=?",
                    (email,)).fetchone()
    if row is None:
        # 每个账号都必须有推荐码，否则这个人没法推荐别人，
        # 而推荐码是唯一的 —— 少了它推荐奖励整条链就断了。
        c.execute("INSERT INTO users (email,uses_total,uses_left,ref_code,"
                  "activated_at) VALUES (?,?,?,?,?)",
                  (email, n, n, _ref_code(email), now()))
        print(f"  新建 {email}  赠送 {n} 次  推荐码 {_ref_code(email)}")
    else:
        c.execute("UPDATE users SET uses_left=uses_left+? WHERE email=?",
                  (n, email))
        print(f"  {email} 增加 {n} 次，剩余 {row['uses_left'] + n}")
    c.commit()


def consume(email: str, n: int = 1) -> None:
    c = conn()
    row = c.execute("SELECT uses_left FROM users WHERE email=?",
                    (email,)).fetchone()
    if row is None:
        print("  [拒绝] 未知用户")
        return
    if row["uses_left"] < n:
        print(f"  [拒绝] 额度不足：剩余 {row['uses_left']}，需要 {n}")
        return
    c.execute("UPDATE users SET uses_left=uses_left-? WHERE email=?",
              (n, email))
    c.commit()
    print(f"  已扣 {n} 次，剩余 {row['uses_left'] - n}")


# ------------------------------------------------------------- 推荐奖励
def _recompute_referrals(c: sqlite3.Connection, invitee: str) -> None:
    """按被邀请人的实付档位，重算其邀请人的奖励。"""
    user = c.execute("SELECT email,referred_by FROM users WHERE email=?",
                     (invitee,)).fetchone()
    if not user or not user["referred_by"]:
        return
    inviter = user["referred_by"]
    pays = [dict(r) for r in c.execute(
        "SELECT p.paid_months,p.amount,p.currency FROM referral_payments p "
        "JOIN users u ON u.email=p.email WHERE u.referred_by=?",
        (inviter,)).fetchall()]
    prog = S.referral_progress(pays)
    given = {r["tier_invites"]
             for r in c.execute(
                 "SELECT tier_invites FROM referral_awards WHERE email=?",
                 (inviter,)).fetchall()}
    added = 0
    for t in prog["achieved"]:
        if t["invites"] in given:
            continue
        uses = S.uses_for_months(t["reward_months"])
        # 必须先看 UPDATE 真的改到了行，再记"已发放"。
        # 顺序反过来会出这种事故：推荐人不存在 -> 更新 0 行 -> 照样记成已发放
        # -> 额度没发出去，但这笔被标记为已完成，再也不会补发。
        cur = c.execute(
            "UPDATE users SET uses_total=uses_total+?, uses_left=uses_left+? "
            "WHERE email=?", (uses, uses, inviter))
        if cur.rowcount == 0:
            print(f"  [失败] 推荐人 {inviter} 不在库中，"
                  f"{t['reward_zh']} 未发放（不记为已完成）")
            continue
        c.execute("INSERT INTO referral_awards (email,tier_invites,months,"
                  "awarded_at) VALUES (?,?,?,?)",
                  (inviter, t["invites"], t["reward_months"], now()))
        added += uses
    if added:
        c.commit()
        print(f"  推荐奖励：{inviter} +{added} 次额度")


def referral(email: str) -> None:
    c = conn()
    u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not u:
        print("  未知用户")
        return
    pays = [dict(r) for r in c.execute(
        "SELECT p.paid_months,p.amount,p.currency FROM referral_payments p "
        "JOIN users u2 ON u2.email=p.email WHERE u2.referred_by=?",
        (email,)).fetchall()]
    prog = S.referral_progress(pays)
    print(f"  推荐码 {u['ref_code']}   已邀请 {len(pays)} 人   "
          f"额度剩余 {u['uses_left']}")
    for t in prog["achieved"]:
        print(f"    [已达成] {t['title_zh']} -> {t['reward_zh']}")
    if prog["next"]:
        n = prog["next"]
        short_people = [p for p in pays
                        if p["paid_months"] < n["min_paid_months"]]
        need_invites = max(0, n["invites"] - len(pays))
        need_paid = len(short_people)
        if need_invites and need_paid:
            why = (f"还差 {need_invites} 位邀请人，"
                   f"且其中 {need_paid} 位需升级到 {n['min_paid_months']} 个月以上")
        elif need_invites:
            why = f"还需邀请 {need_invites} 人"
        elif need_paid:
            why = (f"人数已够，但有 {need_paid} 位被邀请人实付不足 "
                   f"{n['min_paid_months']} 个月")
        else:
            why = "已达标"
        print(f"    [下一档] {why} -> {n['reward_zh']}")


def export_state(path: Path) -> None:
    """导出只读额度快照，供站点展示。只含额度，不含邮箱。"""
    c = conn()
    rows = c.execute("SELECT ref_code, uses_left, uses_total FROM users").fetchall()
    data = {
        "generated_at": now(),
        "free_uses": S.FREE_USES,
        "active_codes": [
            {"ref_code": r["ref_code"], "uses_left": r["uses_left"]}
            for r in rows if r["uses_left"] > 0
        ],
        "orders_pending": c.execute(
            "SELECT COUNT(*) FROM orders WHERE status='pending_payment'"
        ).fetchone()[0],
        "orders_confirmed": c.execute(
            "SELECT COUNT(*) FROM orders WHERE status='confirmed'"
        ).fetchone()[0],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    print(f"  已导出 {path}  "
          f"(待付款 {data['orders_pending']} / 已确认 {data['orders_confirmed']})")


def main() -> int:
    ap = argparse.ArgumentParser(description="订阅后台")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("import", help="从 vercel logs 导入申请")
    p.add_argument("paths", nargs="+")

    p = sub.add_parser("import-alipay", help="导入支付宝订单并开通已付款账号")
    p.add_argument("paths", nargs="+")

    p = sub.add_parser("orders", help="列出申请")
    p.add_argument("--status", default=None,
                   choices=["pending_payment", "confirmed"])

    p = sub.add_parser("confirm", help="人工确认到账")
    p.add_argument("order_id")
    p.add_argument("--by", default=os.environ.get("USERNAME", "operator"))

    p = sub.add_parser("activate", help="开通订阅并发放额度")
    p.add_argument("email")
    p.add_argument("plan", choices=list(S.PLANS["cn"]["plans"]))
    p.add_argument("--by", default="operator")
    p.add_argument("--ref", default="")

    p = sub.add_parser("free", help="赠送额度")
    p.add_argument("email")
    p.add_argument("n", type=int)
    p.add_argument("--by", default="operator")

    p = sub.add_parser("consume", help="扣减额度")
    p.add_argument("email")
    p.add_argument("n", type=int, nargs="?", default=1)

    p = sub.add_parser("referral", help="查推荐进度")
    p.add_argument("email")

    p = sub.add_parser("export", help="导出只读额度快照")
    # 不能落在 10_官网\api\ 里：那个目录会被 vercel deploy 整棵发布到公网，
    # 快照里的推荐码和剩余额度就变成任何人可读。
    p.add_argument("--out", default=str(
        ROOT / "99_产出" / "_data" / "sub_state.json"))

    a = ap.parse_args()
    if a.cmd == "import-alipay":
        import_alipay([Path(x) for x in a.paths])
    elif a.cmd == "import":
        import_log([Path(x) for x in a.paths])
    elif a.cmd == "orders":
        list_orders(a.status)
    elif a.cmd == "confirm":
        confirm(a.order_id, a.by)
    elif a.cmd == "activate":
        activate(a.email, a.plan, a.by, a.ref)
    elif a.cmd == "free":
        add_free(a.email, a.n, a.by)
    elif a.cmd == "consume":
        consume(a.email, a.n)
    elif a.cmd == "referral":
        referral(a.email)
    elif a.cmd == "export":
        export_state(Path(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
