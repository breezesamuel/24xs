const { getCustomer, loadDb, saveDb } = require("../../../lib/entitlements.js");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

const TEMPLATES = {
  welcome: {
    subject: "欢迎使用丙大山数字资产平台",
    body: (name) => `尊敬的 ${name}，欢迎加入丙大山数字资产平台！您的账户已开通，可以开始探索海量数据资产。`
  },
  purchase_success: {
    subject: "购买成功确认",
    body: (orderId) => `您的订单 ${orderId} 已支付成功，相关资产已交付到您的账户。`
  },
  subscription_renewed: {
    subject: "订阅续费成功",
    body: (tier, date) => `您的 ${tier} 订阅已续费成功，下次续费日期：${date}。`
  },
  subscription_expiring: {
    subject: "订阅即将到期提醒",
    body: (days) => `您的订阅将在 ${days} 天后到期，请及时续费以保持服务不中断。`
  },
  credits_low: {
    subject: "积分余额不足提醒",
    body: (remaining) => `您的积分余额仅剩 ${remaining}，建议及时充值或升级订阅。`
  },
  password_changed: {
    subject: "密码修改成功",
    body: () => `您的账户密码已修改。如非本人操作，请立即联系客服。`
  },
  api_key_created: {
    subject: "API Key 创建成功",
    body: (keyName) => `API Key "${keyName}" 已创建，请妥善保管。`
  },
  invoice_issued: {
    subject: "发票已开具",
    body: (invoiceId) => `您的发票 ${invoiceId} 已开具，可在账户中心下载。`
  }
};

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "list";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const customer = await getCustomer(customerId);
  if (!customer) {
    return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  const db = loadDb();

  if (action === "list") {
    const notifications = (db.notifications || []).filter(n => n.customer_id === customerId);
    notifications.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return new Response(JSON.stringify({ ok: true, data: notifications }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "send" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { template, data = {}, email } = body;

    if (!template || !TEMPLATES[template]) {
      return new Response(JSON.stringify({ ok: false, error: "invalid_template" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const t = TEMPLATES[template];
    const notification = {
      id: "N-" + Date.now().toString(36) + Math.random().toString(36).substr(2, 4),
      customer_id: customerId,
      type: template,
      subject: t.subject,
      body: t.body(data),
      email: email || customer.email,
      status: "sent",
      created_at: new Date().toISOString(),
      read: false
    };

    if (!db.notifications) db.notifications = [];
    db.notifications.push(notification);
    saveDb(db);

    return new Response(JSON.stringify({ ok: true, data: notification }), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  if (action === "mark_read" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { notification_ids } = body;

    if (!notification_ids || !Array.isArray(notification_ids)) {
      return new Response(JSON.stringify({ ok: false, error: "notification_ids_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const notifications = (db.notifications || []).filter(n => n.customer_id === customerId);
    for (const n of notifications) {
      if (notification_ids.includes(n.id)) {
        n.read = true;
        n.read_at = new Date().toISOString();
      }
    }
    saveDb(db);

    return new Response(JSON.stringify({ ok: true, data: { marked: notification_ids.length } }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "templates") {
    return new Response(JSON.stringify({
      ok: true,
      data: Object.keys(TEMPLATES).map(k => ({
        key: k,
        subject: TEMPLATES[k].subject,
        description: TEMPLATES[k].body.toString().slice(0, 50) + "..."
      }))
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}