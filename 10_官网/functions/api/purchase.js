const { checkEntitlement } = require("../../../lib/entitlements.js");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  try {
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ ok: false, error: "method_not_allowed" }), { status: 405, headers: { "Content-Type": "application/json" } });
    }

    const customerId = extractCustomerId(request);
    if (!customerId) {
      return new Response(JSON.stringify({ ok: false, error: "unauthorized", message: "需要登录" }), {
        status: 401,
        headers: { "Content-Type": "application/json" }
      });
    }

    const entitlement = await checkEntitlement({ customerId, action: "purchase", cost: 0, requireActive: true });
    if (!entitlement.allowed) {
      return new Response(JSON.stringify({ ok: false, ...entitlement }), {
        status: entitlement.code || 403,
        headers: { "Content-Type": "application/json" }
      });
    }

    const body = await request.json();
    const asset_id = body.asset_id || "";
    const amount_cny = body.amount_cny || 0;

    if (!asset_id) {
      return new Response(JSON.stringify({ ok: false, error: "missing_asset_id" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const checkout_url = `https://app.moltspay.com/checkout?amount=${amount_cny}&currency=CNY&desc=数字资产:${asset_id}&custom=${encodeURIComponent(asset_id)}`;
    const payment_url = checkout_url;

    return new Response(JSON.stringify({
      ok: true,
      asset_id,
      amount_cny,
      checkout_url,
      payment_url,
      note: "支付网关待完整配置（现为预发地址）。收到款项后自动交付资产文件。"
    }), {
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: "exception" }), { status: 500, headers: { "Content-Type": "application/json" } });
  }
}