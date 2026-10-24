# -*- coding: utf-8 -*-
"""
QQ 邮箱 IMAP 回复轮询器。

功能：
- 用 IMAP 登录 QQ 邮箱（需开启 IMAP 服务并用授权码）
- 轮询收件箱，找出对已发送触达邮件的回复
- 关键词匹配：包含「要」「自检」「自查表」「12 项」「不感兴趣」「不用」「退订」等
- 更新 send_log 状态，触发免费样本交付

配置：通过环境变量传入，不写死在代码里
  EMAIL_USER=460123249@qq.com
  EMAIL_PASS=vcibttgugksebhgc
  IMAP_HOST=imap.qq.com
  IMAP_PORT=993
"""
import os
import imaplib
import email
import re
import csv
import datetime
import sys
from pathlib import Path
from email.header import decode_header

# ====== 配置（从环境变量读取，绝不硬编码）======
EMAIL_USER = os.getenv("EMAIL_USER", "460123249@qq.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")  # 必须通过环境变量传入
IMAP_HOST = os.getenv("IMAP_HOST", "imap.qq.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

# 回复判定关键词
POSITIVE_KEYWORDS = ["要", "自检", "自查表", "12 项", "12项", "发我", "发一下", "给我", "需要", "ok", "OK", "好的", "可以"]
NEGATIVE_KEYWORDS = ["不感兴趣", "不用", "退订", "不需要", "别发了", "不要", "拒绝", "停止", "屏蔽"]

LOG_DIR = Path(__file__).resolve().parent / "send_logs"
SENT_LOG_PATTERN = "send_log_email_*.csv"
REPLY_LOG = LOG_DIR / f"reply_tracking_{datetime.date.today().isoformat().replace('-', '')}.csv"


def decode_mime_header(value):
    """解码邮件头中的 MIME 编码（兼容未知编码）"""
    if not value:
        return ""
    # 可能是 Header 对象，转为字符串
    if hasattr(value, "__str__") and not isinstance(value, str):
        value = str(value)
    try:
        parts = decode_header(value)
    except Exception:
        return str(value)
    decoded = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            try:
                decoded += part.decode(enc or "utf-8", errors="replace")
            except LookupError:
                # 未知编码（如 unknown-8bit），尝试常见编码
                for fallback in ("utf-8", "gbk", "gb2312", "latin-1"):
                    try:
                        decoded += part.decode(fallback, errors="replace")
                        break
                    except Exception:
                        continue
                else:
                    decoded += part.decode("utf-8", errors="replace")
        else:
            decoded += part
    return decoded


def extract_email_addr(from_header):
    """从 From 头提取纯邮箱地址（兼容 Header 对象）"""
    if from_header is None:
        return ""
    # 可能是 Header 对象，转为字符串
    if hasattr(from_header, "__str__"):
        from_header = str(from_header)
    elif not isinstance(from_header, str):
        from_header = str(from_header)
    match = re.search(r"[\w\.-]+@[\w\.-]+", from_header)
    return match.group(0).lower() if match else ""


def is_reply_to_our_email(msg, sent_emails: set) -> tuple[bool, str]:
    """
    判断是否是对我们发送邮件的回复。
    返回 (是否回复, 匹配到的原发件邮箱)
    """
    # 检查 In-Reply-To / References 头
    in_reply_to = msg.get("In-Reply-To", "")
    references = msg.get("References", "")
    for ref in (in_reply_to, references):
        if ref:
            ref_str = str(ref)
            for sent in sent_emails:
                if sent in ref_str:
                    return True, sent

    # 检查 Subject 是否包含 Re: 且发件人在我们的发送列表中
    subject = decode_mime_header(msg.get("Subject", ""))
    from_addr = extract_email_addr(msg.get("From", ""))
    if from_addr in sent_emails and subject.lower().startswith("re:"):
        return True, from_addr

    return False, ""


def classify_reply(body: str) -> str:
    """根据正文内容分类回复类型"""
    body_lower = body.lower()
    for kw in POSITIVE_KEYWORDS:
        if kw in body_lower:
            return "positive"
    for kw in NEGATIVE_KEYWORDS:
        if kw in body_lower:
            return "negative"
    return "neutral"


def get_email_body(msg) -> str:
    """提取邮件正文（优先 text/plain）"""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    continue
    else:
        try:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            pass
    return ""


def load_sent_emails() -> set:
    """从 send_log 加载我们发送过的目标邮箱集合"""
    sent = set()
    for log_file in LOG_DIR.glob(SENT_LOG_PATTERN):
        try:
            with open(log_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("status") == "sent":
                        # 优先用 IR邮箱，其次邮箱列，最后联系人列
                        email_addr = row.get("IR邮箱") or row.get("邮箱") or row.get("联系人(角色)", "")
                        # 提取邮箱地址
                        match = re.search(r"[\w\.-]+@[\w\.-]+", email_addr)
                        if match:
                            sent.add(match.group(0).lower())
        except Exception as e:
            print(f"[WARN] 读取 {log_file} 失败: {e}")
    return sent


def update_sent_log_status(target_email: str, new_status: str):
    """更新 send_log 中对应邮箱的状态"""
    for log_file in LOG_DIR.glob(SENT_LOG_PATTERN):
        try:
            rows = []
            with open(log_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                rows = list(reader)
            changed = False
            for row in rows:
                row_email = row.get("IR邮箱") or row.get("邮箱") or row.get("联系人(角色)", "")
                if extract_email_addr(row_email).lower() == target_email.lower():
                    row["status"] = new_status
                    changed = True
            if changed:
                with open(log_file, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            print(f"[WARN] 更新 {log_file} 失败: {e}")


def log_reply_tracking(company: str, email: str, reply_type: str, subject: str, body_snippet: str):
    """记录回复跟踪日志"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not REPLY_LOG.exists()
    with open(REPLY_LOG, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["date", "company", "email", "reply_type", "subject", "body_snippet"])
        writer.writerow([
            datetime.datetime.now().isoformat(),
            company, email, reply_type, subject, body_snippet[:200]
        ])


def trigger_sample_delivery(company: str, email: str) -> str:
    """触发免费样本交付（调用 day1_executor deliver-sample）"""
    try:
        root = Path(__file__).resolve().parents[2]
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "tools" / "day1_executor.py"), "deliver-sample"],
            cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        if proc.returncode == 0:
            samples_dirs = sorted((root / "samples").glob("*")) if (root / "samples").exists() else []
            if samples_dirs:
                latest = samples_dirs[-1]
                pdfs = list(latest.glob("*.pdf"))
                if pdfs:
                    return f"PDF已生成: {pdfs[0].name}"
        return f"生成失败: {proc.stderr[-200:] if proc.stderr else '未知错误'}"
    except Exception as e:
        return f"异常: {e}"


def main():
    if not EMAIL_PASS:
        print("[ERROR] EMAIL_PASS 环境变量未设置")
        return 1

    print(f"[INFO] 连接 {IMAP_HOST}:{IMAP_PORT} as {EMAIL_USER}")
    sent_emails = load_sent_emails()
    print(f"[INFO] 已加载 {len(sent_emails)} 个已发送目标邮箱")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")

        # 搜索最近 3 天的未读邮件（减少处理量）
        since_date = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%d-%b-%Y")
        typ, data = mail.search(None, f'(SINCE "{since_date}" UNSEEN)')
        if typ != "OK":
            print("[ERROR] 搜索失败")
            return 1

        mail_ids = data[0].split()
        print(f"[INFO] 发现 {len(mail_ids)} 封未读邮件待检查")

        # 限制最多处理 100 封，避免超时
        mail_ids = mail_ids[-100:]
        replied_count = 0
        for num in mail_ids:
            typ, msg_data = mail.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            is_reply, matched_email = is_reply_to_our_email(msg, sent_emails)
            if not is_reply:
                continue

            # 解析邮件
            from_addr = extract_email_addr(msg.get("From", ""))
            subject = decode_mime_header(msg.get("Subject", ""))
            body = get_email_body(msg)
            reply_type = classify_reply(body)

            print(f"[REPLY] From: {from_addr} | Subject: {subject} | Type: {reply_type}")

            # 更新发送日志状态
            if reply_type == "positive":
                update_sent_log_status(matched_email, "replied_positive")
                log_reply_tracking("", matched_email, "positive", subject, body[:200])
                # 触发样本交付
                result = trigger_sample_delivery("", matched_email)
                print(f"  -> 触发样本交付: {result}")
            elif reply_type == "negative":
                update_sent_log_status(matched_email, "replied_negative")
                log_reply_tracking("", matched_email, "negative", subject, body[:200])
            else:
                update_sent_log_status(matched_email, "replied_neutral")
                log_reply_tracking("", matched_email, "neutral", subject, body[:200])

            replied_count += 1

        mail.close()
        mail.logout()
        print(f"[DONE] 本次检查到 {replied_count} 条回复")
        return 0

    except imaplib.IMAP4.error as e:
        print(f"[ERROR] IMAP 认证/连接失败: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] 未预期错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import subprocess
    sys.exit(main())