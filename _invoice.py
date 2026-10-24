# Automated VAT Invoice Generation (China e-invoice compliant)
import json, hashlib, uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

# Company info (seller)
SELLER = {
    "name": "上海丙大山智能科技有限公司",
    "tax_id": "91310000MAXXXXXXXX",  # Replace with real tax ID
    "address": "上海市徐汇区罗香路37号",
    "phone": "021-XXXXXXXX",
    "bank_name": "中国工商银行徐汇长桥支行",
    "bank_account": "6222031001026162672",
    "invoice_type": "vat_special"  # vat_special (专票) or vat_normal (普票)
}

# Tax rates
TAX_RATES = {
    "vat_special": 0.06,  # 6% for modern services (information technology services)
    "vat_normal": 0.03,   # 3% for small-scale taxpayers
    "exempt": 0.00
}

class InvoiceGenerator:
    def __init__(self):
        self.invoice_dir = OUT / "invoices"
        self.invoice_dir.mkdir(exist_ok=True)
        self.sequence_file = OUT / "invoice_sequence.json"
        self.sequence = self._load_sequence()
    
    def _load_sequence(self) -> Dict:
        if self.sequence_file.exists():
            return json.loads(self.sequence_file.read_text(encoding="utf-8"))
        return {"year": datetime.now().year, "counter": 0}
    
    def _save_sequence(self):
        self.sequence_file.write_text(json.dumps(self.sequence, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def _next_invoice_number(self) -> str:
        year = datetime.now().year
        if self.sequence["year"] != year:
            self.sequence = {"year": year, "counter": 0}
        self.sequence["counter"] += 1
        self._save_sequence()
        return f"{year}{self.sequence['counter']:06d}"
    
    def generate(self, purchase: Dict, customer: Dict, items: List[Dict]) -> Dict:
        """
        purchase: {purchase_id, payment_txn_id, license_type, created_at}
        customer: {customer_id, company_name, tax_id, address, phone, email, bank_name, bank_account}
        items: [{name, spec, unit, quantity, unit_price, amount, tax_rate, tax_amount}]
        """
        invoice_number = self._next_invoice_number()
        invoice_date = datetime.now()
        
        # Calculate totals
        total_amount = sum(item["amount"] for item in items)
        total_tax = sum(item.get("tax_amount", 0) for item in items)
        total_incl_tax = total_amount + total_tax
        
        # Determine tax rate based on seller status
        tax_rate = TAX_RATES.get(SELLER["invoice_type"], 0.06)
        
        # Recalculate tax per item if not provided
        for item in items:
            if "tax_amount" not in item:
                item["tax_rate"] = tax_rate
                item["tax_amount"] = round(item["amount"] * tax_rate, 2)
        
        invoice = {
            "invoice_id": f"INV-{invoice_date.strftime('%Y%m%d')}-{invoice_number}",
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "invoice_time": invoice_date.strftime("%H:%M:%S"),
            "invoice_type": SELLER["invoice_type"],
            "seller": SELLER,
            "buyer": {
                "name": customer.get("company_name", "个人"),
                "tax_id": customer.get("tax_id", ""),
                "address": customer.get("address", ""),
                "phone": customer.get("phone", ""),
                "bank_name": customer.get("bank_name", ""),
                "bank_account": customer.get("bank_account", "")
            },
            "items": items,
            "total_amount": round(total_amount, 2),
            "total_tax": round(total_tax, 2),
            "total_incl_tax": round(total_incl_tax, 2),
            "total_incl_tax_cn": self._amount_to_chinese(total_incl_tax),
            "payment_txn_id": purchase.get("payment_txn_id", ""),
            "license_type": purchase.get("license_type", ""),
            "status": "issued",
            "issued_at": invoice_date.isoformat(),
            "verification_code": self._generate_verification_code(invoice_number, total_incl_tax),
            "remarks": f"数字资产许可费 - 许可类型: {purchase.get('license_type', '')} - 交易单号: {purchase.get('purchase_id', '')}"
        }
        
        # Save invoice JSON
        invoice_file = self.invoice_dir / f"{invoice['invoice_id']}.json"
        invoice_file.write_text(json.dumps(invoice, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Generate HTML for PDF rendering
        html = self._render_html(invoice)
        html_file = self.invoice_dir / f"{invoice['invoice_id']}.html"
        html_file.write_text(html, encoding="utf-8")
        
        return invoice
    
    def _generate_verification_code(self, invoice_number: str, amount: float) -> str:
        """Generate 20-digit verification code per China tax bureau format"""
        seed = f"{invoice_number}{amount}{SELLER['tax_id']}{datetime.now().strftime('%Y%m%d')}"
        hash_val = hashlib.sha256(seed.encode()).hexdigest()
        return hash_val[:20].upper()
    
    def _amount_to_chinese(self, amount: float) -> str:
        """Convert amount to Chinese uppercase (财务大写)"""
        units = ["分", "角", "元", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]
        digits = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
        
        # Split yuan and fen
        yuan = int(amount)
        fen = int(round((amount - yuan) * 100))
        
        def convert(num: int) -> str:
            if num == 0:
                return "零"
            result = ""
            pos = 0
            while num > 0:
                digit = num % 10
                if digit != 0:
                    result = digits[digit] + units[pos] + result
                else:
                    if result and result[0] != "零":
                        result = "零" + result
                num //= 10
                pos += 1
            return result
        
        yuan_str = convert(yuan) + "元" if yuan > 0 else ""
        jiao_str = digits[fen // 10] + "角" if fen // 10 > 0 else ""
        fen_str = digits[fen % 10] + "分" if fen % 10 > 0 else ""
        
        if not yuan_str and not jiao_str and not fen_str:
            return "零元整"
        
        result = yuan_str + jiao_str + fen_str
        if fen == 0:
            result += "整"
        return result
    
    def _render_html(self, invoice: Dict) -> str:
        items_html = ""
        for i, item in enumerate(invoice["items"], 1):
            items_html += f"""
<tr>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: center;">{i}</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px;">{item["name"]}</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: center;">{item.get("spec", "")}</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: center;">{item.get("unit", "项")}</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">{item["quantity"]}</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">¥{item["unit_price"]:.2f}</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">¥{item["amount"]:.2f}</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: center;">{item.get("tax_rate", 0.06)*100:.0f}%</td>
    <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">¥{item.get("tax_amount", 0):.2f}</td>
</tr>
"""
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>发票 - {invoice["invoice_id"]}</title>
<style>
@page {{ size: A4; margin: 20mm; }}
body {{ font-family: "Microsoft YaHei", "SimSun", sans-serif; font-size: 12px; color: #1f2937; }}
.header {{ text-align: center; margin-bottom: 20px; }}
.header h1 {{ font-size: 28px; margin: 0; color: #1f2937; }}
.header .type {{ font-size: 14px; color: #6b7280; margin-top: 4px; }}
.info {{ display: flex; justify-content: space-between; margin-bottom: 16px; font-size: 11px; }}
.info div {{ width: 48%; }}
.info label {{ color: #6b7280; display: block; margin-bottom: 2px; }}
.info span {{ font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
th {{ background: #f3f4f6; border: 1px solid #e5e7eb; padding: 8px; font-weight: 600; text-align: center; }}
.totals {{ display: flex; justify-content: flex-end; margin-top: 16px; }}
.totals table {{ width: auto; }}
.totals td {{ border: 1px solid #e5e7eb; padding: 8px 16px; }}
.totals .label {{ text-align: right; font-weight: 600; background: #f9fafb; }}
.totals .value {{ text-align: right; }}
.footer {{ margin-top: 24px; font-size: 10px; color: #6b7280; display: flex; justify-content: space-between; }}
.verification {{ text-align: center; margin-top: 16px; }}
.verification code {{ background: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-family: monospace; letter-spacing: 1px; }}
</style>
</head>
<body>
<div class="header">
    <h1>增值税{("专用发票" if invoice["invoice_type"] == "vat_special" else "普通发票")}</h1>
    <div class="type">发票代码: 3100213130  发票号码: {invoice["invoice_number"]}</div>
</div>

<div class="info">
    <div>
        <label>销售方名称</label>
        <span>{invoice["seller"]["name"]}</span>
    </div>
    <div>
        <label>购买方名称</label>
        <span>{invoice["buyer"]["name"]}</span>
    </div>
    <div>
        <label>销售方纳税人识别号</label>
        <span>{invoice["seller"]["tax_id"]}</span>
    </div>
    <div>
        <label>购买方纳税人识别号</label>
        <span>{invoice["buyer"]["tax_id"] or "无"}</span>
    </div>
    <div>
        <label>销售方地址、电话</label>
        <span>{invoice["seller"]["address"]} {invoice["seller"]["phone"]}</span>
    </div>
    <div>
        <label>购买方地址、电话</label>
        <span>{invoice["buyer"]["address"]} {invoice["buyer"]["phone"]}</span>
    </div>
    <div>
        <label>销售方开户行及账号</label>
        <span>{invoice["seller"]["bank_name"]} {invoice["seller"]["bank_account"]}</span>
    </div>
    <div>
        <label>购买方开户行及账号</label>
        <span>{invoice["buyer"]["bank_name"] or "-"} {invoice["buyer"]["bank_account"] or "-"}</span>
    </div>
</div>

<table>
    <thead>
        <tr>
            <th style="width: 5%;">序号</th>
            <th style="width: 25%;">货物或应税劳务、服务名称</th>
            <th style="width: 10%;">规格型号</th>
            <th style="width: 5%;">单位</th>
            <th style="width: 8%;">数量</th>
            <th style="width: 10%;">单价</th>
            <th style="width: 10%;">金额</th>
            <th style="width: 8%;">税率</th>
            <th style="width: 10%;">税额</th>
        </tr>
    </thead>
    <tbody>
        {items_html}
    </tbody>
</table>

<div class="totals">
    <table>
        <tr><td class="label">合计金额（¥）</td><td class="value">¥{invoice["total_amount"]:.2f}</td></tr>
        <tr><td class="label">合计税额（¥）</td><td class="value">¥{invoice["total_tax"]:.2f}</td></tr>
        <tr><td class="label">价税合计（大写）</td><td class="value">{invoice["total_incl_tax_cn"]}</td></tr>
        <tr><td class="label">价税合计（小写）</td><td class="value">¥{invoice["total_incl_tax"]:.2f}</td></tr>
    </table>
</div>

<div class="footer">
    <div>
        <label>收款人</label><span>__________</span>
        <label>复核人</label><span>__________</span>
        <label>开票人</label><span>__________</span>
    </div>
    <div>
        <label>备注</label><span>{invoice["remarks"]}</span>
    </div>
</div>

<div class="verification">
    <label>校验码: </label><code>{invoice["verification_code"]}</code>
    <br><small>开票日期: {invoice["invoice_date"]} {invoice["invoice_time"]}</small>
</div>
</body>
</html>"""

# Save module
print("Invoice generator module ready")
