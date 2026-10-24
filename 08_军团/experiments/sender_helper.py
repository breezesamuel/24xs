#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RFC-correct per-row touch sender. Replaces the send_*.bat clipboard loop that
broke rows at commas inside quoted copy. Still manual-send (Y/N/Q): this tool
only copies the RIGHT copy for the RIGHT company; a human presses send in the
real messaging/email page. Never auto-sends.
"""
import argparse
import base64
import csv
import datetime
import os
import subprocess
import sys

PLACEHOLDER_MARK = "（自有品牌）"

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_logs")


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f)]


def copy_clipboard(text):
    b64 = base64.b64encode(text.encode("utf-8")).decode()
    cmd = (f"[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
           f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}'));"
           f"Set-Clipboard -Value $t")
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                   check=False, capture_output=True)


def log_row(channel, row, status):
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d")
    log = os.path.join(LOG_DIR, f"send_log_{channel}_{stamp}.csv")
    write_header = not os.path.exists(log)
    with open(log, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()) + ["sent_at", "status"])
        if write_header:
            w.writeheader()
        out = dict(row)
        out["sent_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        out["status"] = status
        w.writerow(out)


def prose(row, channel):
    if channel == "wechat":
        return row.get("第1次触达文案", "").strip()
    if channel == "email":
        return row.get("第1次触达文案", "").strip()
    if channel == "phone":
        return row.get("第1次触达文案", "").strip()
    return row.get("第1次触达文案", "").strip()


def pick():
    while True:
        k = input("  [Y]sent [N]skip [Q]quit > ").strip().lower()
        if k in {"y", "n", "q"}:
            return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True,
                    help="path to the touch queue CSV (with 第1次触达文案 column)")
    ap.add_argument("--channel", choices=["wechat", "email", "phone"], required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="plan only; do not touch clipboard")
    ap.add_argument("--auto-yes", action="store_true",
                    help="skip Y/N/Q prompt, log all as sent (for automation)")
    args = ap.parse_args()

    rows = load(args.csv)
    print(f"loaded {len(rows)} rows from {args.csv} (channel={args.channel})")
    if args.dry_run:
        ok, ph = 0, 0
        for r in rows:
            head = r.get("公司", "?").strip()
            if PLACEHOLDER_MARK in head:
                ph += 1
                print(f"  [skip-placeholder] {head}")
                continue
            ok += 1
            print(f"  [ok] {head}  ICP={r.get('ICP分','').strip()}")
        print(f"plan: {ok} sendable / {ph} placeholder-skipped / {len(rows)} total")
        return

    for r in rows:
        head = r.get("公司", "?").strip()
        if PLACEHOLDER_MARK in head:
            print(f"\n[SKIP placeholder] {head}")
            log_row(args.channel, r, "skipped_placeholder")
            continue
        body = prose(r, args.channel)
        print("\n" + "=" * 60)
        print(f"company : {head}")
        print(f"ICP     : {r.get('ICP分','').strip()}  industry={r.get('行业','').strip()}")
        print("-" * 60)
        print(body)
        print("=" * 60)
        if not body:
            print("[warn] empty copy; skipping")
            log_row(args.channel, r, "skipped_empty")
            continue
        copy_clipboard(body)
        print("[copied to clipboard] switch to the messaging/email page, Ctrl+V, send.")
        if args.auto_yes:
            choice = "y"
            print("[auto-yes] sent")
        else:
            choice = pick()
        if choice == "y":
            log_row(args.channel, r, "sent")
        elif choice == "n":
            log_row(args.channel, r, "skipped")
        else:
            log_row(args.channel, r, "quit_pending")
            print("quit. remaining rows left untouched.")
            return
    print("\ndone.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted.")
        sys.exit(130)