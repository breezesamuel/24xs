# -*- coding: utf-8 -*-
"""
Experiment Runner：单次实验的完整执行入口。
用法：
  python -m 08_军团.experiment_runner intel          # 挖掘机会
  python -m 08_军团.experiment_runner capital status  # 资本状态
  python -m 08_军团.experiment_runner launch --template keyword --param "AI coding"
  python -m 08_军团.experiment_runner swarm --interval 60
  python -m 08_军团.experiment_runner first_money     # 首单实验：14天内跑通 GEO 诊断首单回款
"""
import argparse
import asyncio
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intel.lootdrop_intel import LootDropIntel, save_opportunities
from capital.capital_allocator import CapitalAllocator, AllocationBucket
from swarm_orchestrator import SwarmOrchestrator

INTEL_DIR = Path(__file__).resolve().parent / "intel"

def cmd_intel(args):
    """挖掘 Loot Drop 重建机会。"""
    intel = LootDropIntel()
    print("[*] 诊断 MCP 连接...")
    diag = intel.diagnose()
    print(f"    {diag}")

    print("[*] 挖掘可重建项目...")
    opps = intel.find_rebuildable_gems(max_results=args.max)

    out_path = INTEL_DIR / args.output
    save_opportunities(opps, out_path)
    print(f"[+] 发现 {len(opps)} 个高价值重建机会，已保存到 {out_path}")
    for i, o in enumerate(opps[:10], 1):
        # market_potential_score 在 RebuildOpportunity 里没有直接存，从 startup.rebuild_plan 取
        score = "N/A"
        if hasattr(o.startup, 'rebuild_plan') and o.startup.rebuild_plan:
            score = o.startup.rebuild_plan.get('market_potential_score', 'N/A')
        print(f"  {i}. {o.startup.name} ({o.startup.sector}) - 市场潜力 {score} - 需资金 ${o.capital_required_usd:,.0f} - MVP {o.time_to_mvp_weeks}周")

def cmd_capital(args):
    """资本分配器状态/操作。"""
    cap = CapitalAllocator()
    if args.action == "status":
        print(json.dumps(cap.summary(), ensure_ascii=False, indent=2, default=str))
    elif args.action == "allocate":
        ok = cap.allocate(AllocationBucket[args.bucket.upper()], args.exp_id, args.name, Decimal(str(args.amount)), args.notes)
        print(f"[+] 分配 {'成功' if ok else '失败'}: {args.exp_id}")
    elif args.action == "spend":
        ok = cap.spend(args.exp_id, Decimal(str(args.amount)), args.notes)
        print(f"[+] 花费 {'成功' if ok else '失败'}: {args.exp_id} - {args.amount}")
    elif args.action == "revenue":
        ok = cap.revenue(args.exp_id, Decimal(str(args.amount)), args.notes)
        print(f"[+] 收入 {'成功' if ok else '失败'}: {args.exp_id} - {args.amount}")
    elif args.action == "reply":
        # 记录回复/约会（通过实验账本查找）
        print(f"[!] reply 动作暂通过手工记录，后续完善")
    elif args.action == "deal":
        print(f"[!] deal 动作暂通过手工记录，后续完善")
    elif args.action == "close":
        ok = cap.close(args.exp_id, args.notes)
        print(f"[+] 关闭 {'成功' if ok else '失败'}: {args.exp_id}")
    elif args.action == "stoploss":
        ids = cap.check_stop_losses()
        print(f"[!] 触发止损: {ids}")
        for eid in ids:
            cap.force_close(eid)

def cmd_launch(args):
    """启动单个实验（简化版：直接跑 worker 任务）。"""
    from workers.page_agent_worker import PageAgentWorker, TaskTemplates, WorkerTask

    async def run():
        worker = PageAgentWorker()
        if args.template == "keyword":
            task = TaskTemplates.validate_market_keyword(args.param, args.region)
        elif args.template == "pricing":
            task = TaskTemplates.scrape_competitor_pricing(args.param)
        elif args.template == "social":
            task = TaskTemplates.post_to_social(args.platform, args.param, args.account)
        elif args.template == "waitlist":
            task = TaskTemplates.signup_waitlist(args.param, args.email)
        elif args.template == "affiliate":
            task = TaskTemplates.extract_affiliate_links(args.param, args.keyword)
        else:
            task = WorkerTask(
                id=args.exp_id or uuid.uuid4().hex[:8],
                name=args.name or "Custom Task",
                instruction=args.instruction,
                target_url=args.url,
                model=args.model,
            )

        print(f"[*] Executing: {task.name}")
        result = await worker.execute(task)
        print(json.dumps(vars(result), ensure_ascii=False, indent=2, default=str))

    asyncio.run(run())

def cmd_swarm(args):
    """启动军团持续循环。"""
    capital = CapitalAllocator()
    orchestrator = SwarmOrchestrator(capital)
    print(f"[*] Starting swarm: interval={args.interval}min, max_cycles={args.cycles or '∞'}")
    asyncio.run(orchestrator.run_continuous(interval_minutes=args.interval, max_cycles=args.cycles))

def cmd_first_money(args):
    """首单实验：14天内跑通 GEO 诊断首单回款。"""
    from experiments.first_money_exp import FirstMoneyRunner
    runner = FirstMoneyRunner(dry_run=getattr(args, "dry_run", False))
    # 旧版忽略这些参数，直接写死 2000/50/14。现在真正传进去。
    exp = runner.run(
        budget_cny=Decimal(str(args.budget)),
        target_leads=args.target_leads,
        days=args.days,
    )
    print(f"\n[✅ 首单实验 {exp.id} 准备就绪]")
    print(f"  线索: {len(exp.leads)} 家 (A档: {sum(1 for l in exp.leads if l.tier=='A')})")
    print(f"  已花费: {exp.spent_cny} 元 | 剩余: {exp.budget_cny - exp.spent_cny} 元")
    print(f"  触达队列: 99_产出/获客名单/触达队列_A档_*.csv")
    print(f"\n[下一步] 请人工执行触达：")
    print(f"  1. 打开 CSV: 99_产出/获客名单/触达队列_A档_*.csv")
    print(f"  2. 按每行的 3 段文案发私信/邮件/电话")
    print(f"  3. 记录回复 -> 约会 -> 成交")
    print(f"  4. 回款后记账: python cli.py swarm capital revenue --exp-id {exp.id} --amount <金额>")

def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="AI Worker Swarm Experiment Runner")
    sub = parser.add_subparsers(dest="command", required=True)

    # intel
    p_intel = sub.add_parser("intel", help="挖掘 Loot Drop 重建机会")
    p_intel.add_argument("--max", type=int, default=20)
    p_intel.add_argument("--output", default="rebuild_opportunities.json")

    # capital
    p_cap = sub.add_parser("capital", help="资本分配器")
    p_cap.add_argument("action", choices=["status", "allocate", "spend", "revenue", "reply", "deal", "close", "stoploss"])
    p_cap.add_argument("--bucket", choices=[b.value for b in AllocationBucket])
    p_cap.add_argument("--exp-id")
    p_cap.add_argument("--name")
    p_cap.add_argument("--amount", type=float)
    p_cap.add_argument("--notes", default="")

    # launch
    p_launch = sub.add_parser("launch", help="执行单个 Worker 任务")
    p_launch.add_argument("--template", choices=["keyword", "pricing", "social", "waitlist", "affiliate", "custom"], default="custom")
    p_launch.add_argument("--instruction")
    p_launch.add_argument("--url", default="https://example.com")
    p_launch.add_argument("--model", default="qwen3.5-plus")
    p_launch.add_argument("--param", help="template 参数（关键词/URL/内容等）")
    p_launch.add_argument("--region", default="US")
    p_launch.add_argument("--platform", default="twitter")
    p_launch.add_argument("--account", default="")
    p_launch.add_argument("--email", default="test@example.com")
    p_launch.add_argument("--keyword", default="")
    p_launch.add_argument("--exp-id")
    p_launch.add_argument("--name")

    # swarm
    p_swarm = sub.add_parser("swarm", help="启动持续军团循环")
    p_swarm.add_argument("--interval", type=int, default=60, help="循环间隔分钟")
    p_swarm.add_argument("--cycles", type=int, default=0, help="最大循环数，0=无限")

    # first_money
    p_fm = sub.add_parser("first_money", help="首单实验：14天内跑通 GEO 诊断首单回款")
    p_fm.add_argument("--budget", type=int, default=2000, help="预算上限(元)")
    p_fm.add_argument("--target-leads", type=int, default=50, help="目标线索数")
    p_fm.add_argument("--days", type=int, default=14, help="截止天数")
    p_fm.add_argument("--dry-run", action="store_true", help="只跑流程，不动资金账本、不写 leads 表")

    args = parser.parse_args(argv)

    if args.command == "intel":
        cmd_intel(args)
    elif args.command == "capital":
        cmd_capital(args)
    elif args.command == "launch":
        cmd_launch(args)
    elif args.command == "swarm":
        cmd_swarm(args)
    elif args.command == "first_money":
        cmd_first_money(args)

if __name__ == "__main__":
    main()