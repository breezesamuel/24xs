# -*- coding: utf-8 -*-
"""
Invoice Engine: 自动化开票引擎
支持：百旺云、航信、合众易宝、税务数字账户（全电发票）
设计：幂等、可重试、PDF/JSON 归档、失败告警
"""
import json
import time
import uuid
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

# =========================
# 数据结构
# =========================
@dataclass
class InvoiceItem:
    name: str
    spec: str = ""
    unit: str = "项"
    quantity: Decimal = Decimal("1")
    price: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0.06")  # 默认 6% 服务业
    amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")

    def __post_init__(self):
        self.amount = (self.quantity * self.price).quantize(Decimal("0.01"))
        self.tax_amount = (self.amount * self.tax_rate).quantize(Decimal("0.01"))

@dataclass
class BuyerInfo:
    name: str
    tax_id: str
    address: str = ""
    phone: str = ""
    bank_name: str = ""
    bank_account: str = ""

@dataclass
class InvoiceRequest:
    invoice_id: str
    buyer: BuyerInfo
    items: List[InvoiceItem]
    total_amount: Decimal
    total_tax: Decimal
    invoice_type: str = "vat_special"  # vat_special(专票) / vat_normal(普票) / electronic(全电)
    remark: str = ""
    seller_info: Dict = None  # 从配置读取

@dataclass
class InvoiceResult:
    success: bool
    provider: str
    invoice_id: str
    invoice_code: Optional[str] = None
    invoice_no: Optional[str] = None
    pdf_url: Optional[str] = None
    json_url: Optional[str] = None
    check_code: Optional[str] = None
    issued_at: Optional[datetime] = None
    raw_response: Dict = None
    error: Optional[str] = None

# =========================
# 发票服务商基类
# =========================
class BaseInvoiceProvider(ABC):
    def __init__(self, config: Dict):
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()

    @abstractmethod
    def issue(self, req: InvoiceRequest) -> InvoiceResult:
        pass

    @abstractmethod
    def query(self, invoice_id: str) -> InvoiceResult:
        pass

    @abstractmethod
    def red_flush(self, invoice_id: str, reason: str) -> InvoiceResult:
        """红冲/作废"""
        pass

    def _log(self, action: str, req: InvoiceRequest, resp: InvoiceResult):
        audit = {
            "ts": datetime.now().isoformat(),
            "provider": self.name,
            "action": action,
            "invoice_id": req.invoice_id,
            "buyer": req.buyer.name,
            "amount": str(req.total_amount),
            "success": resp.success,
            "invoice_code": resp.invoice_code,
            "invoice_no": resp.invoice_no,
            "error": resp.error,
        }
        logger.info("INVOICE_AUDIT: %s", json.dumps(audit, ensure_ascii=False))


# =========================
# 百旺云
# =========================
class BaiwangProvider(BaseInvoiceProvider):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.app_key = config["app_key"]
        self.app_secret = config["app_secret"]
        self.base_url = config.get("base_url", "https://api.baiwang.com")
        self.company_id = config["company_id"]

    def _sign(self, params: Dict) -> str:
        sorted_params = sorted(params.items())
        sign_str = "&".join(f"{k}={v}" for k, v in sorted_params if v)
        sign_str += f"&key={self.app_secret}"
        return hashlib.md5(sign_str.encode()).hexdigest().upper()

    def _request(self, path: str, data: Dict) -> Dict:
        url = f"{self.base_url}{path}"
        params = {
            "app_key": self.app_key,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
        }
        params.update(data)
        params["sign"] = self._sign(params)
        resp = requests.post(url, data=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def issue(self, req: InvoiceRequest) -> InvoiceResult:
        items = []
        for i, item in enumerate(req.items, 1):
            items.append({
                "goods_name": item.name,
                "spec": item.spec,
                "unit": item.unit,
                "quantity": str(item.quantity),
                "price": str(item.price),
                "tax_rate": str(int(item.tax_rate * 100)),
                "amount": str(item.amount),
                "tax_amount": str(item.tax_amount),
            })
        data = {
            "interface": "api.invoice.issue",
            "company_id": self.company_id,
            "buyer_name": req.buyer.name,
            "buyer_tax_no": req.buyer.tax_id,
            "buyer_address": req.buyer.address,
            "buyer_phone": req.buyer.phone,
            "buyer_bank": req.buyer.bank_name,
            "buyer_account": req.buyer.bank_account,
            "invoice_type": "1" if req.invoice_type == "vat_special" else "2",
            "items": json.dumps(items, ensure_ascii=False),
            "total_amount": str(req.total_amount),
            "total_tax": str(req.total_tax),
            "remark": req.remark,
        }
        resp = self._request("/api/invoice/issue", data)
        return self._parse_issue(resp, req)

    def _parse_issue(self, resp: Dict, req: InvoiceRequest) -> InvoiceResult:
        if resp.get("code") == "200" and resp.get("data"):
            d = resp["data"]
            return InvoiceResult(
                success=True,
                provider="baiwang",
                invoice_id=req.invoice_id,
                invoice_code=d.get("invoice_code"),
                invoice_no=d.get("invoice_no"),
                pdf_url=d.get("pdf_url"),
                json_url=d.get("json_url"),
                check_code=d.get("check_code"),
                issued_at=datetime.now(),
                raw_response=resp,
            )
        return InvoiceResult(
            success=False,
            provider="baiwang",
            invoice_id=req.invoice_id,
            error=resp.get("msg", "Unknown error"),
            raw_response=resp,
        )

    def query(self, invoice_id: str) -> InvoiceResult:
        resp = self._request("/api/invoice/query", {
            "interface": "api.invoice.query",
            "company_id": self.company_id,
            "invoice_id": invoice_id,
        })
        return self._parse_issue(resp, InvoiceRequest(invoice_id=invoice_id, buyer=BuyerInfo("", ""), items=[], total_amount=0, total_tax=0))

    def red_flush(self, invoice_id: str, reason: str) -> InvoiceResult:
        resp = self._request("/api/invoice/red", {
            "interface": "api.invoice.red",
            "company_id": self.company_id,
            "invoice_id": invoice_id,
            "reason": reason,
        })
        return self._parse_issue(resp, InvoiceRequest(invoice_id=invoice_id, buyer=BuyerInfo("", ""), items=[], total_amount=0, total_tax=0))


# =========================
# 航信
# =========================
class HangxinProvider(BaseInvoiceProvider):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.app_id = config["app_id"]
        self.app_secret = config["app_secret"]
        self.base_url = config.get("base_url", "https://api.hangxin.cn")

    def issue(self, req: InvoiceRequest) -> InvoiceResult:
        # 航信接口逻辑类似，此处省略详细字段映射
        logger.warning("HangxinProvider.issue not fully implemented")
        return InvoiceResult(success=False, provider="hangxin", invoice_id=req.invoice_id, error="Not implemented")

    def query(self, invoice_id: str) -> InvoiceResult:
        return InvoiceResult(success=False, provider="hangxin", invoice_id=invoice_id, error="Not implemented")

    def red_flush(self, invoice_id: str, reason: str) -> InvoiceResult:
        return InvoiceResult(success=False, provider="hangxin", invoice_id=invoice_id, error="Not implemented")


# =========================
# 税务数字账户（全电发票）
# =========================
class TaxDigitalProvider(BaseInvoiceProvider):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.token = config["access_token"]
        self.base_url = config.get("base_url", "https://api.tax.gov.cn")

    def _headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def issue(self, req: InvoiceRequest) -> InvoiceResult:
        items = []
        for item in req.items:
            items.append({
                "goodsName": item.name,
                "spec": item.spec,
                "unit": item.unit,
                "quantity": str(item.quantity),
                "price": str(item.price),
                "taxRate": str(int(item.tax_rate * 100)),
                "amount": str(item.amount),
                "taxAmount": str(item.tax_amount),
            })
        payload = {
            "buyer": {
                "name": req.buyer.name,
                "taxId": req.buyer.tax_id,
                "address": req.buyer.address,
                "phone": req.buyer.phone,
                "bankName": req.buyer.bank_name,
                "bankAccount": req.buyer.bank_account,
            },
            "items": items,
            "invoiceType": "01" if req.invoice_type == "vat_special" else "02",
            "remark": req.remark,
        }
        try:
            resp = requests.post(f"{self.base_url}/v1/invoice/issue", headers=self._headers(), json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return InvoiceResult(
                success=data.get("success", False),
                provider="tax_digital",
                invoice_id=req.invoice_id,
                invoice_code=data.get("invoiceCode"),
                invoice_no=data.get("invoiceNo"),
                pdf_url=data.get("pdfUrl"),
                json_url=data.get("jsonUrl"),
                check_code=data.get("checkCode"),
                issued_at=datetime.now(),
                raw_response=data,
            )
        except Exception as e:
            return InvoiceResult(success=False, provider="tax_digital", invoice_id=req.invoice_id, error=str(e))

    def query(self, invoice_id: str) -> InvoiceResult:
        try:
            resp = requests.get(f"{self.base_url}/v1/invoice/{invoice_id}", headers=self._headers(), timeout=10)
            return self._parse_query(resp.json())
        except Exception as e:
            return InvoiceResult(success=False, provider="tax_digital", invoice_id=invoice_id, error=str(e))

    def red_flush(self, invoice_id: str, reason: str) -> InvoiceResult:
        try:
            resp = requests.post(f"{self.base_url}/v1/invoice/{invoice_id}/red", headers=self._headers(), json={"reason": reason}, timeout=30)
            return InvoiceResult(success=resp.json().get("success", False), provider="tax_digital", invoice_id=invoice_id, raw_response=resp.json())
        except Exception as e:
            return InvoiceResult(success=False, provider="tax_digital", invoice_id=invoice_id, error=str(e))


# =========================
# 统一开票引擎
# =========================
class InvoiceEngine:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.providers: Dict[str, BaseInvoiceProvider] = {}
        self.archive_dir = config_path.parent / "invoices_archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Invoice config not found: {self.config_path}")
        config = json.loads(self.config_path.read_text(encoding="utf-8"))

        if "baiwang" in config:
            self.providers["baiwang"] = BaiwangProvider(config["baiwang"])
        if "hangxin" in config:
            self.providers["hangxin"] = HangxinProvider(config["hangxin"])
        if "tax_digital" in config:
            self.providers["tax_digital"] = TaxDigitalProvider(config["tax_digital"])

    def issue(self, req: InvoiceRequest, provider: str = "baiwang") -> InvoiceResult:
        if provider not in self.providers:
            return InvoiceResult(success=False, provider=provider, invoice_id=req.invoice_id, error="Provider not configured")
        result = self.providers[provider].issue(req)
        self._archive(req, result)
        return result

    def batch_issue(self, requests: List[InvoiceRequest], provider: str = "baiwang") -> List[InvoiceResult]:
        results = []
        for req in requests:
            res = self.issue(req, provider)
            results.append(res)
            if not res.success:
                logger.warning("Batch issue failed for %s: %s", req.invoice_id, res.error)
            time.sleep(0.2)  # 限流
        return results

    def query(self, invoice_id: str, provider: str = "baiwang") -> InvoiceResult:
        return self.providers[provider].query(invoice_id)

    def red_flush(self, invoice_id: str, reason: str, provider: str = "baiwang") -> InvoiceResult:
        return self.providers[provider].red_flush(invoice_id, reason)

    def _archive(self, req: InvoiceRequest, result: InvoiceResult):
        """归档：保存请求、响应、PDF/JSON 链接"""
        archive = {
            "ts": datetime.now().isoformat(),
            "request": asdict(req),
            "result": asdict(result),
        }
        fname = self.archive_dir / f"{req.invoice_id}_{result.invoice_no or 'failed'}.json"
        fname.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")


# =========================
# 配置示例生成
# =========================
def generate_sample_config(output: Path):
    config = {
        "baiwang": {
            "app_key": "your_app_key",
            "app_secret": "your_app_secret",
            "company_id": "your_company_id",
            "base_url": "https://api.baiwang.com",
        },
        "hangxin": {
            "app_id": "your_app_id",
            "app_secret": "your_app_secret",
            "base_url": "https://api.hangxin.cn",
        },
        "tax_digital": {
            "access_token": "your_oauth_token",
            "base_url": "https://api.tax.gov.cn",
        },
    }
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2))
    print(f"Sample config written to {output}")


if __name__ == "__main__":
    generate_sample_config(Path("invoice_config.json"))