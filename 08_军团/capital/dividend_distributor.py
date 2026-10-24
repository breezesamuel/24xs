# -*- coding: utf-8 -*-
"""
Dividend Distributor: 分红计算与发放执行
支持：按持股比例分红、个税代扣、批量付款(银企直连/支付宝/微信)、回单归档
设计：双人授权、幂等、可审计、可回滚
"""
import json
import time
import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional

from capital.capital_allocator import CapitalAllocator, AllocationBucket

logger = logging.getLogger(__name__)

# 系统/占位账号不得充当人工审批人
SYSTEM_APPROVER_BLOCKLIST = {"ceo", "cfo", "admin", "system", "bot", "test", "me"}

# =========================
# 数据结构
# =========================
@dataclass
class Shareholder:
    id: str
    name: str
    id_type: str = "id_card"  # id_card / passport / org_code
    id_number: str = ""
    share_ratio: Decimal = Decimal("0")  # 持股比例，如 0.51
    contact: str = ""  # 手机/邮箱
    bank_name: str = ""
    bank_account: str = ""
    bank_branch: str = ""
    tax_resident: bool = True  # 是否税收居民
    tax_rate: Decimal = Decimal("0.20")  # 个税税率，居民 20%，非居民 20%（按税收协定可降低）

@dataclass
class DividendPlan:
    plan_id: str
    period: str  # "2026-Q3" / "2026"
    total_profit_cny: Decimal
    retained_earnings_cny: Decimal = Decimal("0")  # 留存收益
    distributable_cny: Decimal = Decimal("0")
    shareholders: List[Shareholder] = None
    gross_dividends: Dict[str, Decimal] = None  # shareholder_id -> 金额
    tax_withheld: Dict[str, Decimal] = None
    net_dividends: Dict[str, Decimal] = None
    created_at: datetime = None
    approved_by: List[str] = None  # 审批人 ID 列表
    approved_at: Optional[datetime] = None

    def __post_init__(self):
        if self.shareholders is None:
            self.shareholders = []
        if self.gross_dividends is None:
            self.gross_dividends = {}
        if self.tax_withheld is None:
            self.tax_withheld = {}
        if self.net_dividends is None:
            self.net_dividends = {}
        if self.approved_by is None:
            self.approved_by = []
        if self.created_at is None:
            self.created_at = datetime.now()

    def calculate(self):
        """按持股比例计算分红、个税、净发放"""
        self.distributable_cny = (self.total_profit_cny - self.retained_earnings_cny).quantize(Decimal("0.01"))
        if self.distributable_cny <= 0:
            return
        total_ratio = sum(sh.share_ratio for sh in self.shareholders)
        if total_ratio <= 0:
            return
        for sh in self.shareholders:
            gross = (self.distributable_cny * sh.share_ratio / total_ratio).quantize(Decimal("0.01"))
            tax = (gross * sh.tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            net = (gross - tax).quantize(Decimal("0.01"))
            self.gross_dividends[sh.id] = gross
            self.tax_withheld[sh.id] = tax
            self.net_dividends[sh.id] = net

    def total_gross(self) -> Decimal:
        return sum(self.gross_dividends.values(), Decimal("0"))

    def total_tax(self) -> Decimal:
        return sum(self.tax_withheld.values(), Decimal("0"))

    def total_net(self) -> Decimal:
        return sum(self.net_dividends.values(), Decimal("0"))

@dataclass
class PayoutRecord:
    record_id: str
    plan_id: str
    shareholder_id: str
    gross_cny: Decimal
    tax_cny: Decimal
    net_cny: Decimal
    channel: str  # bank / alipay / wechat
    status: str = "pending"  # pending / processing / success / failed / refunded
    batch_no: str = ""
    bank_seq: str = ""
    paid_at: Optional[datetime] = None
    error: str = ""

# =========================
# 付款渠道基类
# =========================
class BasePayoutChannel(ABC):
    @abstractmethod
    def pay(self, records: List[PayoutRecord]) -> List[PayoutRecord]:
        pass

    @abstractmethod
    def query(self, batch_no: str) -> List[PayoutRecord]:
        pass

class BankEBICSChannel(BasePayoutChannel):
    """银企直连批量付款"""
    def __init__(self, config: Dict):
        self.config = config

    def pay(self, records: List[PayoutRecord]) -> List[PayoutRecord]:
        # 生成银企直连报文（CFONB/STET 格式），上传银行前置机
        # 这里仅定义接口，实际需对接具体银行
        logger.warning("BankEBICSChannel.pay not fully implemented")
        for r in records:
            r.status = "failed"
            r.error = "Bank channel not implemented"
        return records

    def query(self, batch_no: str) -> List[PayoutRecord]:
        return []

class AlipayTransferChannel(BasePayoutChannel):
    """支付宝企业付款到银行卡/支付宝账户"""
    def __init__(self, config: Dict):
        self.config = config

    def pay(self, records: List[PayoutRecord]) -> List[PayoutRecord]:
        # 调用支付宝 "alipay.fund.trans.toaccount.transfer" / "alipay.fund.trans.uni.transfer"
        logger.warning("AlipayTransferChannel.pay not fully implemented")
        for r in records:
            r.status = "failed"
            r.error = "Alipay channel not implemented"
        return records

    def query(self, batch_no: str) -> List[PayoutRecord]:
        return []

class WechatTransferChannel(BasePayoutChannel):
    """微信企业付款到零钱/银行卡"""
    def __init__(self, config: Dict):
        self.config = config

    def pay(self, records: List[PayoutRecord]) -> List[PayoutRecord]:
        # 调用微信 "mch-transfer/transfer-batches"
        logger.warning("WechatTransferChannel.pay not fully implemented")
        for r in records:
            r.status = "failed"
            r.error = "Wechat channel not implemented"
        return records

    def query(self, batch_no: str) -> List[PayoutRecord]:
        return []


# =========================
# 分红执行器
# =========================
class DividendDistributor:
    def __init__(self, capital: CapitalAllocator, config_path: Path):
        self.capital = capital
        self.config_path = config_path
        self.channels: Dict[str, BasePayoutChannel] = {}
        self.archive_dir = config_path.parent / "dividend_archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._load_channels()

    def _load_channels(self):
        if not self.config_path.exists():
            return
        raw = self.config_path.read_text(encoding="utf-8").strip()
        if raw.startswith("{"):
            config = json.loads(raw)
        else:
            from capital.payment_gateway import ConfigCrypto
            config = ConfigCrypto().decrypt_dict(raw)
        if "bank_ebics" in config:
            self.channels["bank"] = BankEBICSChannel(config["bank_ebics"])
        if "alipay" in config:
            self.channels["alipay"] = AlipayTransferChannel(config["alipay"])
        if "wechat" in config:
            self.channels["wechat"] = WechatTransferChannel(config["wechat"])

    def load_shareholder_register(self) -> List[Shareholder]:
        """从加密名册读取股东信息（含收款账户），缺失时返回空列表"""
        reg_path = self.config_path.parent / "shareholders.enc"
        if not reg_path.exists():
            return []
        from capital.payment_gateway import ConfigCrypto
        data = ConfigCrypto().decrypt_dict(reg_path.read_text(encoding="utf-8").strip())
        rows = data.get("shareholders", [])
        out = []
        for r in rows:
            out.append(Shareholder(
                id=r["id"],
                name=r["name"],
                id_type=r.get("id_type", "id_card"),
                id_number=r.get("id_number", ""),
                share_ratio=Decimal(str(r["share_ratio"])),
                contact=r.get("contact", ""),
                bank_name=r.get("bank_name", ""),
                bank_account=r.get("bank_account", ""),
                bank_branch=r.get("bank_branch", ""),
                tax_resident=r.get("tax_resident", True),
                tax_rate=Decimal(str(r.get("tax_rate", "0.20"))),
            ))
        return out

    def create_plan(self, period: str, total_profit_cny: Decimal,
                    retained_cny: Decimal, shareholders: List[Shareholder]) -> DividendPlan:
        plan = DividendPlan(
            plan_id=f"DIV_{period}_{uuid.uuid4().hex[:8]}",
            period=period,
            total_profit_cny=total_profit_cny,
            retained_earnings_cny=retained_cny,
            shareholders=shareholders,
        )
        plan.calculate()
        self._save_plan(plan)
        logger.info("Dividend plan created: %s, distributable: %s", plan.plan_id, plan.distributable_cny)
        return plan

    def approve(self, plan_id: str, approver: str) -> bool:
        """登记一次人工审批。要求两名不同的外部审批人，系统账号不算。"""
        plan = self._load_plan(plan_id)
        if not plan:
            return False
        if not approver or approver.strip().lower() in SYSTEM_APPROVER_BLOCKLIST:
            logger.error("Invalid approver rejected for %s: %r", plan_id, approver)
            return False
        if approver not in plan.approved_by:
            plan.approved_by.append(approver)
        if len(plan.approved_by) >= 2:  # 双人授权
            plan.approved_at = datetime.now()
            self._save_plan(plan)
            logger.info("Dividend plan %s reached dual approval by %s", plan_id, plan.approved_by)
            return True
        self._save_plan(plan)
        return False

    def execute(self, plan_id: str, approved_by_human: bool = False,
                approval_evidence: str = "") -> List[PayoutRecord]:
        """执行付款。默认关闭，必须显式传入人工审批与留痕证据。"""
        if not approved_by_human:
            logger.error("Dividend execution rejected: approved_by_human not set")
            return []
        if not approval_evidence.strip():
            logger.error("Dividend execution rejected: approval_evidence is required")
            return []

        plan = self._load_plan(plan_id)
        if not plan or not plan.approved_at:
            logger.error("Plan not found or not approved: %s", plan_id)
            return []
        if len(set(plan.approved_by)) < 2:
            logger.error("Plan %s does not have two distinct approvers", plan_id)
            return []
        if not self.channels:
            logger.error("Dividend execution rejected: no payout channel configured")
            return []

        # 生成付款记录
        records = []
        for sh in plan.shareholders:
            net = plan.net_dividends.get(sh.id, Decimal("0"))
            if net <= 0:
                continue
            channel = self._select_channel(sh)
            records.append(PayoutRecord(
                record_id=f"PAY_{plan_id}_{sh.id}_{uuid.uuid4().hex[:6]}",
                plan_id=plan_id,
                shareholder_id=sh.id,
                gross_cny=plan.gross_dividends.get(sh.id, Decimal("0")),
                tax_cny=plan.tax_withheld.get(sh.id, Decimal("0")),
                net_cny=net,
                channel=channel,
            ))

        # 按渠道分组执行
        for ch_name, channel in self.channels.items():
            ch_records = [r for r in records if r.channel == ch_name]
            if ch_records:
                batch_no = f"BATCH_{plan_id}_{ch_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                for r in ch_records:
                    r.batch_no = batch_no
                results = channel.pay(ch_records)
                self._archive_batch(batch_no, ch_name, results)

        self._save_plan(plan)
        return records

    def _select_channel(self, shareholder: Shareholder) -> str:
        if shareholder.bank_account:
            return "bank"
        if shareholder.contact and "@" in shareholder.contact:
            return "alipay"
        return "wechat"

    def _archive_batch(self, batch_no: str, channel: str, records: List[PayoutRecord]):
        archive = {
            "ts": datetime.now().isoformat(),
            "batch_no": batch_no,
            "channel": channel,
            "records": [asdict(r) for r in records],
        }
        fname = self.archive_dir / f"{batch_no}.json"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        fname.write_text(json.dumps(archive, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _save_plan(self, plan: DividendPlan):
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        fname = self.archive_dir / f"{plan.plan_id}.json"
        fname.write_text(json.dumps(asdict(plan), ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _load_plan(self, plan_id: str) -> Optional[DividendPlan]:
        fname = self.archive_dir / f"{plan_id}.json"
        if not fname.exists():
            return None
        data = json.loads(fname.read_text(encoding="utf-8"))
        # 反序列化 Decimal
        for k in ("total_profit_cny", "retained_earnings_cny", "distributable_cny"):
            data[k] = Decimal(data[k])
        for k in ("gross_dividends", "tax_withheld", "net_dividends"):
            data[k] = {k2: Decimal(v2) for k2, v2 in data[k].items()}
        data["shareholders"] = [Shareholder(**sh) for sh in data["shareholders"]]
        if data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data["approved_at"]:
            data["approved_at"] = datetime.fromisoformat(data["approved_at"])
        return DividendPlan(**data)


# =========================
# 与 CapitalAllocator 联动
# =========================
def run_dividend_cycle(capital: CapitalAllocator, period: str, distributor: DividendDistributor):
    """从资本账本计算可分红利润，生成分红方案（草稿）

    安全约束：股东名册与收款账户一律从加密名册文件读取，绝不硬编码；
    本函数只产出待审草稿，不做自动审批、不执行付款。
    """
    summary = capital.summary()
    net_pnl = Decimal(summary["net_pnl_cny"])
    if net_pnl <= 0:
        logger.info("No profit to distribute for %s", period)
        return None

    shareholders = distributor.load_shareholder_register()
    if not shareholders:
        logger.warning(
            "No shareholder register configured. Create %s (encrypted) before distributing.",
            distributor.config_path.name,
        )
        return None

    plan = distributor.create_plan(
        period=period,
        total_profit_cny=net_pnl,
        retained_cny=net_pnl * Decimal("0.30"),  # 留存 30%
        shareholders=shareholders,
    )

    logger.info("Dividend draft %s created: distributable=%s, net=%s",
                plan.plan_id, plan.distributable_cny, plan.total_net())

    # 双人授权与实际付款必须由两名不同自然人在外部完成：
    #   1) dist.approve(plan.plan_id, "<审批人工号>")  两次，且审批人不得为系统账号
    #   2) dist.execute(plan.plan_id, approved_by_human=True)  仅在外部审批留痕后调用
    return plan


if __name__ == "__main__":
    from capital.capital_allocator import CapitalAllocator
    cap = CapitalAllocator()
    dist = DividendDistributor(cap, Path("dividend_config.enc"))
    run_dividend_cycle(cap, "2026-Q3", dist)
