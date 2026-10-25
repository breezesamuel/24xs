// GET /pay/return - PayPal auto-return callback (auto-capture + activate + receipt)
import { PayPalGateway } from "../../lib/_lib/paypal.js";
import { SUBSCRIPTION_PLANS, CURRENCY } from "../../lib/_lib/plans.js";
import { getPending, removePending } from "../../lib/_lib/pending.js";
import { sendReceipt } from "../../lib/_lib/mailer.js";

function html(title, body) {
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>${title}</title>
<style>body{font-family:system-ui,sans-serif;max-width:600px;margin:40px auto;padding:0 16px;line-height:1.6}
.card{border:1px solid #e5e7eb;border-radius:8px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.ok{color:#059669}.err{color:#dc2626}.muted{color:#6b7280;font-size:.9em}
code{background:#f3f4f6;padding:2px 5px;border-radius:3px;font-size:.9em}</style></head>
<body><div class="card">${body}</div></body></html>`;
}

export default async function handler(req, res) {
  const { token: orderId, plan: planQuery, user: userQuery, dry_run } = req.query;
  if (!orderId) return res.status(400).send(html("错误", `<p class="err">缺少订单号 token</p>`));

  const pending = await getPending(orderId);
  let planKey = planQuery || pending?.plan;
  let userId  = userQuery  || pending?.userId || "default_user";

  // Fallback: 从 PayPal 订单的 custom_id 恢复 "plan|userId"
  // （serverless 多实例内存不共享，pending 可能丢失；custom_id 写在订单里，可靠）
  if (!planKey || !SUBSCRIPTION_PLANS[planKey]) {
    const clientId = process.env.PAYPAL_CLIENT_ID;
    const secret   = process.env.PAYPAL_SECRET;
    if (clientId && secret) {
      const gw = new PayPalGateway(clientId, secret);
      const info = await gw.getOrder(orderId);
      if (info.status !== "error" && info.custom_id) {
        const [p, u] = String(info.custom_id).split("|", 2);
        if (p && SUBSCRIPTION_PLANS[p]) planKey = p;
        if (u) userId = u;
      }
    }
  }

  if (!planKey || !SUBSCRIPTION_PLANS[planKey]) {
    return res.status(400).send(html("错误", `
      <p class="err">无法确定订阅计划</p>
      <p class="muted">订单 <code>${orderId}</code> 未登记或 plan 无效。</p>
    `));
  }

  const planData = SUBSCRIPTION_PLANS[planKey];
  const clientId = process.env.PAYPAL_CLIENT_ID;
  const secret   = process.env.PAYPAL_SECRET;
  const isDryRun = dry_run === "1" && process.env.PAY_RETURN_DRY_RUN === "1";

  if (isDryRun) {
    await removePending(orderId);
    return res.send(html("DRY-RUN 成功（未真实收款）", `
      <p class="ok">✅ DRY-RUN：回调→激活→计 KPI 链路验证通过</p>
      <p>订单：<code>${orderId}</code></p>
      <p>计划：<strong>${planKey}</strong> (${planData.name})</p>
      <p>用户：<code>${userId}</code></p>
      <p class="muted">未发生真实扣款；仅验证链路通畅。</p>
    `));
  }

  if (!clientId || !secret) {
    return res.status(500).send(html("错误", `<p class="err">PayPal 凭证未配置</p>`));
  }

  const gw = new PayPalGateway(clientId, secret);
  const cap = await gw.captureOrder(orderId);
  if (cap.status !== "completed") {
    return res.status(400).send(html("捕获失败", `
      <p class="err">PayPal 捕获失败（买家可能未批准或订单已失效）</p>
      <p>订单：<code>${orderId}</code></p>
      <pre class="muted">${JSON.stringify(cap, null, 2)}</pre>
    `));
  }

  const activation = {
    status: "completed",
    subscription: { plan: planKey, user_id: userId, activated_at: new Date().toISOString() },
    payment_price: planData.price,
    kpi_touched: true,
    partner_commission: planKey !== "basic" ? {
      partner_type: "community_owner",
      suggested_commission: Math.round(planData.price * 0.25 * 100) / 100,
      description: `推广${planData.name}, 可获 ${CURRENCY} ${Math.round(planData.price * 0.25 * 100) / 100} 元分佣`,
    } : null,
    message: `订阅支付完成: ${CURRENCY} ${planData.price} 元`,
  };

  await removePending(orderId);

  // 发送邮件回执（非阻塞，不影响回页）
  const amount = cap.capture?.amount || "?";
  const currency = cap.capture?.currency || "USD";
  const receiptR = await sendReceipt({
    orderId,
    plan: planKey,
    planName: planData.name,
    amountUsd: amount,
    amountCny: planData.price,
    payerEmail: cap.capture?.payer_email || null,
    env: cap.env,
  });

  const receiptLine = receiptR.ok
    ? `<p class="ok">📧 收据已发送</p>`
    : `<p class="muted">收据发送失败（${receiptR.info || "未知"}）— 不影响激活</p>`;

  return res.send(html("支付成功 · 订阅已激活", `
    <p class="ok">✅ PayPal 收款成功，订阅已激活</p>
    <p>订单：<code>${orderId}</code></p>
    <p>计划：<strong>${planKey}</strong> (${planData.name})</p>
    <p>金额：<strong>${amount} ${currency}</strong>（约 ${CURRENCY} ${planData.price}）</p>
    <p>用户：<code>${userId}</code></p>
    ${receiptLine}
    <p class="muted">本窗口将自动关闭…（若未关闭可手动关）</p>
    <script>
      (function () {
        var payload = { type: "paypal:completed", order_id: ${JSON.stringify(orderId)},
                        plan: ${JSON.stringify(planKey)}, status: "completed" };
        try { if (window.opener && !window.opener.closed) window.opener.postMessage(payload, "*"); } catch (e) {}
        try {
          if (window.opener && !window.opener.closed) {
            window.opener.focus();
            setTimeout(function () { window.close(); }, 600);
            return;
          }
        } catch (e) {}
        setTimeout(function () { window.location.replace("/"); }, 3000);
      })();
    </script>
  `));
}
