const { getCustomer, checkEntitlement, loadDb, saveDb } = require("../../../lib/entitlements.js");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const path = url.pathname.replace("/api/portal", "") || "/";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  if (path === "/credits" && request.method === "GET") {
    const customer = await getCustomer(customerId);
    if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

    const pricing = require("fs").existsSync(require("path").resolve(__dirname, "../../../11_数据资产/registry_real_verified/pricing_engine.json"))
      ? JSON.parse(require("fs").readFileSync(require("path").resolve(__dirname, "../../../11_数据资产/registry_real_verified/pricing_engine.json"), "utf8"))
      : { tiers: {} };
    const tierConfig = pricing.tiers?.[customer.tier] || {};

    return new Response(JSON.stringify({
      ok: true,
      data: {
        balance: customer.credit_balance || 0,
        tier: customer.tier,
        included_credits: customer.included_credits || 0,
        used_this_month: customer.used_this_month || 0,
        remaining: Math.max(0, (customer.credit_balance || 0) - (customer.used_this_month || 0)),
        utilization_pct: customer.included_credits ? ((customer.used_this_month || 0) / customer.included_credits * 100).toFixed(1) : 0,
        overage_rate: tierConfig.overage_rate || 0,
        renews_at: customer.renews_at,
        billing_cycle: customer.billing_cycle
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (path === "/usage" && request.method === "GET") {
    const db = loadDb();
    const customer = await getCustomer(customerId);
    if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

    const page = parseInt(url.searchParams.get("page") || "1");
    const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 200);
    const action = url.searchParams.get("action");
    const startDate = url.searchParams.get("start_date");
    const endDate = url.searchParams.get("end_date");

    let records = (db.usage_records || []).filter(r => r.customer_id === customerId);
    if (action) records = records.filter(r => r.action === action);
    if (startDate) records = records.filter(r => r.date >= startDate);
    if (endDate) records = records.filter(r => r.date <= endDate);
    records.sort((a, b) => new Date(b.ts) - new Date(a.ts));

    const total = records.length;
    const start = (page - 1) * limit;
    const data = records.slice(start, start + limit);

    return new Response(JSON.stringify({ ok: true, data, total, page, limit }), { headers: { "Content-Type": "application/json" } });
  }

  if (path === "/purchases" && request.method === "GET") {
    const db = loadDb();
    const customer = await getCustomer(customerId);
    if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

    const page = parseInt(url.searchParams.get("page") || "1");
    const limit = Math.min(parseInt(url.searchParams.get("limit") || "20"), 100);
    let purchases = (db.purchases || []).filter(p => p.customer_id === customerId);
    purchases.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    const total = purchases.length;
    const start = (page - 1) * limit;
    const data = purchases.slice(start, start + limit);

    return new Response(JSON.stringify({ ok: true, data, total, page, limit }), { headers: { "Content-Type": "application/json" } });
  }

  if (path === "/profile" && request.method === "GET") {
    const customer = await getCustomer(customerId);
    if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

    const { password_hash, ...safe } = customer;
    return new Response(JSON.stringify({ ok: true, data: safe }), { headers: { "Content-Type": "application/json" } });
  }

  if (path === "/api-keys" && request.method === "GET") {
    const db = loadDb();
    const keys = (db.api_keys || []).filter(k => k.customer_id === customerId);
    return new Response(JSON.stringify({ ok: true, data: keys }), { headers: { "Content-Type": "application/json" } });
  }

  if (path === "/api-keys" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { name, permissions, rate_limit } = body;
    if (!name) return new Response(JSON.stringify({ ok: false, error: "name_required" }), { status: 400, headers: { "Content-Type": "application/json" } });

    const db = loadDb();
    const keyId = "KEY-" + Date.now().toString(36).toUpperCase() + Math.random().toString(36).substr(2, 4).toUpperCase();
    const rawKey = "sk_live_" + Math.random().toString(36).substr(2, 32);
    const keyHash = require("crypto").createHash("sha256").update(rawKey).digest("hex");

    const newKey = {
      key_id: keyId,
      customer_id: customerId,
      name,
      key_hash: keyHash,
      permissions: permissions || ["read"],
      rate_limit: rate_limit || 60,
      status: "active",
      created_at: new Date().toISOString(),
      last_used_at: null,
      expires_at: null
    };
    db.api_keys.push(newKey);
    saveDb(db);

    return new Response(JSON.stringify({ ok: true, data: { ...newKey, api_key: rawKey } }), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
}