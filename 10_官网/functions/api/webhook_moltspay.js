const { saveCustomer, getCustomer, loadDb, saveDb, addMonths } = require("../../../lib/entitlements.js");

export async function onRequest(context) {
  try {
    const sig = context.request.headers.get("X-X402-Signature");
    const ts = context.request.headers.get("X-X402-Timestamp");
    const rawBody = await context.request.text();

    if (!sig || !ts) return new Response("Missing signature headers", { status: 400 });

    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parseInt(ts)) > 300) return new Response("Timestamp expired", { status: 400 });

    const secret = context.env.MOLTSPAY_WEBHOOK_SECRET;
    if (!secret) return new Response("Server config error", { status: 503 });

    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
    const msg = encoder.encode(ts + "." + rawBody);
    const expectedSig = await crypto.subtle.sign("HMAC", key, msg);
    const expectedHex = Array.from(new Uint8Array(expectedSig)).map(b => b.toString(16).padStart(2, "0")).join("");

    if (expectedHex !== sig) return new Response("Invalid signature", { status: 401 });

    const event = JSON.parse(rawBody);
    const eventId = event.id;
    const eventType = event.type;

    // Idempotency: track processed event IDs in KV/D1 (simplified here with in-memory check via file)
    const db = loadDb();
    if (!db.processed_webhooks) db.processed_webhooks = [];
    if (db.processed_webhooks.includes(eventId)) return new Response("OK (duplicate)", { status: 200 });
    db.processed_webhooks.push(eventId);
    if (db.processed_webhooks.length > 10000) db.processed_webhooks = db.processed_webhooks.slice(-5000);
    saveDb(db);

    const customerId = event.metadata?.customer_id || event.customer || "";
    if (!customerId) {
      console.log("Webhook: no customer_id in event", eventType);
      return new Response("OK", { status: 200 });
    }

    const customer = await getCustomer(customerId);
    if (!customer) {
      console.log("Webhook: customer not found", customerId);
      return new Response("OK", { status: 200 });
    }

    switch (eventType) {
      case "payment.succeeded":
      case "charge.succeeded": {
        const isSubscription = event.metadata?.subscription === "true" || event.subscription_id;
        const amount = event.amount_cny || event.amount || 0;
        const tier = event.metadata?.tier || customer.tier;
        const billing_cycle = event.metadata?.billing_cycle || customer.billing_cycle || "monthly";
        const renewsAt = addMonths(new Date().toISOString(), billing_cycle === "monthly" ? 1 : 12);

        await saveCustomer({
          ...customer,
          tier,
          billing_cycle,
          status: "active",
          included_credits: event.metadata?.included_credits || customer.included_credits,
          credit_balance: (customer.credit_balance || 0) + (event.metadata?.included_credits || 0),
          used_this_month: isSubscription ? 0 : customer.used_this_month,
          renews_at: isSubscription ? renewsAt : customer.renews_at,
          ends_at: isSubscription ? renewsAt : customer.ends_at,
          cancel_at_period_end: false,
          trial_ends_at: null,
          total_spent: (customer.total_spent || 0) + amount,
          last_payment_at: new Date().toISOString(),
          last_payment_amount: amount,
          subscription_id: event.subscription_id || customer.subscription_id
        });

        if (!isSubscription) {
          const assetId = event.metadata?.asset_id || event.custom || "";
          if (assetId) console.log("One-time purchase confirmed:", { assetId, amount, customerId });
        }
        break;
      }

      case "subscription.created":
      case "subscription.activated": {
        const tier = event.metadata?.tier || customer.tier;
        const billing_cycle = event.metadata?.billing_cycle || customer.billing_cycle || "monthly";
        const included = event.metadata?.included_credits || 0;
        const renewsAt = addMonths(new Date().toISOString(), billing_cycle === "monthly" ? 1 : 12);

        await saveCustomer({
          ...customer,
          tier,
          billing_cycle,
          status: "active",
          included_credits: included,
          credit_balance: included,
          used_this_month: 0,
          renews_at: renewsAt,
          ends_at: renewsAt,
          cancel_at_period_end: false,
          trial_ends_at: event.trial_end ? new Date(event.trial_end * 1000).toISOString() : null,
          subscription_id: event.subscription_id || event.id
        });
        break;
      }

      case "subscription.renewed":
      case "subscription.payment_succeeded": {
        const billing_cycle = customer.billing_cycle || "monthly";
        const renewsAt = addMonths(customer.renews_at || new Date().toISOString(), billing_cycle === "monthly" ? 1 : 12);
        const included = event.metadata?.included_credits || customer.included_credits;

        await saveCustomer({
          ...customer,
          status: "active",
          included_credits: included,
          credit_balance: included,
          used_this_month: 0,
          renews_at: renewsAt,
          ends_at: renewsAt,
          cancel_at_period_end: false,
          past_due_since: null
        });
        break;
      }

      case "subscription.payment_failed": {
        await saveCustomer({
          ...customer,
          status: "past_due",
          past_due_since: new Date().toISOString(),
          cancel_at_period_end: false
        });
        break;
      }

      case "subscription.canceled": {
        const immediate = event.metadata?.immediate === "true";
        const endsAt = immediate ? new Date().toISOString() : (customer.renews_at || customer.ends_at);
        await saveCustomer({
          ...customer,
          status: immediate ? "canceled" : "active",
          cancel_at_period_end: !immediate,
          ends_at: endsAt
        });
        break;
      }

      case "subscription.expired": {
        await saveCustomer({
          ...customer,
          status: "expired",
          ends_at: new Date().toISOString()
        });
        break;
      }

      case "subscription.trial_ending": {
        // 3 days before trial ends - could send notification
        console.log("Trial ending soon for", customerId);
        break;
      }
    }

    return new Response("OK", { status: 200 });
  } catch (e) {
    console.error("Webhook error:", e);
    return new Response("Internal error", { status: 500 });
  }
}