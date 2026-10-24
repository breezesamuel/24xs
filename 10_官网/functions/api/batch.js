const { checkEntitlement, consumeEntitlement, getCustomer, loadDb, saveDb } = require("../../../lib/entitlements.js");
const fs = require("fs");
const path = require("path");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
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
  if (!customer) {
    return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  if (action === "verify" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { proofs } = body;

    if (!proofs || !Array.isArray(proofs) || proofs.length === 0) {
      return new Response(JSON.stringify({ ok: false, error: "proofs_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    if (proofs.length > 100) {
      return new Response(JSON.stringify({ ok: false, error: "too_many_proofs", message: "单次最多验证100条" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const entitlement = await checkEntitlement({ customerId, action: "verify", cost: proofs.length, requireActive: true });
    if (!entitlement.allowed) {
      return new Response(JSON.stringify({ ok: false, ...entitlement }), { status: entitlement.code || 403, headers: { "Content-Type": "application/json" } });
    }

    const results = [];
    for (const p of proofs) {
      const { proof, data, parent_proof, variant_index } = p;
      let match = false;
      let computed = "";

      if (proof && parent_proof && variant_index) {
        const enc = new TextEncoder();
        const chain = parent_proof + ":variant:" + variant_index;
        const h = await crypto.subtle.digest("SHA-256", enc.encode(chain));
        computed = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
        match = computed === proof;
      } else if (proof && data) {
        const enc = new TextEncoder();
        const h = await crypto.subtle.digest("SHA-256", enc.encode(typeof data === "string" ? data : JSON.stringify(data)));
        computed = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
        match = computed === proof;
      }

      results.push({ proof: proof?.slice(0, 16), match, computed: computed.slice(0, 16) });
    }

    await consumeEntitlement({ customerId, action: "verify", cost: proofs.length, metadata: { batch_size: proofs.length } });

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total: results.length,
        matched: results.filter(r => r.match).length,
        failed: results.filter(r => !r.match).length,
        results
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "export" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { asset_ids, format = "json" } = body;

    if (!asset_ids || !Array.isArray(asset_ids) || asset_ids.length === 0) {
      return new Response(JSON.stringify({ ok: false, error: "asset_ids_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    if (asset_ids.length > 1000) {
      return new Response(JSON.stringify({ ok: false, error: "too_many_assets", message: "单次最多导出1000条" }), { status: 400, headers: { "Content-Type": "application/json" } });
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

  if (action === "stats") {
    const db = loadDb();
    const usage = (db.usage_records || []).filter(r => r.customer_id === customerId);
    const purchases = (db.purchases || []).filter(p => p.customer_id === customerId);

    const actionCounts = {};
    for (const u of usage) {
      actionCounts[u.action] = (actionCounts[u.action] || 0) + 1;
    }

    const dailyUsage = {};
    for (const u of usage) {
      const d = u.date || u.ts?.slice(0, 10);
      if (d) dailyUsage[d] = (dailyUsage[d] || 0) + (u.cost || 1);
    }

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total_api_calls: usage.length,
        total_credits_used: usage.reduce((s, u) => s + (u.cost || 0), 0),
        action_breakdown: actionCounts,
        daily_usage: dailyUsage,
        total_purchases: purchases.length,
        total_spent: purchases.reduce((s, p) => s + (p.amount_cny || 0), 0)
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}