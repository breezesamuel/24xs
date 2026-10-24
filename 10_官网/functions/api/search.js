const { checkEntitlement, consumeEntitlement } = require("../../../lib/entitlements.js");
const { withMiddleware } = require("../../../lib/middleware.js");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

async function handler(context) {
  const { request } = context;
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized", message: "需要登录" }), {
      status: 401,
      headers: { "Content-Type": "application/json" }
    });
  }

  const entitlement = await checkEntitlement({ customerId, action: "search", cost: 1, requireActive: true });
  if (!entitlement.allowed) {
    return new Response(JSON.stringify({ ok: false, ...entitlement }), {
      status: entitlement.code || 403,
      headers: { "Content-Type": "application/json" }
    });
  }

  const url = new URL(request.url);
  const q = url.searchParams.get("q") || "";
  const type = url.searchParams.get("type") || "";
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 200);

  if (!q && !type) {
    return new Response(JSON.stringify({ ok: false, error: "query_required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" }
    });
  }

  await consumeEntitlement({ customerId, action: "search", cost: 1, metadata: { query: q, type } });

  return new Response(JSON.stringify({
    ok: true,
    query: { q, type, limit },
    note: "Production: connect to Cloudflare D1 or external search service. Local: assets_search.db FTS5",
    example: "SELECT asset_id,name,type,tags FROM assets_fts WHERE assets_fts MATCH ? LIMIT ?"
  }), { headers: { "Content-Type": "application/json; charset=utf-8" } });
}

export const onRequest = withMiddleware(handler);