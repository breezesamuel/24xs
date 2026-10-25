// POST /api/paypal/order - Create PayPal order (no charge)
import { PayPalGateway, cnyToUsd } from "../../lib/_lib/paypal.js";
import { SUBSCRIPTION_PLANS } from "../../lib/_lib/plans.js";
import { registerPending } from "../../lib/_lib/pending.js";

export default async function handler(req, res) {
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  try {
    const { plan = "professional", userId = "web_visitor" } = req.body || {};
    const planData = SUBSCRIPTION_PLANS[plan];
    if (!planData) return res.status(400).json({ status: "error", message: `Invalid plan: ${plan}` });

    const amountUsd = cnyToUsd(planData.price);
    const clientId = process.env.PAYPAL_CLIENT_ID;
    const secret = process.env.PAYPAL_SECRET;
    if (!clientId || !secret) return res.status(500).json({ status: "error", message: "PayPal credentials not configured" });

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