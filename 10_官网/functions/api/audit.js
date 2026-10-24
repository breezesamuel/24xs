const { getCustomer, loadDb, saveDb } = require("../../../lib/entitlements.js");

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
    const isAdm = isAdmin(customer);
    const logs = (db.audit_logs || []).filter(l => isAdm || l.customer_id === customerId);
    logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    const page = parseInt(url.searchParams.get("page") || "1");
    const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 200);
    const start = (page - 1) * limit;
    const data = logs.slice(start, start + limit);

    return new Response(JSON.stringify({ ok: true, data, total: logs.length, page, limit }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "log" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { action: logAction, resource, details, ip_address } = body;

    if (!logAction || !resource) {
      return new Response(JSON.stringify({ ok: false, error: "missing_params" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const log = {
      id: "LOG-" + Date.now().toString(36) + Math.random().toString(36).substr(2, 4),
      customer_id: customerId,
      action: logAction,
      resource,
      details: details || {},
      ip_address: ip_address || request.headers.get("x-forwarded-for") || "unknown",
      user_agent: request.headers.get("user-agent") || "unknown",
      timestamp: new Date().toISOString()
    };

    if (!db.audit_logs) db.audit_logs = [];
    db.audit_logs.push(log);
    if (db.audit_logs.length > 100000) db.audit_logs = db.audit_logs.slice(-50000);
    saveDb(db);

    return new Response(JSON.stringify({ ok: true, data: log }), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  if (action === "stats") {
    const isAdm = isAdmin(customer);
    const logs = (db.audit_logs || []).filter(l => isAdm || l.customer_id === customerId);

    const actionCounts = {};
    const resourceCounts = {};
    for (const l of logs) {
      actionCounts[l.action] = (actionCounts[l.action] || 0) + 1;
      resourceCounts[l.resource] = (resourceCounts[l.resource] || 0) + 1;
    }

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total_logs: logs.length,
        action_breakdown: actionCounts,
        resource_breakdown: resourceCounts,
        recent_logs: logs.slice(0, 10)
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}