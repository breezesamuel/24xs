const { checkEntitlement } = require("../../../lib/entitlements.js");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized", message: "需要登录" }), {
      status: 401,
      headers: { "Content-Type": "application/json" }
    });
  }

  const entitlement = await checkEntitlement({ customerId, action: "assets_view", cost: 0, requireActive: true });
  if (!entitlement.allowed) {
    return new Response(JSON.stringify({ ok: false, ...entitlement }), {
      status: entitlement.code || 403,
      headers: { "Content-Type": "application/json" }
    });
  }

  const url = new URL(request.url);
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "100"), 500);

  const manifest = {
    total: 1056693,
    format: "jsonl",
    path: "11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl",
    license: "internal-use-license-v1",
    note: "1,056,693 真实可验证源资产，每条含 SHA256 链式证明"
  };

  return new Response(JSON.stringify({
    ok: true,
    ...manifest,
    offset: parseInt(url.searchParams.get("offset") || "0"),
    limit
  }), {
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });
}