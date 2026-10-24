const fs = require("fs");
const path = require("path");
const { checkEntitlement, consumeEntitlement } = require("../../../lib/entitlements.js");
const { withMiddleware } = require("../../../lib/middleware.js");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

async function handler(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "search";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const entitlement = await checkEntitlement({ customerId, action: "search", cost: 1, requireActive: true });
  if (!entitlement.allowed) {
    return new Response(JSON.stringify({ ok: false, ...entitlement }), { status: entitlement.code || 403, headers: { "Content-Type": "application/json" } });
  }

  const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
  if (!fs.existsSync(assetsPath)) {
    return new Response(JSON.stringify({ ok: false, error: "assets_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  if (action === "search") {
    const q = url.searchParams.get("q") || "";
    const type = url.searchParams.get("type") || "";
    const minPrice = parseFloat(url.searchParams.get("min_price") || "0");
    const maxPrice = parseFloat(url.searchParams.get("max_price") || "999999");
    const tags = url.searchParams.get("tags") || "";
    const sortBy = url.searchParams.get("sort") || "relevance";
    const page = parseInt(url.searchParams.get("page") || "1");
    const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 200);

    if (!q && !type && !tags) {
      return new Response(JSON.stringify({ ok: false, error: "query_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const results = [];
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");
    const qLower = q.toLowerCase();
    const tagList = tags.split(",").map(t => t.trim().toLowerCase()).filter(t => t);

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const asset = JSON.parse(line);

        if (type && asset.type !== type) continue;
        if (asset.price_cny_ref < minPrice || asset.price_cny_ref > maxPrice) continue;

        if (tagList.length > 0) {
          const assetTags = (asset.tags || []).map(t => t.toLowerCase());
          if (!tagList.some(t => assetTags.includes(t))) continue;
        }

        if (q) {
          const nameMatch = (asset.name || "").toLowerCase().includes(qLower);
          const typeMatch = (asset.type || "").toLowerCase().includes(qLower);
          const tagMatch = (asset.tags || []).some(t => t.toLowerCase().includes(qLower));
          const descMatch = (asset.deliverable || "").toLowerCase().includes(qLower);

          if (!nameMatch && !typeMatch && !tagMatch && !descMatch) continue;

          let score = 0;
          if (nameMatch) score += 10;
          if (typeMatch) score += 5;
          if (tagMatch) score += 3;
          if (descMatch) score += 1;

          results.push({ ...asset, _score: score });
        } else {
          results.push({ ...asset, _score: 0 });
        }

        if (results.length >= 1000) break;
      } catch (e) {}
    }

    if (sortBy === "price_asc") results.sort((a, b) => (a.price_cny_ref || 0) - (b.price_cny_ref || 0));
    else if (sortBy === "price_desc") results.sort((a, b) => (b.price_cny_ref || 0) - (a.price_cny_ref || 0));
    else if (sortBy === "name") results.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    else results.sort((a, b) => b._score - a._score);

    const total = results.length;
    const start = (page - 1) * limit;
    const data = results.slice(start, start + limit).map(r => {
      const { _score, ...asset } = r;
      return asset;
    });

    await consumeEntitlement({ customerId, action: "search", cost: 1, metadata: { query: q, type, results: total } });

    return new Response(JSON.stringify({
      ok: true,
      data,
      total,
      page,
      limit,
      has_more: start + limit < total
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "detail") {
    const assetId = url.searchParams.get("asset_id");
    if (!assetId) {
      return new Response(JSON.stringify({ ok: false, error: "asset_id_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const asset = JSON.parse(line);
        if (asset.asset_id === assetId) {
          return new Response(JSON.stringify({ ok: true, data: asset }), { headers: { "Content-Type": "application/json" } });
        }
      } catch (e) {}
    }

    return new Response(JSON.stringify({ ok: false, error: "asset_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}

export const onRequest = withMiddleware(handler);