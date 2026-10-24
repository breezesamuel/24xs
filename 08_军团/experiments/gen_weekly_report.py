# -*- coding: utf-8 -*-
"""
周报生成器：汇总本周触达、回复、样本交付、成交情况。

输出：data/reports/weekly_YYYY-WW.md
"""
import csv
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "data" / "logs"
REPORT_DIR = ROOT / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def load_log(path: Path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    week_str = monday.isocalendar()[:2]  # (year, week)
    week_label = f"{week_str[0]}-W{week_str[1]:02d}"

    sent_logs = list(LOG_DIR.glob("send_log_email_*.csv"))
    reply_logs = list(LOG_DIR.glob("reply_tracking_*.csv"))

    sent_rows = []
    for p in sent_logs:
        sent_rows.extend(load_log(p))

    reply_rows = []
    for p in reply_logs:
        reply_rows.extend(load_log(p))

    # 过滤本周
    def in_this_week(row, date_key):
        try:
            d = datetime.datetime.strptime(row.get(date_key, ""), "%Y-%m-%d %H:%M:%S").date()
            return d >= monday and d <= monday + datetime.timedelta(days=6)
        except Exception:
            return False

    sent_this_week = [r for r in sent_rows if in_this_week(r, "sent_at")]
    replied_this_week = [r for r in reply_rows if in_this_week(r, "date") and r.get("reply_detected") == "yes"]

    # 统计
    total_sent = len(sent_this_week)
    total_replied = len(replied_this_week)
    reply_rate = f"{total_replied/total_sent*100:.1f}%" if total_sent else "0%"

    # 生成报告
    lines = [
        f"# 周报 {week_label} ({monday} ~ {monday + datetime.timedelta(days=6)})",
        "",
        "## 核心指标",
        f"- 本周触达: **{total_sent}** 家",
        f"- 本周回复: **{total_replied}** 家",
        f"- 回复率: **{reply_rate}**",
        "",
        "## 触达明细",
    ]
    for r in sent_this_week:
        lines.append(f"- {r.get('公司', '')} | {r.get('channel', '')} | {r.get('sent_at', '')} | {r.get('status', '')}")

    lines += ["", "## 回复与样本交付"]
    for r in replied_this_week:
        lines.append(f"- {r.get('company', '')} | 样本: {r.get('sample_delivered', '')}")

    lines += ["", "## 下周行动"]
    lines.append("- 对未回复名单发送第 2 次触达（间隔 7 天）")
    lines.append("- 对回复名单跟进报价/签约")
    lines.append("- 生成下周内容 + 更新 sitemap")

    out = REPORT_DIR / f"weekly_{week_label}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"周报已生成: {out}")


if __name__ == "__main__":
    main()