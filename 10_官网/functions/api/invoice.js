const { getCustomer, loadDb, saveDb } = require("../../../lib/entitlements.js");
const fs = require("fs");
const path = require("path");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

function generateInvoiceId() {
  const now = new Date();
  return `INV-${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}-${Math.random().toString(36).substr(2,6).toUpperCase()}`;
}

function toChineseUpper(num) {
  const digits = "零壹贰叁肆伍陆柒捌玖";
  const units = ["", "拾", "佰", "仟"];
  const bigUnits = ["", "万", "亿"];
  
  if (num === 0) return "零元整";
  
  let result = "";
  let n = Math.floor(num);
  let unitPos = 0;
  let needZero = false;
  
  while (n > 0) {
    const section = n % 10000;
    if (needZero) result = "零" + result;
    let sectionStr = "";
    let sec = section;
    let secUnitPos = 0;
    while (sec > 0) {
      const d = sec % 10;
      if (d !== 0) {
        sectionStr = digits[d] + units[secUnitPos] + sectionStr;
      } else if (sectionStr && !sectionStr.startsWith("零")) {
        sectionStr = "零" + sectionStr;
      }
      sec = Math.floor(sec / 10);
      secUnitPos++;
    }
    if (sectionStr) {
      result = sectionStr + bigUnits[unitPos] + result;
    }
    needZero = section < 1000 && section > 0;
    n = Math.floor(n / 10000);
    unitPos++;
  }
  
  result = result.replace(/零+/g, "零").replace(/零$/, "");
  return result + "元整";
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "list";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const customer = await getCustomer(customerId);
  if (!customer) {
    return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  const db = loadDb();

  if (action === "list") {
    const invoices = (db.invoices || []).filter(i => i.customer_id === customerId);
    return new Response(JSON.stringify({ ok: true, data: invoices }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "generate" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { purchase_id, amount_cny, type = "增值税普通发票" } = body;

    if (!purchase_id || !amount_cny) {
      return new Response(JSON.stringify({ ok: false, error: "missing_params" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const purchase = (db.purchases || []).find(p => p.purchase_id === purchase_id && p.customer_id === customerId);
    if (!purchase) {
      return new Response(JSON.stringify({ ok: false, error: "purchase_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const taxRate = 0.06;
    const taxAmount = Math.round(amount_cny * taxRate * 100) / 100;
    const totalAmount = Math.round((amount_cny + taxAmount) * 100) / 100;

    const invoice = {
      invoice_id: generateInvoiceId(),
      customer_id: customerId,
      purchase_id,
      type,
      amount_cny: amount_cny,
      tax_cny: taxAmount,
      total_cny: totalAmount,
      amount_chinese: toChineseUpper(totalAmount),
      status: "issued",
      issued_at: new Date().toISOString(),
      buyer_name: customer.company_name || customer.email,
      buyer_tax_id: customer.tax_id || "",
      seller_name: "上海丙大山智能科技有限公司",
      seller_tax_id: "91310104MA1FL2XXXX",
      items: purchase.asset_ids || [],
      pdf_url: `/api/invoice?action=pdf&invoice_id=${generateInvoiceId()}`
    };

    db.invoices.push(invoice);
    saveDb(db);

    return new Response(JSON.stringify({ ok: true, data: invoice }), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  if (action === "pdf") {
    const invoiceId = url.searchParams.get("invoice_id");
    const invoice = (db.invoices || []).find(i => i.invoice_id === invoiceId && i.customer_id === customerId);
    if (!invoice) {
      return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>发票 ${invoice.invoice_id}</title><style>body{font-family:SimSun,sans-serif;padding:40px;max-width:800px;margin:0 auto}h1{text-align:center;color:#333}table{width:100%;border-collapse:collapse;margin:20px 0}td,th{border:1px solid #ddd;padding:8px;text-align:left}.header{display:flex;justify-content:space-between;margin-bottom:20px}.total{font-size:1.2em;font-weight:bold;color:#e74c3c}</style></head><body><div class="header"><div><strong>发票编号：</strong>${invoice.invoice_id}</div><div><strong>开票日期：</strong>${invoice.issued_at.slice(0,10)}</div></div><h1>${invoice.type}</h1><table><tr><th>项目</th><th>金额</th></tr><tr><td>数据资产采购</td><td>¥${invoice.amount_cny.toFixed(2)}</td></tr><tr><td>税额(6%)</td><td>¥${invoice.tax_cny.toFixed(2)}</td></tr><tr><td class="total">价税合计</td><td class="total">¥${invoice.total_cny.toFixed(2)}</td></tr></table><p><strong>大写金额：</strong>${invoice.amount_chinese}</p><hr><p><strong>购买方：</strong>${invoice.buyer_name}</p><p><strong>销售方：</strong>${invoice.seller_name}</p><p><strong>纳税人识别号：</strong>${invoice.seller_tax_id}</p></body></html>`;

    return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}