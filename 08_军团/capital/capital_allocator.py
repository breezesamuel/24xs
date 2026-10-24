# -*- coding: utf-8 -*-
"""
Capital Allocator：1 万本金的杠杆分配与复投引擎。
核心原则：
1. 永不满仓，永不单一押注
2. 每个实验上限 500-2000 元，止损线 -50%
3. 盈利实验自动复投，亏损实验归零清理
4. 杠杆只用于已验证正期望值的策略，且不超过净值 20%
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Optional
import json

CAPITAL_DIR = Path(__file__).resolve().parent.parent / "08_军团" / "capital"
CAPITAL_DIR.mkdir(parents=True, exist_ok=True)

class AllocationBucket(Enum):
    COMPUTE_API = "compute_api"          # 算力/API 额度：跑模型、调用 page-agent、向量库
    EXPERIMENT_BUDGET = "experiment"     # 单次实验预算：域名、服务器、广告测试
    LEVERAGE_MARGIN = "leverage"         # 杠杆保证金：仅用于正期望值策略
    REINVEST_POOL = "reinvest"           # 复投池：盈利实验的利润自动流入
    RESERVE = "reserve"                  # 备用金：不可动用，防黑天鹅

@dataclass
class Allocation:
    bucket: AllocationBucket
    amount_cny: Decimal
    max_single_bet_cny: Decimal
    stop_loss_pct: Decimal  # 0.5 = 50%
    description: str

@dataclass
class ExperimentLedger:
    id: str
    name: str
    bucket: AllocationBucket
    allocated_cny: Decimal
    spent_cny: Decimal = Decimal("0")
    revenue_cny: Decimal = Decimal("0")
    status: str = "active"  # active, completed, stopped, reinvested
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    closed_at: Optional[str] = None
    roi_pct: Decimal = Decimal("0")
    notes: str = ""

    def current_value(self) -> Decimal:
        return self.revenue_cny - self.spent_cny

    def roi(self) -> Decimal:
        if self.spent_cny == 0:
            return Decimal("0")
        return (self.current_value() / self.spent_cny * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def should_stop_loss(self, stop_loss_pct: Decimal) -> bool:
        return self.roi() <= -stop_loss_pct * 100

    def should_take_profit(self, take_profit_pct: Decimal = Decimal("100")) -> bool:
        return self.roi() >= take_profit_pct

class CapitalAllocator:
    """
    1 万本金默认分配（可调）：
    - 算力/API: 3000 元 (30%) - 持续性支出
    - 实验预算: 4000 元 (40%) - 单次 500-2000，并行 2-4 个
    - 杠杆保证金: 1000 元 (10%) - 仅用于已验证策略
    - 复投池: 1000 元 (10%) - 初始为空，盈利自动流入
    - 备用金: 1000 元 (10%) - 绝不动用
    """
    DEFAULT_TOTAL = Decimal("10000")

    DEFAULT_ALLOCATIONS = [
        Allocation(AllocationBucket.COMPUTE_API, Decimal("3000"), Decimal("500"), Decimal("0.3"), "模型 API、向量库、Page-Agent 云端并行"),
        Allocation(AllocationBucket.EXPERIMENT_BUDGET, Decimal("4000"), Decimal("2000"), Decimal("0.5"), "域名、VPS、广告测试、外包"),
        Allocation(AllocationBucket.LEVERAGE_MARGIN, Decimal("1000"), Decimal("1000"), Decimal("0.2"), "仅用于正期望值策略，如量化/期权/永续合约"),
        Allocation(AllocationBucket.REINVEST_POOL, Decimal("1000"), Decimal("0"), Decimal("0"), "盈利实验利润自动流入，复投下一轮"),
        Allocation(AllocationBucket.RESERVE, Decimal("1000"), Decimal("0"), Decimal("0"), "绝不动用的防黑天鹅资金"),
    ]

    def __init__(self, total_cny: Decimal = DEFAULT_TOTAL, allocations: Optional[list[Allocation]] = None,
                 state_dir: Path = None):
        self.total_cny = total_cny
        self.allocations = allocations or self.DEFAULT_ALLOCATIONS
        self.ledger: list[ExperimentLedger] = []
        # state_dir 可注入，便于隔离测试账本；默认写模块目录
        self.state_dir = Path(state_dir) if state_dir else CAPITAL_DIR
        self._load_state()

    @property
    def state_file(self) -> Path:
        return self.state_dir / "capital_state.json"

    def _load_state(self):
        state_file = self.state_file
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            self.total_cny = Decimal(data.get("total_cny", str(self.DEFAULT_TOTAL)))
            self.ledger = []
            for e in data.get("ledger", []):
                e = dict(e)
                e["bucket"] = AllocationBucket(e["bucket"])
                e["allocated_cny"] = Decimal(e["allocated_cny"])
                e["spent_cny"] = Decimal(e["spent_cny"])
                e["revenue_cny"] = Decimal(e["revenue_cny"])
                e["roi_pct"] = Decimal(e["roi_pct"])
                self.ledger.append(ExperimentLedger(**e))

    def _save_state(self):
        state_file = self.state_file
        data = {
            "total_cny": str(self.total_cny),
            "updated_at": datetime.now().isoformat(),
            "ledger": [
                {
                    **vars(e),
                    "bucket": e.bucket.value,
                    "allocated_cny": str(e.allocated_cny),
                    "spent_cny": str(e.spent_cny),
                    "revenue_cny": str(e.revenue_cny),
                    "roi_pct": str(e.roi_pct),
                }
                for e in self.ledger
            ],
            "bucket_balances": {a.bucket.value: str(self.available(a.bucket)) for a in self.allocations},
        }
        state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def available(self, bucket: AllocationBucket) -> Decimal:
        """桶内可用余额 = 分配额 - 该桶所有未结清实验的已占用额度

        占用额取 allocated_cny 与 spent_cny 的较大值：一旦分配即锁定额度，
        否则可对同一笔预算反复 allocate（回归：旧实现只看 spent_cny，
        分配后不扣减，可超额分配；且关闭实验后额度被退还，可重复投放）。

        不计入：cancelled（额度释放）、reinvested
              （_maybe_reinvest 已把本金加回本桶，再扣一次会重复扣减）。
        """
        alloc = next(a for a in self.allocations if a.bucket == bucket)
        used = sum(
            (max(e.allocated_cny, e.spent_cny) for e in self.ledger
             if e.bucket == bucket and e.status not in ("cancelled", "reinvested")),
            Decimal("0"),
        )
        return alloc.amount_cny - used

    def can_allocate(self, bucket: AllocationBucket, amount_cny: Decimal) -> bool:
        return self.available(bucket) >= amount_cny

    def allocate(self, bucket: AllocationBucket, exp_id: str, name: str, amount_cny: Decimal, notes: str = "") -> bool:
        if not self.can_allocate(bucket, amount_cny):
            return False
        alloc = next(a for a in self.allocations if a.bucket == bucket)
        if amount_cny > alloc.max_single_bet_cny:
            return False
        exp = ExperimentLedger(
            id=exp_id,
            name=name,
            bucket=bucket,
            allocated_cny=amount_cny,
            notes=notes,
        )
        self.ledger.append(exp)
        self._save_state()
        return True

    def spend(self, exp_id: str, amount_cny: Decimal, notes: str = "") -> bool:
        for e in self.ledger:
            if e.id == exp_id and e.status == "active":
                e.spent_cny += amount_cny
                if notes:
                    e.notes += f" | {notes}"
                self._save_state()
                return True
        return False

    def revenue(self, exp_id: str, amount_cny: Decimal, notes: str = "") -> bool:
        for e in self.ledger:
            if e.id == exp_id:
                e.revenue_cny += amount_cny
                if notes:
                    e.notes += f" | {notes}"
                self._maybe_reinvest(e)
                self._save_state()
                return True
        return False

    def close(self, exp_id: str, reason: str = "") -> bool:
        for e in self.ledger:
            if e.id == exp_id and e.status == "active":
                e.status = "completed"
                e.closed_at = datetime.now().isoformat()
                e.notes += f" | Closed: {reason}"
                self._maybe_reinvest(e)
                self._save_state()
                return True
        return False

    def _maybe_reinvest(self, exp: ExperimentLedger):
        """盈利实验：利润自动流入复投池，本金归还原桶。"""
        profit = exp.revenue_cny - exp.spent_cny
        if profit > 0 and exp.status != "reinvested":
            # 找到复投池分配
            reinvest_alloc = next(a for a in self.allocations if a.bucket == AllocationBucket.REINVEST_POOL)
            reinvest_alloc.amount_cny += profit
            # 本金归还原桶
            orig_alloc = next(a for a in self.allocations if a.bucket == exp.bucket)
            orig_alloc.amount_cny += exp.spent_cny
            exp.status = "reinvested"
            exp.notes += f" | Reinvested profit: {profit} CNY"

    def check_stop_losses(self) -> list[str]:
        """检查所有活跃实验是否触发止损。返回需强平的实验 ID 列表。"""
        to_close = []
        for e in self.ledger:
            if e.status == "active":
                alloc = next(a for a in self.allocations if a.bucket == e.bucket)
                if e.should_stop_loss(alloc.stop_loss_pct):
                    to_close.append(e.id)
        return to_close

    def force_close(self, exp_id: str, reason: str = "Stop loss triggered"):
        self.close(exp_id, reason)

    def summary(self) -> dict:
        active = [e for e in self.ledger if e.status == "active"]
        completed = [e for e in self.ledger if e.status in ("completed", "reinvested")]
        total_invested = sum(e.spent_cny for e in self.ledger)
        total_revenue = sum(e.revenue_cny for e in self.ledger)
        net_pnl = total_revenue - total_invested

        return {
            "total_capital_cny": str(self.total_cny),
            "net_pnl_cny": str(net_pnl),
            "roi_pct": str((net_pnl / total_invested * 100).quantize(Decimal("0.01")) if total_invested else "0"),
            "active_experiments": len(active),
            "completed_experiments": len(completed),
            "bucket_balances": {a.bucket.value: str(self.available(a.bucket)) for a in self.allocations},
            "recent_experiments": [
                {
                    "id": e.id,
                    "name": e.name,
                    "bucket": e.bucket.value,
                    "allocated": str(e.allocated_cny),
                    "spent": str(e.spent_cny),
                    "revenue": str(e.revenue_cny),
                    "roi": str(e.roi()),
                    "status": e.status,
                }
                for e in sorted(self.ledger, key=lambda x: x.started_at, reverse=True)[:10]
            ]
        }

def demo():
    cap = CapitalAllocator()
    print("=== 初始状态 ===")
    print(json.dumps(cap.summary(), ensure_ascii=False, indent=2))

    # 分配 3 个实验
    cap.allocate(AllocationBucket.EXPERIMENT_BUDGET, "exp001", "SEO 站群测试", Decimal("1500"), "用 page-agent 批量建站")
    cap.allocate(AllocationBucket.EXPERIMENT_BUDGET, "exp002", "AI 表单填充 SaaS", Decimal("2000"), "基于 page-agent 核心")
    cap.allocate(AllocationBucket.COMPUTE_API, "exp003", "模型微调实验", Decimal("800"), "LoRA 微调垂直领域")

    print("\n=== 分配后 ===")
    print(json.dumps(cap.summary(), ensure_ascii=False, indent=2))

    # 模拟花费和收入
    cap.spend("exp001", Decimal("500"), "买域名+服务器")
    cap.spend("exp001", Decimal("300"), "内容生成 API")
    cap.revenue("exp001", Decimal("3000"), "卖站给买家")

    cap.spend("exp002", Decimal("1000"), "VPS + 域名")
    cap.revenue("exp002", Decimal("500"), "首月订阅收入")

    cap.spend("exp003", Decimal("800"), "GPU 租用")
    cap.close("exp003", "微调效果不达预期")

    print("\n=== 运行后 ===")
    print(json.dumps(cap.summary(), ensure_ascii=False, indent=2))

    # 止损检查
    print("\n=== 止损检查 ===")
    print(cap.check_stop_losses())

if __name__ == "__main__":
    demo()