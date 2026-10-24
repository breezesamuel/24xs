# -*- coding: utf-8 -*-
"""
First Money Experiment (Pure Factory Engine)：首单 GEO 诊断回款实验。
仅使用工厂引擎（01_引擎）能力：
1. 离线生成 50 家高仿真 A 段线索
2. 工厂引擎生成个性化 GEO 诊断报告样例
3. 工厂引擎生成触达队列（私信/邮件/电话三板斧）
4. 导出 CSV 供人工执行触达
预算：2000 元（从 EXPERIMENT 桶）
目标：14 天内 ≥ 1 单 GEO 诊断回款（8k-30k）
"""
import asyncio
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

from capital.capital_allocator import CapitalAllocator, AllocationBucket
from workers.offline_lead_gen import generate_real_leads, RealLead, save_leads

EXP_DIR = Path(__file__).resolve().parent
EXP_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class TouchRecord:
    lead_id: str
    company: str
    channel: str
    template_used: str
    sent_at: str
    replied: bool = False
    replied_at: Optional[str] = None
    meeting_booked: bool = False
    deal_stage: str = "sent"
    revenue_cny: Decimal = Decimal("0")

@dataclass
class FirstMoneyExperiment:
    id: str
    name: str = "First Money: GEO Audit First Sale (Pure Factory)"
    budget_cny: Decimal = Decimal("2000")
    spent_cny: Decimal = Decimal("0")
    revenue_cny: Decimal = Decimal("0")
    target_leads: int = 50
    target_revenue_cny: Decimal = Decimal("8000")
    deadline_days: int = 14
    status: str = "planning"
    leads: list[RealLead] = field(default_factory=list)
    touches: list[TouchRecord] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    deadline_at: str = field(default_factory=lambda: (datetime.now() + timedelta(days=14)).isoformat())
    closed_at: Optional[str] = None

    def days_left(self) -> int:
        return max(0, (datetime.fromisoformat(self.deadline_at) - datetime.now()).days)

    def roi(self) -> float:
        if self.spent_cny == 0:
            return 0.0
        return float((self.revenue_cny - self.spent_cny) / self.spent_cny * 100)

class FirstMoneyRunner:
    # 阶段成本基准（单实验上限 2000）。dry_run 或预算下探时按比例缩减，
    # 不再像旧版那样无视 --budget 直接写死 200/300/500。
    COST_LEADGEN = Decimal("200")
    COST_GEO_REPORTS = Decimal("300")
    COST_OUTREACH = Decimal("500")
    BUDGET_CEILING = Decimal("2000")

    def __init__(self, dry_run: bool = False):
        # dry_run: 不动资金账本、不写 leads 表、不导出触达队列。
        # 用于在名单未核验前验证流程，避免污染资金与数据库。
        self.dry_run = dry_run
        self.capital = CapitalAllocator()
        self.exp: Optional[FirstMoneyExperiment] = None
        # 已记过回款的公司，用于 record_deal 幂等
        self._dealt: set[str] = set()

    def run(
        self,
        budget_cny: Decimal = Decimal("2000"),
        target_leads: int = 50,
        days: int = 14,
    ) -> FirstMoneyExperiment:
        """同步执行一次首单实验（单日模式）"""
        budget_cny = Decimal(str(budget_cny))
        target_leads = int(target_leads)
        days = int(days)

        for name, val in (("budget_cny", budget_cny), ("target_leads", target_leads), ("days", days)):
            if val <= 0:
                raise ValueError(f"{name} 必须 > 0，收到 {val}")
        if budget_cny > self.BUDGET_CEILING:
            raise ValueError(f"单实验预算上限 {self.BUDGET_CEILING} 元，收到 {budget_cny}")

        # 按预算比例缩放三个阶段成本，避免预算下探时仍超支
        ratio = budget_cny / self.BUDGET_CEILING
        self.cost_leadgen = (self.COST_LEADGEN * ratio).quantize(Decimal("1"))
        self.cost_geo = (self.COST_GEO_REPORTS * ratio).quantize(Decimal("1"))
        self.cost_outreach = (self.COST_OUTREACH * ratio).quantize(Decimal("1"))

        self.exp = FirstMoneyExperiment(
            id=f"fm_{uuid.uuid4().hex[:8]}",
            budget_cny=budget_cny,
            target_leads=target_leads,
            deadline_days=days,
            deadline_at=(datetime.now() + timedelta(days=days)).isoformat(),
        )
        print(f"[=== First Money Experiment {self.exp.id} ===]")
        print(f"预算: {self.exp.budget_cny} 元 | 目标线索: {target_leads} | 期限: {days} 天"
              f"{'  [DRY-RUN: 不动资金/不写库]' if self.dry_run else ''}")
        print(f"阶段成本(按预算缩放): 名单 {self.cost_leadgen} + 报告 {self.cost_geo}"
              f" + 触达 {self.cost_outreach}")

        # 1. 申请预算
        if self.dry_run:
            print("[预算] DRY-RUN：跳过资金预留")
        elif not self.capital.allocate(AllocationBucket.EXPERIMENT_BUDGET, self.exp.id, self.exp.name, self.exp.budget_cny, "首单 GEO 诊断实验（纯工厂引擎）"):
            raise RuntimeError(f"预算不足：需要 {self.exp.budget_cny} 元")
        self.exp.status = "lead_gen"

        # 2. 生成真实线索
        self._generate_leads()

        # 3. 导入工厂引擎数据库 + 生成触达队列
        self._factory_pipeline()

        # 4. 记账（实验保持 open，等真实回款后才结项）
        self._finalize()

        return self.exp

    def _generate_leads(self):
        """生成高仿真线索（5 行业 × N 家），数量由 target_leads 决定。"""
        print(f"[LeadGen] 生成线索 (目标 {self.exp.target_leads} 家)...")
        # 每行业生成 target_leads 的余量，避免总数不足
        per_industry = max(1, (self.exp.target_leads + 4) // 5)
        leads = generate_real_leads(target_per_industry=per_industry)
        self.exp.leads = leads[:self.exp.target_leads]
        if len(self.exp.leads) < self.exp.target_leads:
            print(f"[WARN] 仅生成 {len(self.exp.leads)}/{self.exp.target_leads} 家线索，"
                  f"未达目标数（线索源已耗尽，属正常）")

        # 保存线索
        leads_file = EXP_DIR / f"{self.exp.id}_leads.json"
        save_leads(self.exp.leads, leads_file.name)
        print(f"[+] 生成 {len(self.exp.leads)} 家线索，已保存: {leads_file}")

        # 记账
        if not self.dry_run:
            self.capital.spend(self.exp.id, self.cost_leadgen, "离线线索生成")
        self.exp.spent_cny += self.cost_leadgen
        self.exp.status = "factory_pipeline"

    def _factory_pipeline(self):
        """跑工厂引擎完整流程：入库 → 诊断 → 触达队列导出。"""
        print("[Factory] 启动工厂引擎流程...")

        # 动态导入工厂引擎模块
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "01_引擎"))
        import db
        import lead_engine
        import outreach
        from config import INDUSTRIES

        db.init()

        # 2.1 入库（幂等：同公司已存在则跳过，避免重复运行累积重复记录）
        inserted = skipped = 0
        for lead in self.exp.leads:
            # 映射行业 key
            ind_key = next((i["key"] for i in INDUSTRIES if i["name"] in lead.industry or lead.industry in i["name"]), "home_improvement")
            if self.dry_run:
                skipped += 1
                continue
            try:
                # 已存在同公司则跳过（run_all / 重跑都不会翻倍）
                existing = db.conn().execute(
                    "SELECT id FROM leads WHERE company = ? LIMIT 1", (lead.company,)
                ).fetchone()
                if existing:
                    skipped += 1
                    continue
                db.q("""
                    INSERT INTO leads(company, industry, city, contact, channel, pain, angle, tier, icp_score, status)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (lead.company, lead.industry, lead.city, lead.contact,
                      lead.channel, lead.pain, "GEO 诊断", lead.tier, lead.icp_score, "new"))
                inserted += 1
            except Exception as e:
                print(f"  [WARN] 入库失败 {lead.company}: {e}")

        print(f"[+] 入库 {inserted} 条（跳过已存在/DRY-RUN {skipped} 条）")

        # 2.2 生成 GEO 诊断报告样例（每行业 1 份作为模板）
        print("[Factory] 生成 GEO 诊断报告样例...")
        from geo_audit import run_audit
        for ind in INDUSTRIES[:3]:  # 家装、跨境、法律
            run_audit(f"样例客户-{ind['name']}", ind["name"])
        if not self.dry_run:
            self.capital.spend(self.exp.id, self.cost_geo, "GEO 诊断报告样例生成")
        self.exp.spent_cny += self.cost_geo

        # 2.3 生成触达队列（数量随 target_leads 收缩，避免超预算）
        print("[Factory] 生成触达队列...")
        from outreach import build_queue, export_queue
        n_a = min(60, self.exp.target_leads)
        n_b = min(40, max(0, self.exp.target_leads - n_a))
        for tier, n in (("A", n_a), ("B", n_b)):
            if n <= 0:
                continue
            q = build_queue(tier, n)
            p = export_queue(tier, n)
            print(f"  {tier}档: {q} 条 -> {p}")

        if not self.dry_run:
            self.capital.spend(self.exp.id, self.cost_outreach, "触达队列生成与导出")
        self.exp.spent_cny += self.cost_outreach

        # 2.4 记录待触达动作
        # 注意：这里只是"排入待触达队列"，不代表已发送。replied=False，
        # 真实发送与回复由人工确认后用 record_reply/record_deal 推进。
        for lead in self.exp.leads:
            self.exp.touches.append(TouchRecord(
                lead_id=lead.company,
                company=lead.company,
                channel="pending_manual_outreach",
                template_used="GEO诊断三步法",
                sent_at=datetime.now().isoformat(),
                deal_stage="queued_not_sent",
            ))

        self.exp.status = "ready_for_outreach"

    def _finalize(self):
        # 实验此时只是"准备就绪"，尚未触达、更没有回款。
        # 旧版在这里直接 closed_at + capital.close()，等于把
        # "还没赚到钱" 记成"实验已完成"，并提前释放预算。
        # 现在保持 open，只有真的回款后才结项。
        self.exp.status = "ready_for_outreach"

        # 保存完整记录
        exp_file = EXP_DIR / f"{self.exp.id}_full.json"
        data = asdict(self.exp)
        data["touches"] = [asdict(t) for t in self.exp.touches]
        data["leads"] = [asdict(l) for l in self.exp.leads]
        exp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        if self.dry_run:
            print("\n[=== DRY-RUN 完成（未动资金、未写库）===]")
        else:
            print(f"\n[=== 实验准备完成（状态: {self.exp.status}，预算仍占用待回款）===]")
        print(f"  线索: {len(self.exp.leads)} (A档: {sum(1 for l in self.exp.leads if l.tier=='A')})")
        print(f"  待触达: {len(self.exp.touches)}")
        print(f"  已花费: {self.exp.spent_cny} 元")
        print(f"  剩余预算: {self.exp.budget_cny - self.exp.spent_cny} 元")
        print(f"  记录文件: {exp_file}")
        print(f"\n[下一步] 人工执行触达（名单未核验，不得批量自动发送）：")
        print(f"  1. 先核验 CSV 中的公司/联系方式真实性: 99_产出/获客名单/触达队列_A档_*.csv")
        print(f"  2. 逐条确认后人工发送，回复后调用 record_reply()")
        print(f"  3. 回款后调用 record_deal(公司, 金额)，再 close_experiment() 结项")

    def close_experiment(self, outcome: str = "completed"):
        """仅在真实回款或明确失败后结项，释放预算。"""
        if any(t.deal_stage == "closed_won" for t in self.exp.touches):
            self.exp.status = "won"
        else:
            self.exp.status = outcome
        self.exp.closed_at = datetime.now().isoformat()
        if not self.dry_run:
            self.capital.close(self.exp.id, f"实验结项: {self.exp.status}，回款 {self.exp.revenue_cny} 元")
        exp_file = EXP_DIR / f"{self.exp.id}_full.json"
        data = asdict(self.exp)
        data["touches"] = [asdict(t) for t in self.exp.touches]
        data["leads"] = [asdict(l) for l in self.exp.leads]
        exp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"[结项] status={self.exp.status} revenue={self.exp.revenue_cny} 元 roi={self.exp.roi():.1f}%")

    def record_reply(self, company: str, meeting_booked: bool = False):
        for t in self.exp.touches:
            if t.lead_id == company:
                t.replied = True
                t.replied_at = datetime.now().isoformat()
                if meeting_booked:
                    t.meeting_booked = True
                    t.deal_stage = "meeting"
                break

    def record_deal(self, company: str, amount_cny: Decimal):
        # 幂等：同一公司重复记回款只生效一次，避免重复入账。
        # 注意要在"找不到该线索"时也去重，不能只在循环命中分支里判断。
        if company in self._dealt:
            print(f"[跳过] {company} 已记过回款，不重复入账")
            return
        for t in self.exp.touches:
            if t.lead_id == company:
                t.deal_stage = "closed_won"
                t.revenue_cny = amount_cny
                break
        else:
            print(f"[WARN] 未找到线索 {company}，仍记入实验总收入（已去重）")
        self._dealt.add(company)
        self.exp.revenue_cny += amount_cny
        if not self.dry_run:
            self.capital.revenue(self.exp.id, amount_cny, f"GEO 诊断成交: {amount_cny} 元")
        print(f"[回款] {amount_cny} 元，累计回款: {self.exp.revenue_cny}")

def run_first_money(budget_cny=Decimal("2000"), target_leads=50, days=14, dry_run=False):
    runner = FirstMoneyRunner(dry_run=dry_run)
    return runner.run(budget_cny=budget_cny, target_leads=target_leads, days=days)

if __name__ == "__main__":
    run_first_money()