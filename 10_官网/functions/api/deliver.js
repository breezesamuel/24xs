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

  const entitlement = await checkEntitlement({ customerId, action: "deliver", cost: 1, requireActive: true });
  if (!entitlement.allowed) {
    return new Response(JSON.stringify({ ok: false, ...entitlement }), {
      status: entitlement.code || 403,
      headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const body = await request.json();
    const purchase_id = body.purchase_id || "";
    const txn_id = body.txn_id || "";

    if (!purchase_id || !txn_id) {
      return new Response(JSON.stringify({ ok: false, error: "missing_params" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    await consumeEntitlement({ customerId, action: "deliver", cost: 1, metadata: { purchase_id, txn_id } });

    const downloadUrl = `https://geo-audit-24xs.vercel.app/api/download?purchase=${purchase_id}&txn=${txn_id}&token=${Buffer.from(purchase_id + ":" + txn_id).toString("base64")}`;

    return new Response(JSON.stringify({
      ok: true,
      purchase_id,
      txn_id,
      download_url: downloadUrl,
      expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      status: "ready",
      delivery_method: "download_link",
      note: "下载链接 24 小时有效，单次使用"
    }), { headers: { "Content-Type": "application/json" } });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: "exception" }), { status: 500, headers: { "Content-Type": "application/json" } });
  }
}

export const onRequest = withMiddleware(handler);