// GET /api/paypal/status?order_id=xxx —— 只读查单，供客户页"零操作"自动确认到账
// 前端轮询本接口：COMPLETED 即视为付款成功（不需客户手动刷新或点任何按钮）。
// 注意路径：_lib 在 api/ 的同级目录，故用 ../_lib/paypal.js
import { PayPalGateway } from "../../lib/_lib/paypal.js";

export default async function handler(req, res) {
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

  const orderId = String(req.query.order_id || "").trim();
  if (!orderId) return res.status(400).json({ status: "error", message: "missing order_id" });

  const clientId = process.env.PAYPAL_CLIENT_ID;
  const secret = process.env.PAYPAL_SECRET;
  if (!clientId || !secret) {
    return res.status(500).json({ status: "error", message: "PayPal credentials not configured" });
  }

  try {
    const gw = new PayPalGateway(clientId, secret);
    const r = await gw.getOrder(orderId);
    if (r.status === "error") {
      return res.status(404).json({ status: "error", order_id: orderId, detail: r.error });
    }
    return res.json({
      status: r.status,
      order_id: r.order_id || orderId,
      completed: !!r.completed,
      amount: r.capture?.amount || null,
      currency: r.capture?.currency || null,
      capture_id: r.capture?.id || null,
    });
  } catch (e) {
    return res.status(500).json({ status: "error", message: String(e) });
  }
}
