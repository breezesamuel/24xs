# -*- coding: utf-8 -*-
"""把邮箱地址写入 .eml 的 To 字段，仅限有公开邮箱的 prospects"""
from __future__ import annotations

import email
import email.policy
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

EML_DIR = Path(r"F:\2026\24xs\99_产出\外发草稿")

# 只有这些 prospects 有公开邮箱
EMAIL_MAP = {
    "外发_上海夕阳红口腔门_5105.eml": "xiyanghong@xyhkq.com.cn",
    "外发_上海汇尚口腔_1020.eml": "huishangkouqiang@163.com",
    "外发_格莱美婚礼宴会_5261.eml": "info@grammywedding.com",
    "外发_上海花嫁丽舍甜馨_2299.eml": "1033375049@qq.com",
    "外发_上海绚丽汇文化传播_5312.eml": "bigdata@netsun.com",
}

updated = 0
for fn, to_addr in EMAIL_MAP.items():
    fp = EML_DIR / fn
    if not fp.exists():
        print(f"[MISS] {fn}")
        continue
    raw = fp.read_bytes()
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    if msg.get("To"):
        print(f"[SKIP] {fn} 已有 To: {msg.get('To')}")
        continue
    del msg["To"]
    msg["To"] = to_addr
    fp.write_bytes(msg.as_bytes(policy=email.policy.default))
    print(f"[OK] {fn} -> To: {to_addr}")
    updated += 1

print(f"\n完成: 更新 {updated} 份")