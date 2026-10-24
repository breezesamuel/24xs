const { loadDb, saveDb, getCustomer } = require("../../../lib/entitlements.js");
const fs = require("fs");
const path = require("path");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

function isAdmin(customer) {
  if (!customer) return false;
  const adminEmails = ["admin@24xs.com", "supi24@163.com"];
  if (customer.email && adminEmails.includes(customer.email)) return true;
  if (customer.tier === "admin") return true;
  return false;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "";

  const customerId = extractCustomerId(request);
  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const customer = await getCustomer(customerId);
  if (!isAdmin(customer)) {
    return new Response(JSON.stringify({ ok: false, error: "forbidden", message: "需要管理员权限" }), { status: 403, headers: { "Content-Type": "application/json" } });
  }

  const db = loadDb();

  if (action === "dashboard" || action === "") {
    const totalCustomers = (db.customers || []).length;
    const activeCustomers = (db.customers || []).filter(c => (c.status === "active" || c.status === "trialing")).length;
    const totalRevenue = (db.purchases || []).filter(p => p.status === "completed" || p.status === "success").reduce((sum, p) => sum + (p.amount_cny || 0), 0);
    const totalPurchases = (db.purchases || []).length;
    const totalUsage = (db.usage_records || []).length;
    const creditsUsed = (db.usage_records || []).reduce((sum, r) => sum + (r.cost || 0), 0);

    return new Response(JSON.stringify({
      ok: true,
      dashboard: {
        total_customers: totalCustomers,
        active_customers: activeCustomers,
        total_revenue_cny: Math.round(totalRevenue * 100) / 100,
        total_purchases: totalPurchases,
        total_api_calls: totalUsage,
        credits_used: creditsUsed,
        last_updated: new Date().toISOString()
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "customers") {
    const page = parseInt(url.searchParams.get("page") || "1");
    const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 200);
    let customers = [...(db.customers || [])];
    const tier = url.searchParams.get("tier");
    const status = url.searchParams.get("status");
    if (tier) customers = customers.filter(c => c.tier === tier);
    if (status) customers = customers.filter(c => c.status === status);

    const total = customers.length;
    const start = (page - 1) * limit;
    const data = customers.slice(start, start + limit).map(c => {
      const { password_hash, ...safe } = c;
      return safe;
    });

    return new Response(JSON.stringify({ ok: true, data, total, page, limit }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "purchases") {
    const purchases = [...(db.purchases || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return new Response(JSON.stringify({ ok: true, data: purchases }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "usage") {
    const usage = [...(db.usage_records || [])].sort((a, b) => new Date(b.ts) - new Date(a.ts)).slice(0, 100);
    return new Response(JSON.stringify({ ok: true, data: usage }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "health") {
    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    const stats = fs.existsSync(assetsPath) ? fs.statSync(assetsPath) : null;
    return new Response(JSON.stringify({
      ok: true,
      status: "healthy",
      version: "2.0.0",
      uptime: process.uptime ? process.uptime() : 0,
      assets_count: stats ? 1056693 : 0,
      storage_mb: stats ? (stats.size / 1024 / 1024).toFixed(1) : 0,
      timestamp: new Date().toISOString()
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}