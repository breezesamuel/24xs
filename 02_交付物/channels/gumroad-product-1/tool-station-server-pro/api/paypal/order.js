// POST /api/paypal/order - Create PayPal order (no charge)
// CJS (Vercel type=commonjs; ESM import 会 FUNCTION_INVOCATION_FAILED)
const { PayPalGateway, cnyToUsd } = require("../../lib/_lib/paypal.js");
const { SUBSCRIPTION_PLANS } = require("../../lib/_lib/plans.js");
const { registerPending } = require("../../lib/_lib/pending.js");

async function handler(req, res) {
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  try {
    const { plan = "professional", userId = "web_visitor" } = req.body || {};
    const planData = SUBSCRIPTION_PLANS[plan];
    if (!planData) return res.status(400).json({ status: "error", message: `Invalid plan: ${plan}` });

    const amountUsd = cnyToUsd(planData.price);
    const clientId = process.env.PAYPAL_CLIENT_ID;
    const secret = process.env.PAYPAL_SECRET;
    // fail-closed: PayPal 未配置 → 503 (服务未就绪), 而非 500 (服务器崩溃)
    if (!clientId || !secret) return res.status(503).json({ status: "unavailable", error: "paypal_not_configured", message: "PayPal 收款网关未配置 (主收款走支付宝 /api/pay)" });

    const gw = new PayPalGateway(clientId, secret);
    const publicBase = process.env.PUBLIC_BASE || `https://${req.headers.host}`;
    const returnUrl = `${publicBase}/pay/return?plan=${plan}&user=${encodeURIComponent(userId)}`;
    const cancelUrl = `${publicBase}/pay/cancel`;

    const order = await gw.createOrder({
      amountUsd,
      currency: "USD",
      description: `AI 提效平台 · ${planData.name}`,
      customId: `${plan}|${userId}`.slice(0, 127),
      referenceId: plan,
      returnUrl,
      cancelUrl,
    });

    if (order.status !== "created") {
      return res.status(400).json({ status: "error", stage: "create_order", detail: order, message: "PayPal create order failed" });
    }

    registerPending(order.order_id, { plan, userId, returnUrl });

    return res.json({
      status: "created",
      order_id: order.order_id,
      approve_url: order.approve_url,
      plan,
      plan_name: planData.name,
      price_cny: planData.price,
      amount_usd: order.amount,
      env: order.env,
      next: "User approves on PayPal, then browser auto-returns to /pay/return for auto-capture and subscription activation.",
    });
  } catch (e) {
    console.error("paypal/order error:", e);
    return res.status(500).json({ status: "error", message: String(e) });
  }
}

module.exports = handler;
module.exports.default = handler;