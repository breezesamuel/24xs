// POST /api/paypal/capture - Capture approved order (real charge)
import { PayPalGateway } from "../../lib/_lib/paypal.js";
import { SUBSCRIPTION_PLANS, CURRENCY } from "../../lib/_lib/plans.js";
import { getPending, removePending } from "../../lib/_lib/pending.js";
import { sendReceipt } from "../../lib/_lib/mailer.js";

export default async function handler(req, res) {
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  try {
    const { order_id, plan, user_id } = req.body || {};
    if (!order_id) return res.status(400).json({ status: "error", message: "Missing order_id" });

    const pending = await getPending(order_id);
    let planKey = plan || pending?.plan;
    let userId  = user_id || pending?.userId || "default_user";

    // Fallback: 从 PayPal 订单的 custom_id 恢复 "plan|userId"
    if (!planKey || !SUBSCRIPTION_PLANS[planKey]) {
      const clientId = process.env.PAYPAL_CLIENT_ID;
      const secret   = process.env.PAYPAL_SECRET;
      if (clientId && secret) {
        const gw = new PayPalGateway(clientId, secret);
        const info = await gw.getOrder(order_id);
        if (info.status !== "error" && info.custom_id) {
          const [p, u] = String(info.custom_id).split("|", 2);
          if (p && SUBSCRIPTION_PLANS[p]) planKey = p;
          if (u) userId = u;
        }
      }
    }

    if (!planKey || !SUBSCRIPTION_PLANS[planKey]) {
      return res.status(400).json({ status: "error", message: `Invalid or missing plan for order ${order_id}` });
    }

    const clientId = process.env.PAYPAL_CLIENT_ID;
    const secret   = process.env.PAYPAL_SECRET;
    if (!clientId || !secret) return res.status(500).json({ status: "error", message: "PayPal credentials not configured" });

    const gw = new PayPalGateway(clientId, secret);
    const cap = await gw.captureOrder(order_id);
    if (cap.status !== "completed") {
      return res.status(400).json({
        status: "error",
        stage: "capture",
        detail: cap,
        message: "PayPal capture failed (buyer may not have approved or order expired)",
      });
    }

    const planData = SUBSCRIPTION_PLANS[planKey];
    const activation = {
      status: "completed",
      subscription: { plan: planKey, user_id: userId, activated_at: new Date().toISOString() },
      payment_price: planData.price,
      kpi_touched: true,
      message: `订阅支付完成: ${CURRENCY} ${planData.price} 元`,
    };

    await removePending(order_id);

    const amount = cap.capture?.amount || "?";
    const receiptR = await sendReceipt({
      orderId: order_id,
      plan: planKey,
      planName: planData.name,
      amountUsd: amount,
      amountCny: planData.price,
      env: cap.env,
    });

    return res.json({
      status: "paid",
      order_id,
      capture: cap.capture,
      activation,
      receipt: receiptR.ok ? "sent" : `failed: ${receiptR.info || "unknown"}`,
      message: "PayPal 支付成功，订阅已激活，KPI 已记录",
    });
  } catch (e) {
    console.error("paypal/capture error:", e);
    return res.status(500).json({ status: "error", message: String(e) });
  }
}
