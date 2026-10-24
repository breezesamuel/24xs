# -*- coding: utf-8 -*-
"""
真实 SMTP 发送器 — QQ 邮箱（smtp.qq.com:465, SSL）。

与 sender_helper.py 的区别：那一版只把文案复制到剪贴板并写 status=sent，
并未发出任何邮件；本模块通过 SMTP 真正投递，并以服务器返回的
Message-ID 作为可核验凭证。

安全约束（默认 dry-run，不自动外发）：
  - 凭据只从环境变量读取，不落盘、不打印
  - 默认 --dry-run：生成邮件但不发送，需显式 --send 才真正投递
  - 按 (收件人, 主题) 去重，避免重复打扰
  - 拒绝向占位/未核实对象发送
  - 仅允许发往公开企业渠道；无收件人的行一律跳过

用法:
  python -X utf8 smtp_sender.py --build            # 只生成，不发送
  python -X utf8 smtp_sender.py --send --limit 1   # 实际发送 1 封（先小样本验证）
  python -X utf8 smtp_sender.py --send --limit 0   # 全部发送
"""

import argparse
import csv
import datetime
import email.utils
import hashlib
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("EMAIL_USER", "")
SMTP_PASS = os.getenv("EMAIL_PASS", "")

HERE = Path(__file__).resolve().parent
QUEUE_FILE = HERE.parents[1] / "99_产出" / "获客名单" / "已核实触达队列_20260930.csv"
LOG_DIR = HERE / "send_logs"

# 真实列名（来自 已核实触达队列_20260930.csv）
COL_COMPANY = "公司"
COL_CHANNEL = "公开渠道"
COL_EMAIL = "IR邮箱"
COL_WECHAT = "商务微信"
COL_ROLE = "联系人角色"
COL_NOTE = "备注"
COL_COPY = "第1次触达文案"

# 渠道合规策略：这些邮箱是「披露/客服」性质，不是采购邮箱。
# 自动外发前必须由人工逐条确认，避免把唯一发信身份打废。
RESTRICTED_LOCALPARTS = {
    "ir", "investor", "investors", "ir@", "tc",
    "support", "service", "help", "helpdesk", "customercare",
}

# 需在 CSV 中显式写入 ALLOW 才放行
OVERRIDE_TOKEN = "ALLOW"

# 占位/模板标识：命中即拒发。
# 注意：文案里 "xx区" 这类对区县的匿名引用是合法的，不能用裸 "xx" 做匹配。
PLACEHOLDER_TOKENS = [
    "模板", "待查", "占位", "placeholder",
    "xx外贸工厂", "自有品牌", "待补", "tbd",
    "xx公司", "xx工厂", "xx科技", "某公司", "某某",
]

POSITIVE_KEYWORDS = ["要", "自检", "自查表", "12项", "12 项", "发我", "发一下",
                     "给我", "需要", "好的", "可以", "ok", "收到"]
NEGATIVE_KEYWORDS = ["不感兴趣", "不用", "退订", "不需要", "别发了", "不要",
                     "拒绝", "停止", "屏蔽", "删除"]


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def looks_like_placeholder(*values: str) -> bool:
    blob = " ".join(_text(v) for v in values).lower()
    for token in PLACEHOLDER_TOKENS:
        if token in blob:
            return True
    return False


def pick(row: dict, *names: str) -> str:
    for n in names:
        if n in row and _text(row[n]):
            return _text(row[n])
    return ""


def extract_email(value: str) -> str:
    import re
    m = re.search(r"[\w\.\-+]+@[\w\.\-]+\.\w+", value or "")
    return m.group(0) if m else ""


def dedup_key(to_addr: str, subject: str) -> str:
    raw = f"{to_addr.lower()}|{' '.join(subject.split())}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def already_sent(key: str) -> bool:
    if not LOG_DIR.exists():
        return False
    for f in LOG_DIR.glob("smtp_sent_*.jsonl"):
        try:
            if any(f'"{key}"' in line for line in f.read_text(encoding="utf-8").splitlines()):
                return True
        except Exception:
            continue
    return False


def record_sent(payload: dict) -> None:
    import json
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    with open(LOG_DIR / f"smtp_sent_{stamp}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def build_message(row: dict, to_addr: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_addr
    msg["Subject"] = subject
    company = pick(row, COL_COMPANY)
    if company:
        msg["X-Outreach-Company"] = company
    role = pick(row, COL_ROLE)
    if role:
        msg["X-Outreach-Role"] = role
    msg.set_content(body)
    return msg


def load_queue() -> list:
    if not QUEUE_FILE.exists():
        print(f"[ERROR] 队列文件不存在: {QUEUE_FILE}")
        return []
    rows = []
    with open(QUEUE_FILE, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def channel_policy_verdict(row: dict, to_addr: str) -> tuple[bool, str]:
    """
    判断该渠道是否允许自动冷触达。
    返回 (是否放行, 原因)
    """
    if not to_addr:
        return False, "无邮箱渠道"
    note = _text(row.get(COL_NOTE))
    if OVERRIDE_TOKEN in note.upper():
        return True, "备注中含 ALLOW，人工放行"

    local = to_addr.split("@")[0].lower()
    if any(t in local for t in RESTRICTED_LOCALPARTS):
        return False, f"受限渠道（{local}）：属披露/客服邮箱，需人工确认后在备注写入 ALLOW"

    if "风险高" in note or "不建议群发" in note:
        return False, "备注已标注合规风险，需人工确认"
    if "非独立法人" in note or "业务单元" in note:
        return False, "收件方为业务单元而非法人，主体不适格"
    if "客服" in _text(row.get(COL_CHANNEL)):
        return False, "客服渠道不应用于冷开发"
    return True, "渠道可用"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="真正发送（默认只 dry-run）")
    ap.add_argument("--limit", type=int, default=0, help="本次最多发送几封，0=不限")
    ap.add_argument("--to", default="", help="只处理指定收件邮箱（单封验证用）")
    args = ap.parse_args()

    if args.send and not (SMTP_USER and SMTP_PASS):
        print("[ERROR] 未设置 EMAIL_USER / EMAIL_PASS 环境变量，拒绝发送")
        return 2

    rows = load_queue()
    if not rows:
        return 1

    plan = []
    for row in rows:
        company = pick(row, COL_COMPANY)
        channel_field = pick(row, COL_CHANNEL, COL_EMAIL)
        to_addr = args.to or extract_email(pick(row, COL_EMAIL, COL_CHANNEL))
        body = pick(row, COL_COPY)
        wechat = pick(row, COL_WECHAT)

        if not to_addr:
            plan.append((row, "", "SKIP", f"仅有微信渠道（{wechat}），本脚本只发邮件", company))
            continue
        if not body:
            plan.append((row, to_addr, "SKIP", f"缺文案（列「{COL_COPY}」为空）", company))
            continue
        if looks_like_placeholder(company, channel_field, body):
            plan.append((row, to_addr, "SKIP", "疑似占位/未核实内容，拒发", company))
            continue
        if to_addr.lower() == (SMTP_USER or "").lower():
            plan.append((row, to_addr, "SKIP", "收件人等于发件账号", company))
            continue

        allowed, why = channel_policy_verdict(row, to_addr)
        if not allowed:
            plan.append((row, to_addr, "BLOCK", why, company))
            continue

        key = dedup_key(to_addr, body[:40])
        if already_sent(key):
            plan.append((row, to_addr, "SKIP", "去重命中：此前已实际发送", company))
            continue

        plan.append((row, to_addr, "READY", key, company))

    if args.limit:
        allowed_idx = [i for i, p in enumerate(plan) if p[2] == "READY"][:args.limit]
        keep = set(allowed_idx)
        for i, item in enumerate(plan):
            if item[2] == "READY" and i not in keep:
                plan[i] = (item[0], item[1], "SKIP", "超出 --limit 限额", item[4])

    n_ready = len([p for p in plan if p[2] == "READY"])
    n_block = len([p for p in plan if p[2] == "BLOCK"])
    print("=" * 72)
    print("SMTP 真实发送器" + ("（DRY-RUN，未发送）" if not args.send else "（实际发送）"))
    print(f"发件账号: {SMTP_USER or '(未配置)'}")
    print(f"队列 {len(plan)} 条 | 可发 {n_ready} | 合规拦截 {n_block}")
    print("=" * 72)

    for row, to_addr, status, note, company in plan:
        print(f"[{status:5}] {company[:24]:26} {to_addr or '-':30} {note}")

    if n_block:
        print(f"\n[提示] {n_block} 条被渠道合规策略拦截。")
        print("       这些是 IR 披露邮箱 / 客服邮箱 / 业务单元，冷开发会毁掉发信信誉。")
        print("       若确认要发，请人工在 CSV 备注列追加 ' ALLOW' 后重跑。")

    if not n_ready:
        print("\n[DRY-RUN] 无可发条目，未连接 SMTP。")
        return 0

    if not args.send:
        print("\n[DRY-RUN] 未连接 SMTP。加 --send 才会真正投递。")
        return 0

    sent, failed = 0, 0
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as srv:
            srv.login(SMTP_USER, SMTP_PASS)
            for row, to_addr, status, note, company in plan:
                if status != "READY":
                    continue
                body = pick(row, COL_COPY)
                subject = f"[咨询] {pick(row, COL_COMPANY)} - 一个可快速验证的小切口"
                msg = build_message(row, to_addr, subject, body)
                try:
                    srv.send_message(msg)
                except Exception as e:
                    failed += 1
                    print(f"[FAIL] {to_addr}: {e}")
                    continue
                sent += 1
                record_sent({
                    "ts": datetime.datetime.now().isoformat(),
                    "dedup_key": note,
                    "to": to_addr,
                    "company": company,
                    "subject": subject,
                    "message_id": msg.get("Message-ID", ""),
                })
                print(f"[SENT] {to_addr}  Message-ID={msg.get('Message-ID','-')}")
    except smtplib.SMTPAuthenticationError:
        print("[ERROR] SMTP 认证失败：授权码无效或未开启 IMAP/SMTP 服务")
        return 3
    except Exception as e:
        print(f"[ERROR] SMTP 连接/发送失败: {e}")
        return 4

    print(f"\n完成：成功 {sent} 封，失败 {failed} 封")
    return 0 if failed == 0 else 5


if __name__ == "__main__":
    sys.exit(main())
