const fs = require("fs");
const path = require("path");
const { getCustomer, loadDb, saveDb, checkEntitlement, consumeEntitlement } = require("../../../lib/entitlements.js");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "assets";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const customer = await getCustomer(customerId);
  if (!customer) {
    return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  const db = loadDb();

  if (action === "assets") {
    const body = await request.json().catch(() => ({}));
    const { asset_ids, format = "json" } = body;

    if (!asset_ids || !Array.isArray(asset_ids) || asset_ids.length === 0) {
      return new Response(JSON.stringify({ ok: false, error: "asset_ids_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    if (asset_ids.length > 1000) {
      return new Response(JSON.stringify({ ok: false, error: "too_many_assets" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const entitlement = await checkEntitlement({ customerId, action: "deliver", cost: asset_ids.length, requireActive: true });
    if (!entitlement.allowed) {
      return new Response(JSON.stringify({ ok: false, ...entitlement }), { status: entitlement.code || 403, headers: { "Content-Type": "application/json" } });
    }

    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    const assets = [];
    const idSet = new Set(asset_ids);

    if (fs.existsSync(assetsPath)) {
      const content = fs.readFileSync(assetsPath, "utf8");
      const lines = content.split("\n");
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const asset = JSON.parse(line);
          if (idSet.has(asset.asset_id)) {
            assets.push(asset);
            if (assets.length >= asset_ids.length) break;
          }
        } catch (e) {}
      }
    }

    await consumeEntitlement({ customerId, action: "deliver", cost: asset_ids.length, metadata: { export_count: assets.length, format } });

    if (format === "csv") {
      const headers = ["asset_id", "type", "name", "source", "proof", "price_cny_ref", "deliverable"];
      const rows = assets.map(a => headers.map(h => `"${(a[h] || "").toString().replace(/"/g, '""')}"`).join(","));
      const csv = [headers.join(","), ...rows].join("\n");
      return new Response(csv, { headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="export_${Date.now()}.csv"` } });
    }

    return new Response(JSON.stringify({ ok: true, data: assets, exported_at: new Date().toISOString() }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "usage") {
    const usage = (db.usage_records || []).filter(u => u.customer_id === customerId);
    usage.sort((a, b) => new Date(b.ts) - new Date(a.ts));

    return new Response(JSON.stringify({ ok: true, data: usage }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "purchases") {
    const purchases = (db.purchases || []).filter(p => p.customer_id === customerId);
    purchases.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    return new Response(JSON.stringify({ ok: true, data: purchases }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "invoices") {
    const invoices = (db.invoices || []).filter(i => i.customer_id === customerId);
    invoices.sort((a, b) => new Date(b.issued_at) - new Date(a.issued_at));

    return new Response(JSON.stringify({ ok: true, data: invoices }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}