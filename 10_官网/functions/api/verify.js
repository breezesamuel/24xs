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

  const entitlement = await checkEntitlement({ customerId, action: "verify", cost: 1, requireActive: true });
  if (!entitlement.allowed) {
    return new Response(JSON.stringify({ ok: false, ...entitlement }), {
      status: entitlement.code || 403,
      headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const body = await request.json();
    const proof = body.proof || "";
    const parent_proof = body.parent_proof || "";
    const variant_index = body.variant_index || 0;

    let result;
    if (proof && parent_proof && variant_index) {
      const enc = new TextEncoder();
      const chain = parent_proof + ":variant:" + variant_index;
      const h = await crypto.subtle.digest("SHA-256", enc.encode(chain));
      const hex = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
      result = { ok: true, match: hex === proof, computed: hex, type: "chain" };
    } else if (proof && body.data) {
      const data = body.data;
      const enc = new TextEncoder();
      const h = await crypto.subtle.digest("SHA-256", enc.encode(typeof data === "string" ? data : JSON.stringify(data)));
      const hex = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
      result = { ok: true, match: hex === proof, computed: hex, type: "direct" };
    } else {
      return new Response(JSON.stringify({ ok: false, error: "bad_request" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    await consumeEntitlement({ customerId, action: "verify", cost: 1, metadata: { proof: proof.slice(0, 16) } });
    return new Response(JSON.stringify(result), { headers: { "Content-Type": "application/json" } });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: "exception" }), { status: 500, headers: { "Content-Type": "application/json" } });
  }
}

export const onRequest = withMiddleware(handler);