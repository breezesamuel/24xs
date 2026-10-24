# -*- coding: utf-8 -*-
"""
广度优先生产采集器 —— 唯一采购人最大化。
实测教训：医院类单个大词重复度极高（8.9:1）。
所以调度不追深度，追「宽度」：大量关键词 x 8种类型 x 3年 x 31省，
每个查询组合去重后新增采购人越多，越优先跑。这是提升唯一率的关键。
"""
import io
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import crawler24 as C  # noqa

PROV = [("110000", "北京"), ("120000", "天津"), ("130000", "河北"),
        ("140000", "山西"), ("150000", "内蒙古"), ("210000", "辽宁"),
        ("220000", "吉林"), ("230000", "黑龙江"), ("310000", "上海"),
        ("320000", "江苏"), ("330000", "浙江"), ("340000", "安徽"),
        ("350000", "福建"), ("360000", "江西"), ("370000", "山东"),
        ("410000", "河南"), ("420000", "湖北"), ("430000", "湖南"),
        ("440000", "广东"), ("450000", "广西"), ("460000", "海南"),
        ("500000", "重庆"), ("510000", "四川"), ("520000", "贵州"),
        ("530000", "云南"), ("540000", "西藏"), ("610000", "陕西"),
        ("620000", "甘肃"), ("630000", "青海"), ("640000", "宁夏"),
        ("650000", "新疆")]

# 超宽关键词池：细分到具体采购标的，覆盖不同采购人群体
WIDE_KW = [
    "医院", "学校", "大学", "学院", "软件", "电梯", "物业", "食堂", "绿化",
    "保洁", "监控", "消防", "装修", "审计", "印刷", "车辆", "家具", "空调",
    "锅炉", "供水", "供电", "网络", "机房", "服务器", "系统集成", "测绘",
    "设计", "施工", "监理", "检测", "评估", "咨询", "培训", "广告", "办公用品",
    "药品", "耗材", "试剂", "设备", "仪器", "安保", "门禁", "停车场", "垃圾",
    "档案", "财务", "机房建设", "视频会议", "安防", "窗帘", "床品", "制服",
    "劳保", "展板", "显示屏", "会议服务", "差旅", "维修", "轮胎", "油料",
    "水处理", "维保", "特种设备", "管线", "管道", "桥梁", "道路", "工程",
    "苗木", "花卉", "石材", "瓷砖", "涂料", "卫浴", "灯具", "厨房", "洗涤",
    "劳务", "外包", "信息系统", "大数据", "云计算", "运维", "等级保护",
    "网站", "宣传片", "翻译", "法律", "财税", "银行", "保险", "拍卖",
    "认证", "建筑", "景观", "食堂托管", "洗涤服务", "安保服务",
    "软件开发", "系统开发", "平台建设", "数据中心", "云服务", "短信",
    "气象", "地震", "水利", "电力", "燃气", "供热", "污水", "固废",
    "环境监测", "检测服务", "运维工程", "修缮", "维修改造", "加固",
    "校园", "教室", "宿舍", "食堂", "实验室", "实训", "教研", "招生",
    "医疗设备", "医用设备", "信息化", "智慧城市", "大数据中心",
    "工会", "党建", "宣传", "文明", "卫生", "防疫", "疾控", "养老",
    "殡葬", "救助", "残疾人", "妇女", "青少年", "社区", "街道", "乡镇",
    "税务", "财政", "审计服务", "绩效评价", "咨询费", "律师", "公证",
    "印刷品", "档案数字化", "政务云", "信创", "国产化",
]
TYPES = [("bidx", "公开招标"), ("yixb", "邀请招标"), ("jztp", "竞争性谈判"),
         ("jzcs", "竞争性磋商"), ("xunjia", "询价"), ("dyly", "单一来源"),
         ("zbj", "中标结果"), ("cjj", "成交结果")]
YEARS = (2024, 2025, 2026)

DB = os.path.join(C.BASE, "ccgp_production.db")


def build_queries(c):
    """读已完成的 grid，生成待跑查询列表。"""
    done = set()
    for kw, db, yr, z in c.execute(
            "SELECT kw,dbselect,yr,zone FROM grid WHERE done=1"):
        done.add((kw, db, yr, z or ""))
    qs = []
    for y in YEARS:
        for db, _ in TYPES:
            for kw in WIDE_KW:
                for z, pn in PROV:
                    if (kw, db, y, z) not in done:
                        qs.append((kw, db, y, z, pn))
    return qs


def main():
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 3000.0
    c = C.init_db()
    seen = set(x[0] for x in c.execute("SELECT url FROM notices"))
    notices0 = c.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    buyers0 = c.execute("SELECT COUNT(*) FROM buyers").fetchone()[0]
    print("启动：已存 %d 公告 / %d 采购人；待跑查询 %s"
          % (len(seen), buyers0, "见日志"), flush=True)
    qs = build_queries(c)
    random.shuffle(qs) if False else None
    t_end = time.time() + budget
    new_buyer_total = 0
    q_done = 0

    logpath = os.path.join(C.BASE, "_prod_crawl.log")

    def log(s):
        print(s, flush=True)
        with io.open(logpath, "a", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%H:%M:%S ") + s + "\n")

    for kw, db, yr, z, pn in qs:
        if time.time() > t_end:
            break
        u = C.search_url(1, kw, db, yr, zone=z)
        try:
            html = C.get(u, tries=2)
            items = C.parse_list(html)
        except Exception:
            continue
        got_here = 0
        for title, url in items:
            if url in seen:
                continue
            if time.time() > t_end:
                break
            try:
                d = C.parse_detail(C.get(url, tries=2), url)
            except Exception:
                continue
            d["title"] = title
            d["province"] = pn
            seen.add(url)
            C.save(c, d, kw, db)
            got_here += 1
            time.sleep(0.28)
        q_done += 1
        c.execute("INSERT OR REPLACE INTO grid VALUES (?,?,?,1,?,1,?,datetime('now'))",
                  (kw, db, yr, z, got_here))
        c.commit()
        if got_here:
            time.sleep(1.1)
        if q_done % 20 == 0:
            nb = c.execute("SELECT COUNT(*) FROM buyers").fetchone()[0]
            nn = c.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
            new_buyer_total = nb - buyers0
            log("进度 查询=%d 公告=%d 采购人=%d(新+%d) 延迟=%.1f"
                % (q_done, nn, nb, new_buyer_total, C.TH.d))

    nn = c.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    nb = c.execute("SELECT COUNT(*) FROM buyers").fetchone()[0]
    elapsed = round(budget - (t_end - time.time()), 1)
    log("【本轮结束】查询=%d 公告=%d 采购人=%d(本轮新+%d) 耗时%ss"
        % (q_done, nn, nb, nb - buyers0, elapsed))
    summary = {
        "本轮查询数": q_done,
        "库内公告总数": nn,
        "库内采购人总数": nb,
        "本轮新增采购人": nb - buyers0,
        "本轮耗时秒": elapsed,
        "本轮新公告": nn - notices0,
        "秒每新公告": round(elapsed / max(nn - notices0, 1), 2),
    }
    with io.open(os.path.join(C.BASE, "_prod_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    c.close()


if __name__ == "__main__":
    main()
