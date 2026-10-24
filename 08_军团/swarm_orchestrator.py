# -*- coding: utf-8 -*-
"""
Swarm Orchestrator：AI 工人军团总调度。
完整闭环：
1. Loot Drop 挖掘机会 → 2. 资本分配器批准预算 → 3. Page-Agent Worker 执行实验
4. 结果评估 → 5. 盈利复投 / 亏损止损 → 6. 循环
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from intel.lootdrop_intel import LootDropIntel, RebuildOpportunity
from workers.page_agent_worker import PageAgentWorker, WorkerTask, TaskTemplates
from capital.capital_allocator import CapitalAllocator, AllocationBucket, ExperimentLedger

ORCHESTRATOR_DIR = Path(__file__).resolve().parent.parent / "08_军团"
EXPERIMENTS_DIR = ORCHESTRATOR_DIR / "experiments"
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class SwarmExperiment:
    id: str
    opportunity: RebuildOpportunity
    capital_exp_id: str
    status: str = "planning"  # planning, building, testing, launching, running, completed, failed
    worker_tasks: list[WorkerTask] = field(default_factory=list)
    results: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

class SwarmOrchestrator:
    def __init__(self, capital: CapitalAllocator):
        self.capital = capital
        self.intel = LootDropIntel()
        self.worker = PageAgentWorker()
        self.active_experiments: dict[str, SwarmExperiment] = {}
        self.max_parallel_experiments = 3
        self.max_parallel_workers = 3

    async def run_cycle(self, max_new_experiments: int = 2) -> dict:
        """单次军团循环：发现 → 筛选 → 启动 → 监控 → 结算。"""
        report = {
            "cycle_start": datetime.now().isoformat(),
            "new_experiments": [],
            "completed_experiments": [],
            "stop_loss_triggered": [],
            "capital_summary": self.capital.summary(),
        }

        # 1. 止损检查
        stop_loss_ids = self.capital.check_stop_losses()
        for exp_id in stop_loss_ids:
            self.capital.force_close(exp_id, "Auto stop-loss")
            report["stop_loss_triggered"].append(exp_id)

        # 2. 发现新机会
        if len([e for e in self.active_experiments.values() if e.status in ("building", "testing", "launching", "running")]) < self.max_parallel_experiments:
            opps = self.intel.find_rebuildable_gems(max_results=10)
            for opp in opps[:max_new_experiments]:
                if await self._launch_experiment(opp):
                    report["new_experiments"].append({"id": opp.startup.id, "name": opp.startup.name})

        # 3. 推进活跃实验
        for exp in list(self.active_experiments.values()):
            if exp.status in ("building", "testing", "launching", "running"):
                await self._advance_experiment(exp)
                if exp.status in ("completed", "failed"):
                    report["completed_experiments"].append({"id": exp.id, "status": exp.status, "roi": exp.results.get("roi")})

        report["cycle_end"] = datetime.now().isoformat()
        report["capital_summary"] = self.capital.summary()
        return report

    async def _launch_experiment(self, opp: RebuildOpportunity) -> bool:
        """为一个重建机会启动实验。"""
        exp_id = f"swarm_{opp.startup.id}_{uuid.uuid4().hex[:6]}"

        # 申请资本
        needed = Decimal(str(opp.capital_required_usd * 7.2))  # 粗略汇率
        if needed > Decimal("2000"):
            needed = Decimal("2000")  # 单次上限

        if not self.capital.can_allocate(AllocationBucket.EXPERIMENT_BUDGET, needed):
            return False

        self.capital.allocate(AllocationBucket.EXPERIMENT_BUDGET, exp_id, f"Rebuild: {opp.startup.name}", needed, f"Loot Drop: {opp.startup.name}")

        # 创建实验对象
        exp = SwarmExperiment(
            id=exp_id,
            opportunity=opp,
            capital_exp_id=exp_id,
            status="building",
        )

        # 规划 Worker 任务（根据重建方案自动生成）
        exp.worker_tasks = self._plan_worker_tasks(opp)
        self.active_experiments[exp_id] = exp
        return True

    def _plan_worker_tasks(self, opp: RebuildOpportunity) -> list[WorkerTask]:
        """根据重建方案自动生成 Worker 任务序列。"""
        tasks = []
        startup = opp.startup

        # 1. 市场验证：关键词趋势
        tasks.append(TaskTemplates.validate_market_keyword(f"{startup.sector} {startup.product_type}"))

        # 2. 竞品定价侦察（如果有竞品 URL）
        # 这里简化：假设重建方案里有竞品信息
        # tasks.append(TaskTemplates.scrape_competitor_pricing("https://competitor.com/pricing"))

        # 3. 落地页部署验证（用 page-agent 在 Vercel/Netlify 部署一个简单页面）
        # tasks.append(WorkerTask(...))

        # 4. 待办：根据 MVP 步骤生成更多任务
        for i, step in enumerate(opp.mvp_steps[:3]):
            tasks.append(WorkerTask(
                id=f"{opp.startup.id}_step{i}",
                name=f"MVP Step {i+1}: {step[:30]}",
                instruction=f"自动化执行: {step}。在浏览器中完成必要的注册/部署/配置操作，返回结果截图和关键信息。",
                target_url="https://vercel.com/new",  # 示例
                max_steps=30,
            ))

        return tasks

    async def _advance_experiment(self, exp: SwarmExperiment):
        """推进单个实验到下一阶段。"""
        if exp.status == "building":
            # 并发执行前 2 个 worker 任务（市场验证 + 竞品侦察）
            initial_tasks = exp.worker_tasks[:2]
            results = await self.worker.execute_batch(initial_tasks, concurrency=2)
            exp.results["initial_validation"] = [vars(r) for r in results]

            # 评估：如果市场验证通过，进入 testing
            if any(r.success for r in results):
                exp.status = "testing"
                self.capital.spend(exp.capital_exp_id, Decimal("200"), "初始验证通过，投入测试预算")
            else:
                exp.status = "failed"
                self.capital.close(exp.capital_exp_id, "初始验证失败")

        elif exp.status == "testing":
            # 执行 MVP 构建任务
            build_tasks = exp.worker_tasks[2:4]
            if build_tasks:
                results = await self.worker.execute_batch(build_tasks, concurrency=1)
                exp.results["mvp_build"] = [vars(r) for r in results]

                if any(r.success for r in results):
                    exp.status = "launching"
                    self.capital.spend(exp.capital_exp_id, Decimal("500"), "MVP 构建成功，投入发布预算")
                else:
                    exp.status = "failed"
                    self.capital.close(exp.capital_exp_id, "MVP 构建失败")

        elif exp.status == "launching":
            # 发布、获取首批用户/收入
            launch_tasks = exp.worker_tasks[4:6] if len(exp.worker_tasks) > 4 else []
            if launch_tasks:
                results = await self.worker.execute_batch(launch_tasks, concurrency=1)
                exp.results["launch"] = [vars(r) for r in results]

                # 简化：假设有收入就视为成功
                revenue = sum(r.output.get("revenue_usd", 0) for r in results if r.success and isinstance(r.output, dict))
                if revenue > 0:
                    cny_revenue = Decimal(str(revenue * 7.2))
                    self.capital.revenue(exp.capital_exp_id, cny_revenue, f"首批收入 ${revenue}")
                    exp.status = "running"
                else:
                    exp.status = "running"  # 先跑着，后续监控

        elif exp.status == "running":
            # 持续监控：每周检查一次收入
            # 这里简化：随机模拟或调用真实监控 API
            pass

    async def run_continuous(self, interval_minutes: int = 60, max_cycles: int = 0):
        """持续运行军团。"""
        cycle = 0
        while max_cycles == 0 or cycle < max_cycles:
            print(f"\n{'='*60}")
            print(f"[Swarm] Cycle {cycle+1} starting at {datetime.now().isoformat()}")
            report = await self.run_cycle()
            print(f"[Swarm] New: {len(report['new_experiments'])}, Completed: {len(report['completed_experiments'])}, StopLoss: {len(report['stop_loss_triggered'])}")
            print(f"[Swarm] Capital: Net PnL {report['capital_summary']['net_pnl_cny']} CNY, ROI {report['capital_summary']['roi_pct']}%")
            cycle += 1
            if max_cycles == 0 or cycle < max_cycles:
                await asyncio.sleep(interval_minutes * 60)

async def demo():
    """演示：跑一个完整循环。"""
    capital = CapitalAllocator()
    orchestrator = SwarmOrchestrator(capital)

    print("[*] 启动单次演示循环...")
    report = await orchestrator.run_cycle(max_new_experiments=1)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(demo())