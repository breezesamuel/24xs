# -*- coding: utf-8 -*-
"""
每日回复检查 + 免费样本自动交付。

流程：
1. 扫描 send_log_email_*.csv，找出 status="sent" 且最近 7 天内有回复（模拟：检查邮箱/微信）
   实际环境需对接真实邮箱 API；这里提供钩子函数 check_replies()
2. 对有回复的记录：
   a) 更新 status="replied"
   b) 生成免费样本 PDF（调用 day1_executor deliver-sample）
   c) 回复邮件附上 PDF 下载链接（模拟：记录到 sent_log）
3. 生成每日跟踪报告
"""
import csv
import datetime
import os
import subprocess
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "send_logs"
SENT_LOG = LOG_DIR / f"send_log_email_{datetime.date.today().isoformat().replace('-', '')}.csv"
REPLY_LOG = LOG_DIR / f"reply_tracking_{datetime.date.today().isoformat().replace('-', '')}.csv"


def load_sent_log():
    if not SENT_LOG.exists():
        return []
    with open(SENT_LOG, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def check_replies(company: str, email: str) -> bool:
    """
    检查是否有回复。
    真实环境：对接 Gmail/Outlook API、企业微信 API、IMAP 等。
    这里返回 False（需人工对接）。
    """
    # TODO: 接入真实邮箱/微信检查
    return False


def deliver_free_sample(company: str, email: str) -> str:
    """调用 day1_executor deliver-sample 生成 PDF，返回产出目录"""
    try:
        root = Path(__file__).resolve().parents[2]
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(root / "tools" / "day1_executor.py"), "deliver-sample"],
            cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        if proc.returncode == 0:
            # 找最新生成的 samples 目录
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
    rows = load_sent_log()
    if not rows:
        print("无发送记录")
        return

    print(f"检查 {len(rows)} 条发送记录...")
    replied = 0
    for row in rows:
        if row.get("status") != "sent":
            continue
        company = row.get("公司", "")
        email = row.get("IR邮箱") or row.get("邮箱") or row.get("联系人(角色)", "")
        if not email or "@" not in email:
            continue

        if check_replies(company, email):
            print(f"[回复] {company} ({email})")
            # 更新原日志
            row["status"] = "replied"
            replied += 1
            # 交付免费样本
            result = deliver_free_sample(company, email)
            print(f"  样本交付: {result}")
            # 记录回复跟踪
            with open(REPLY_LOG, "a", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                if f.tell() == 0:
                    w.writerow(["date", "company", "email", "reply_detected", "sample_delivered", "note"])
                w.writerow([datetime.date.today().isoformat(), company, email, "yes", result, ""])
        else:
            # 记录无回复
            with open(REPLY_LOG, "a", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                if f.tell() == 0:
                    w.writerow(["date", "company", "email", "reply_detected", "sample_delivered", "note"])
                w.writerow([datetime.date.today().isoformat(), company, email, "no", "", ""])

    print(f"完成：{replied} 条有回复，已触发样本交付")


if __name__ == "__main__":
    main()