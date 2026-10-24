const { loadDb, saveDb } = require("../../../lib/entitlements.js");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "list";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const db = loadDb();

  if (action === "list") {
    const webhooks = (db.webhook_queue || []).filter(w => w.customer_id === customerId);
    webhooks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return new Response(JSON.stringify({ ok: true, data: webhooks }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "retry" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { webhook_id } = body;

    if (!webhook_id) {
      return new Response(JSON.stringify({ ok: false, error: "webhook_id_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const webhook = (db.webhook_queue || []).find(w => w.id === webhook_id && w.customer_id === customerId);
    if (!webhook) {
      return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    if (webhook.status === "delivered") {
      return new Response(JSON.stringify({ ok: false, error: "already_delivered" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    webhook.status = "pending";
    webhook.retry_count = (webhook.retry_count || 0) + 1;
    webhook.next_retry_at = new Date(Date.now() + 60000).toISOString();
    webhook.last_error = null;
    webhook.updated_at = new Date().toISOString();

    saveDb(db);

    return new Response(JSON.stringify({ ok: true, data: webhook }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "stats") {
    const webhooks = (db.webhook_queue || []).filter(w => w.customer_id === customerId);
    const stats = {
      total: webhooks.length,
      pending: webhooks.filter(w => w.status === "pending").length,
      delivered: webhooks.filter(w => w.status === "delivered").length,
      failed: webhooks.filter(w => w.status === "failed").length,
      dead_letter: webhooks.filter(w => w.status === "dead_letter").length,
      avg_retries: webhooks.length > 0 ? (webhooks.reduce((s, w) => s + (w.retry_count || 0), 0) / webhooks.length).toFixed(2) : 0
    };

    return new Response(JSON.stringify({ ok: true, data: stats }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}