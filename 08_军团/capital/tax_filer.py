# -*- coding: utf-8 -*-
"""
Tax Filer: 税务申报预填/预览/辅助提交
支持：增值税申报表、企业所得税季报/年报、附加税
设计：仅预览/预填，最终提交需人工确认/CA签名
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from capital.capital_allocator import CapitalAllocator

logger = logging.getLogger(__name__)

# =========================
# 数据结构
# =========================
@dataclass
class VATReturn:
    period: str  # "2026-09"
    company_name: str
    tax_id: str
    # 销项税额
    sales_output_tax: Decimal = Decimal("0")      # 一般计税销项
    sales_output_tax_reduced: Decimal = Decimal("0")  # 简易计税/免税销项
    # 进项税额
    input_tax_deductible: Decimal = Decimal("0")   # 可抵扣进项
    input_tax_non_deductible: Decimal = Decimal("0")  # 不可抵扣进项
    # 附加税
    urban_construction_tax: Decimal = Decimal("0")
    education_surcharge: Decimal = Decimal("0")
    local_education_surcharge: Decimal = Decimal("0")
    # 计算结果
    vat_payable: Decimal = Decimal("0")
    total_tax_payable: Decimal = Decimal("0")

    def calculate(self):
        self.vat_payable = (self.sales_output_tax + self.sales_output_tax_reduced - self.input_tax_deductible).quantize(Decimal("0.01"))
        if self.vat_payable < 0:
            self.vat_payable = Decimal("0")
        # 附加税按增值税额计算（城建税7%/5%，教育费附加3%，地方教育附加2%）
        rate = Decimal("0.12")  # 7%+3%+2% = 12%，按实际地区调整
        self.urban_construction_tax = (self.vat_payable * Decimal("0.07")).quantize(Decimal("0.01"))
        self.education_surcharge = (self.vat_payable * Decimal("0.03")).quantize(Decimal("0.01"))
        self.local_education_surcharge = (self.vat_payable * Decimal("0.02")).quantize(Decimal("0.01"))
        self.total_tax_payable = (self.vat_payable + self.urban_construction_tax + self.education_surcharge + self.local_education_surcharge).quantize(Decimal("0.01"))

@dataclass
class CorporateTaxReturn:
    period: str  # "2026-Q3" or "2026"
    company_name: str
    tax_id: str
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    operating_expense: Decimal = Decimal("0")
    taxable_income: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0.25")
    tax_payable: Decimal = Decimal("0")
    prepaid_tax: Decimal = Decimal("0")
    tax_refund_or_pay: Decimal = Decimal("0")

    def calculate(self):
        self.gross_profit = self.revenue - self.cost
        self.taxable_income = self.gross_profit - self.operating_expense
        if self.taxable_income < 0:
            self.taxable_income = Decimal("0")
        self.tax_payable = (self.taxable_income * self.tax_rate).quantize(Decimal("0.01"))
        self.tax_refund_or_pay = (self.tax_payable - self.prepaid_tax).quantize(Decimal("0.01"))

@dataclass
class FilingPreview:
    period: str
    vat: Optional[VATReturn] = None
    corporate: Optional[CorporateTaxReturn] = None
    generated_at: datetime = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.generated_at is None:
            self.generated_at = datetime.now()

# =========================
# 税务申报引擎
# =========================
class TaxFiler:
    def __init__(self, capital: CapitalAllocator, entity_path: Path = None):
        self.capital = capital
        self.preview_dir = Path(__file__).resolve().parent / "tax_previews"
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self.entity_path = entity_path or (Path(__file__).resolve().parent / "entity_profile.json")
        self.entity = self._load_entity()

    def _load_entity(self) -> Dict:
        """纳税主体信息来自独立配置；缺失时为空，预览会被标记为不可用"""
        if not self.entity_path.exists():
            logger.warning("Entity profile not found: %s", self.entity_path)
            return {}
        return json.loads(self.entity_path.read_text(encoding="utf-8"))

    def preview_vat(self, period: str) -> VATReturn:
        """从账本聚合生成增值税申报表预览"""
        # 1. 从 capital.ledger 聚合收入/支出
        ledger = self.capital.ledger
        sales_output = Decimal("0")
        sales_reduced = Decimal("0")
        input_deduct = Decimal("0")
        input_nondeduct = Decimal("0")

        for exp in ledger:
            if exp.status in ("completed", "reinvested") and exp.revenue_cny > 0:
                # 简化：所有收入按 6% 计税（服务业）
                sales_output += exp.revenue_cny * Decimal("0.06")
            if exp.status in ("completed", "reinvested") and exp.spent_cny > 0:
                # 简化：所有支出按 6% 进项（实际需区分专票/普票、可抵扣/不可抵扣）
                input_deduct += exp.spent_cny * Decimal("0.06")

        vat = VATReturn(
            period=period,
            company_name=self.entity.get("company_name", ""),
            tax_id=self.entity.get("tax_id", ""),
            sales_output_tax=sales_output.quantize(Decimal("0.01")),
            sales_output_tax_reduced=sales_reduced,
            input_tax_deductible=input_deduct.quantize(Decimal("0.01")),
            input_tax_non_deductible=input_nondeduct,
        )
        vat.calculate()
        return vat

    def preview_corporate(self, period: str) -> CorporateTaxReturn:
        """从账本聚合生成企业所得税申报表预览"""
        ledger = self.capital.ledger
        revenue = Decimal("0")
        cost = Decimal("0")
        expense = Decimal("0")

        for exp in ledger:
            if exp.status in ("completed", "reinvested"):
                revenue += exp.revenue_cny
                cost += exp.spent_cny * Decimal("0.4")  # 简化：成本率 40%
                expense += exp.spent_cny * Decimal("0.2")  # 简化：费用率 20%

        corp = CorporateTaxReturn(
            period=period,
            company_name=self.entity.get("company_name", ""),
            tax_id=self.entity.get("tax_id", ""),
            revenue=revenue.quantize(Decimal("0.01")),
            cost=cost.quantize(Decimal("0.01")),
            operating_expense=expense.quantize(Decimal("0.01")),
        )
        corp.calculate()
        return corp

    def preview_all(self, period: str) -> FilingPreview:
        vat = self.preview_vat(period)
        corp = self.preview_corporate(period)
        preview = FilingPreview(period=period, vat=vat, corporate=corp)

        # 告警
        if vat.vat_payable > 0 and vat.vat_payable > vat.input_tax_deductible * Decimal("2"):
            preview.warnings.append("销项税远大于进项税，建议检查进项发票是否全取得")
        if corp.taxable_income > 0 and corp.tax_refund_or_pay > 0:
            preview.warnings.append(f"本期需补缴企业所得税 {corp.tax_refund_or_pay} 元")

        self._save_preview(preview)
        return preview

    def _save_preview(self, preview: FilingPreview):
        preview_dir = Path(__file__).parent / "tax_previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        fname = preview_dir / f"{preview.period.replace('/', '-')}_preview.json"
        fname.write_text(json.dumps(asdict(preview), ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def export_for_manual_filing(self, preview: FilingPreview) -> Dict:
        """导出人工填报所需数据（对应电子税务局表单字段）"""
        return {
            "vat_form": {
                "period": preview.vat.period,
                "row_1_sales_standard": str(preview.vat.sales_output_tax),
                "row_2_sales_reduced": str(preview.vat.sales_output_tax_reduced),
                "row_10_input_deductible": str(preview.vat.input_tax_deductible),
                "row_14_vat_payable": str(preview.vat.vat_payable),
                "row_15_urban_tax": str(preview.vat.urban_construction_tax),
                "row_16_edu_surcharge": str(preview.vat.education_surcharge),
                "row_17_local_edu_surcharge": str(preview.vat.local_education_surcharge),
            },
            "corporate_form": {
                "period": preview.corporate.period,
                "row_1_revenue": str(preview.corporate.revenue),
                "row_2_cost": str(preview.corporate.cost),
                "row_10_taxable_income": str(preview.corporate.taxable_income),
                "row_15_tax_payable": str(preview.corporate.tax_payable),
                "row_20_prepaid": str(preview.corporate.prepaid_tax),
                "row_25_refund_or_pay": str(preview.corporate.tax_refund_or_pay),
            },
            "warnings": preview.warnings,
        }

    def submit_if_approved(self, period: str, approved_by_human: bool, submitter: str = "") -> bool:
        """未接入电子税务局/财税 SaaS 之前一律拒绝提交（fail-closed）

        本方法永远不会返回 True。真实申报必须由持证会计或授权代理人在
        电子税务局完成，或在配置并验证官方 API 后改造本方法。
        """
        logger.error(
            "Tax submission blocked: no filing channel configured (period=%s, submitter=%r, approved=%s). "
            "File via the official e-tax portal manually.",
            period, submitter, approved_by_human,
        )
        return False

    def get_preview_file(self, period: str) -> Optional[Path]:
        fname = Path(__file__).parent / "tax_previews" / f"{period.replace('/', '-')}_preview.json"
        return fname if fname.exists() else None


if __name__ == "__main__":
    from capital.capital_allocator import CapitalAllocator
    cap = CapitalAllocator()
    filer = TaxFiler(cap)
    preview = filer.preview_all("2026-09")
    print(json.dumps(asdict(preview), ensure_ascii=False, indent=2, default=str))
    exported = filer.export_for_manual_filing(preview)
    print(json.dumps(exported, ensure_ascii=False, indent=2, default=str))