# -*- coding: utf-8 -*-
"""
Capital Manager v2: 集成支付网关、开票引擎、税务申报、分红分发
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, List

from capital.payment_gateway import PaymentGatewayManager, PaymentOrder, PaymentResult, NotifyData
from capital.invoice_engine import InvoiceEngine, InvoiceRequest, InvoiceItem, BuyerInfo, InvoiceResult
from capital.tax_filer import TaxFiler, FilingPreview
from capital.capital_allocator import CapitalAllocator
from capital.dividend_distributor import DividendDistributor, Shareholder, DividendPlan

logger = logging.getLogger(__name__)

# =========================
# 统一业务流程
# =========================
@dataclass
class BusinessCycleResult:
    period: str
    payment_results: List[PaymentResult] = field(default_factory=list)
    invoice_results: List[InvoiceResult] = field(default_factory=list)
    tax_preview: Optional[FilingPreview] = None
    dividend_plan: Optional[DividendPlan] = None
    capital_summary: dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

class CapitalManager:
    """统一资金管理器：收款 -> 开票 -> 记账 -> 报税 -> 分红"""
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.capital = CapitalAllocator()
        self.payment_gw = PaymentGatewayManager(config_dir / "payment_config.enc")
        self.invoice_engine = InvoiceEngine(config_dir / "invoice_config.json")
        self.tax_filer = TaxFiler(self.capital)
        self.dividend_dist = DividendDistributor(self.capital, config_dir / "dividend_config.json")

    def on_payment_received(self, notify: NotifyData) -> BusinessCycleResult:
        """收款回调处理：记账 -> 开票 -> 触发交付"""
        result = BusinessCycleResult(period=notify.paid_at.strftime("%Y-%m"))

        # 1. 记账
        exp_id = notify.order_id
        self.capital.revenue(exp_id, notify.amount_cny, f"Payment {notify.trade_no}")

        # 2. 自动开票（需买方信息，这里简化：从订单附属数据获取）
        # 实际需从订单系统获取买方信息
        # invoice_req = InvoiceRequest(...)
        # inv_res = self.invoice_engine.issue(invoice_req)
        # result.invoice_results.append(inv_res)

        # 3. 记录
        result.capital_summary = self.capital.summary()
        return result

    def monthly_cycle(self, period: str) -> BusinessCycleResult:
        """月度结账：报税预览 -> 人工确认 -> 提交"""
        result = BusinessCycleResult(period=period)

        # 1. 税务预览
        preview = self.tax_filer.preview_all(period)
        result.tax_preview = preview
        exported = self.tax_filer.export_for_manual_filing(preview)

        # 2. 保存导出数据供人工填报
        export_file = Path(__file__).parent / "tax_previews" / f"{period}_filing_export.json"
        export_file.parent.mkdir(parents=True, exist_ok=True)
        export_file.write_text(json.dumps(exported, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        result.capital_summary = self.capital.summary()
        return result

    def quarterly_dividend(self, period: str) -> BusinessCycleResult:
        """季度分红"""
        result = BusinessCycleResult(period=period)

        summary = self.capital.summary()
        net_pnl = Decimal(summary["net_pnl_cny"])
        if net_pnl <= 0:
            result.errors.append("No profit to distribute")
            return result

        # 股东名册从加密名册读取，绝不硬编码真实姓名/银行账户
        shareholders = self.dividend_dist.load_shareholder_register()
        if not shareholders:
            result.errors.append(
                "Shareholder register missing (shareholders.enc); dividend draft not created"
            )
            return result

        plan = self.dividend_dist.create_plan(
            period=period,
            total_profit_cny=Decimal(summary["net_pnl_cny"]),
            retained_cny=Decimal(summary["net_pnl_cny"]) * Decimal("0.30"),
            shareholders=shareholders,
        )

        # 审批必须由两名不同的外部自然人在系统外完成；此处不模拟、不自动批准
        result.errors.append(
            f"Dividend draft {plan.plan_id} created; requires two distinct human approvals before execution"
        )

        result.dividend_plan = plan
        result.capital_summary = self.capital.summary()
        return result

    def full_cycle(self, period: str) -> BusinessCycleResult:
        """完整月度/季度循环"""
        result = BusinessCycleResult(period=period)

        # 1. 月度报税
        tax_result = self.monthly_cycle(period)
        result.tax_preview = tax_result.tax_preview
        result.errors.extend(tax_result.errors)

        # 2. 季度分红（每 3 个月）
        if int(period.split("-")[1]) % 3 == 0:
            div_result = self.quarterly_dividend(period)
            result.dividend_plan = div_result.dividend_plan
            result.errors.extend(div_result.errors)

        result.capital_summary = self.capital.summary()
        return result


# =========================
# CLI 入口
# =========================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Capital Manager v2")
    parser.add_argument("action", choices=["payment_notify", "monthly", "quarterly", "full"])
    parser.add_argument("--period", default=datetime.now().strftime("%Y-%m"))
    parser.add_argument("--config-dir", default="F:/2026/24xs/08_军团/capital")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    mgr = CapitalManager(config_dir)

    if args.action == "payment_notify":
        # 模拟回调测试
        from capital.payment_gateway import NotifyData
        notify = NotifyData(
            gateway="alipay",
            trade_no="2026093022001400001234",
            order_id="exp_001",
            amount_cny=Decimal("120000"),
            paid_at=datetime.now(),
        )
        result = mgr.on_payment_received(notify)
    elif args.action == "monthly":
        result = mgr.monthly_cycle(args.period)
    elif args.action == "quarterly":
        result = mgr.quarterly_dividend(args.period)
    elif args.action == "full":
        result = mgr.full_cycle(args.period)

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()