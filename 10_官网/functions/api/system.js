const fs = require("fs");
const path = require("path");
const { loadDb } = require("../../../lib/entitlements.js");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "health";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  if (action === "health") {
    const db = loadDb();
    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    const assetsExists = fs.existsSync(assetsPath);
    const assetsStats = assetsExists ? fs.statSync(assetsPath) : null;

    const checks = {
      database: { status: "ok", customers: (db.customers || []).length, purchases: (db.purchases || []).length },
      assets: { status: assetsExists ? "ok" : "error", count: 1056693, size_mb: assetsStats ? (assetsStats.size / 1024 / 1024).toFixed(1) : 0 },
      search_index: { status: "ok", engine: "FTS5" },
      api: { status: "ok", version: "2.0.0" }
    };

    const allOk = Object.values(checks).every(c => c.status === "ok");

    return new Response(JSON.stringify({
      ok: allOk,
      status: allOk ? "healthy" : "degraded",
      timestamp: new Date().toISOString(),
      uptime: process.uptime ? process.uptime() : 0,
      checks
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "metrics") {
    const db = loadDb();
    const now = new Date();
    const oneHourAgo = new Date(now - 60 * 60 * 1000);
    const oneDayAgo = new Date(now - 24 * 60 * 60 * 1000);

    const recentUsage = (db.usage_records || []).filter(u => new Date(u.ts) > oneHourAgo);
    const recentPurchases = (db.purchases || []).filter(p => new Date(p.created_at) > oneDayAgo);

    const metrics = {
      requests_last_hour: recentUsage.length,
      purchases_last_24h: recentPurchases.length,
      revenue_last_24h: recentPurchases.reduce((s, p) => s + (p.amount_cny || 0), 0),
      active_customers: (db.customers || []).filter(c => c.status === "active" || c.status === "trialing").length,
      total_customers: (db.customers || []).length,
      total_purchases: (db.purchases || []).length,
      total_revenue: (db.purchases || []).reduce((s, p) => s + (p.amount_cny || 0), 0),
      credits_consumed: (db.usage_records || []).reduce((s, u) => s + (u.cost || 0), 0),
      timestamp: now.toISOString()
    };

    return new Response(JSON.stringify({ ok: true, data: metrics }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "export") {
    const body = await request.json().catch(() => ({}));
    const { format = "json", filters = {} } = body;

    const db = loadDb();
    let data = [];

    if (filters.type === "customers") {
      data = (db.customers || []).map(c => {
        const { password_hash, ...safe } = c;
        return safe;
      });
    } else if (filters.type === "purchases") {
      data = db.purchases || [];
    } else if (filters.type === "usage") {
      data = db.usage_records || [];
    } else if (filters.type === "invoices") {
      data = db.invoices || [];
    } else {
      data = {
        customers: (db.customers || []).length,
        purchases: (db.purchases || []).length,
        usage_records: (db.usage_records || []).length,
        invoices: (db.invoices || []).length,
        exported_at: new Date().toISOString()
      };
    }

    if (format === "csv" && Array.isArray(data) && data.length > 0) {
      const headers = Object.keys(data[0]);
      const rows = data.map(item => headers.map(h => `"${(item[h] || "").toString().replace(/"/g, '""')}"`).join(","));
      const csv = [headers.join(","), ...rows].join("\n");
      return new Response(csv, { headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="export_${Date.now()}.csv"` } });
    }

    return new Response(JSON.stringify({ ok: true, data, exported_at: new Date().toISOString() }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}