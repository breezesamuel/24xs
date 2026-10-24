# -*- coding: utf-8 -*-
"""
把「已核实触达文案」按公司名匹配进「已核实真实主体」CSV，
生成带有「第1次触达文案」列的触达队列，供 sender_helper 使用。
"""
import csv
import os

LEADS_CSV = r"F:\2026\24xs\99_产出\获客名单\已核实真实主体_20260930.csv"
COPY_TXT = r"F:\2026\24xs\99_产出\获客名单\已核实触达文案_20260930.txt"
OUT_CSV = r"F:\2026\24xs\99_产出\获客名单\已核实触达队列_20260930.csv"

# 从文案文本里提取每家的文案
def parse_copy(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()
    # 格式：分隔符 + 公司名 + 分隔符 + 文案 + 分隔符 + 下一家公司名...
    parts = text.split("============================================================")
    copy_map = {}
    # parts[0] 是空的（开头就是分隔符），之后是 [公司名, 文案, 公司名, 文案...]
    for i in range(1, len(parts) - 1, 2):
        company = parts[i].strip().split("\n")[0].strip()
        copy = parts[i + 1].strip()
        if company and copy:
            copy_map[company] = copy
    return copy_map


def main():
    copy_map = parse_copy(COPY_TXT)
    print(f"解析到 {len(copy_map)} 家文案")
    for k in copy_map:
        print(f"  - {k}")

    # 读取真实主体 CSV
    with open(LEADS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 字段名映射（CSV 里的列名 -> 触达需要的列名）
    # 关键：给每行加上「第1次触达文案」
    for row in rows:
        company = row["公司"]
        if company in copy_map:
            row["第1次触达文案"] = copy_map[company]
            print(f"[OK] {company} 匹配上文案 ({len(copy_map[company])} 字符)")
        else:
            row["第1次触达文案"] = ""
            print(f"[WARN] {company} 未匹配到文案")

    # 写出新 CSV
    fieldnames = list(rows[0].keys())
    # 确保「第1次触达文案」在最后
    if "第1次触达文案" in fieldnames:
        fieldnames.remove("第1次触达文案")
    fieldnames.append("第1次触达文案")

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"已生成: {OUT_CSV} ({len(rows)} 行)")


if __name__ == "__main__":
    main()