# -*- coding: utf-8 -*-
"""
统一入口：python cli.py <命令>

命令一览：
  init                初始化数据库与目录
  corpus [--all]     生成内容资产（短内容卡/GEO语料/Schema/老板IP）
  geo audit <客户> <行业>    跑一次 GEO 可见度审计并出报告
  geo sheet <客户> <行业>   导出人工探测表（填完用 geo ingest 回填）
  geo ingest <csv> <客户> <行业>  回填真实探测数据
  leads               生成潜客池
  leads import <csv>  导入真实名单
  leads list <档位>    导出名单 CSV
  outreach <档位>     生成并导出触达队列
  money in <客户> <项目> <金额>   记一笔收入
  money out <项目> <金额>         记一笔支出
  money status        查看目标进度
  sim                 生成 1000 万路径测算
  dashboard           生成每日看板
  all                 一键全流程（推荐第一次跑这个）
  swarm intel         挖掘 Loot Drop 创业墓地重建机会
  swarm launch        执行单个 Page-Agent Worker 任务
  swarm capital       资本分配器状态/操作
  swarm run           启动 AI Worker Swarm 持续循环
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus_gen
import db
import finance
import funnel_sim
import geo_audit
import lead_engine
import outreach
import report
from config import INDUSTRIES


def _ind(name_or_key: str) -> str:
    for i in INDUSTRIES:
        if i["key"] == name_or_key or i["name"] == name_or_key:
            return i["key"]
    raise SystemExit(f"未知行业：{name_or_key}。可选：" + " / ".join(f"{i['key']}({i['name']})" for i in INDUSTRIES))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    rest = argv[1:]

    if cmd == "init":
        db.init()
        print("数据库就绪:", db.DB_PATH)
        return 0

    if cmd == "corpus":
        db.init()
        if rest and rest[0] != "--all":
            r = corpus_gen.build_industry(_ind(rest[0]))
            print(f"[{r['industry']}] 生成 {r['count']} 个文件")
            for k, v in r["files"].items():
                print(f"  - {k}: {v}")
        else:
            for r in corpus_gen.build_all():
                print(f"[{r['industry']}] 生成 {r['count']} 个文件")
        return 0

    if cmd == "geo":
        db.init()
        sub = rest[0] if rest else "audit"
        if sub == "audit":
            client = rest[1]
            key = _ind(rest[2])
            ind = next(i for i in INDUSTRIES if i["key"] == key)
            r = geo_audit.run_audit(client, ind["name"])
            m = r["metrics"]
            print(f"[{client} / {ind['name']}] 探测 {m.get('probes')} 次，"
                  f"提及率 {m.get('mention_rate')}，首选率 {m.get('top1_rate')}，动作 {r['actions']} 条")
            print("报告:", r["report"])
        elif sub == "sheet":
            print(geo_audit.export_probe_sheet(rest[1], next(i for i in INDUSTRIES if i["key"] == _ind(rest[2]))["name"]))
        elif sub == "ingest":
            n = geo_audit.ingest_csv(Path(rest[1]), rest[2],
                                     next(i for i in INDUSTRIES if i["key"] == _ind(rest[3]))["name"])
            print(f"回填 {n} 条")
        else:
            print("用法: geo audit|sheet|ingest ...")
        return 0

    if cmd == "leads":
        db.init()
        sub = rest[0] if rest else "build"
        if sub == "build":
            print(lead_engine.pipeline())
        elif sub == "import":
            print(f"导入 {lead_engine.import_csv(Path(rest[1]))} 条")
        elif sub == "list":
            print(lead_engine.export_list(rest[1] if len(rest) > 1 else "A"))
        else:
            print("用法: leads build|import|list")
        return 0

    if cmd == "outreach":
        db.init()
        tier = rest[0] if rest else "A"
        print(outreach.build_queue(tier))
        print(outreach.export_queue(tier))
        return 0

    if cmd == "money":
        db.init()
        sub = rest[0]
        if sub == "in":
            finance.income(rest[1], rest[2], float(rest[3]))
            print("已记账", rest[3])
        elif sub == "out":
            finance.expense(rest[1], float(rest[2]))
            print("已记账", rest[2])
        elif sub == "status":
            import json; print(json.dumps(finance.progress(), ensure_ascii=False, indent=2))
        print("看板:", report.render())
        return 0

    if cmd == "sim":
        db.init(); print(funnel_sim.write_report()); return 0

    if cmd == "dashboard":
        db.init(); print(report.render()); return 0

    if cmd == "all":
        db.init()
        print("== 1 内容资产 =="); corpus_gen.build_all()
        print("== 2 GEO 审计 ==")
        for i in INDUSTRIES[:2]:
            geo_audit.run_audit(f"示例客户{i['name']}", i["name"])
        print("== 3 潜客 =="); lead_engine.pipeline()
        print("== 4 触达 ==")
        for t in ("A", "B", "C"):
            outreach.build_queue(t, 40)
            outreach.export_queue(t)
        print("== 5 测算 =="); funnel_sim.write_report()
        print("== 6 看板 =="); print(report.render())
        return 0

    if cmd == "swarm":
        # 延迟导入避免循环依赖
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "08_军团"))
        from experiment_runner import main as swarm_main
        # 将 swarm 子命令转发给 experiment_runner
        swarm_argv = rest
        return swarm_main(swarm_argv)

    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
