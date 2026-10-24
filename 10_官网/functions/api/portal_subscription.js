const { getCustomer, saveCustomer, loadDb, saveDb, addMonths, addDays } = require("../../../lib/entitlements.js");
const PRICING_PATH = require("path").resolve(__dirname, "../../../11_数据资产/registry_real_verified/pricing_engine.json");
const fs = require("fs");

function loadPricing() {
  try { return JSON.parse(fs.readFileSync(PRICING_PATH, "utf8")); } catch (e) { return { tiers: {} }; }
}

function getTierConfig(tier) {
  return loadPricing().tiers?.[tier] || null;
}

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

async function handleGet(request) {
  const customerId = extractCustomerId(request);
  if (!customerId) return new Response(JSON.stringify({ ok: false, error: "missing_customer_id" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const customer = await getCustomer(customerId);
  if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

  const tierConfig = getTierConfig(customer.tier);
  const now = new Date();
  const renewsAt = customer.renews_at ? new Date(customer.renews_at) : null;
  const endsAt = customer.ends_at ? new Date(customer.ends_at) : null;

  return new Response(JSON.stringify({
    ok: true,
    data: {
      customer_id: customer.customer_id,
      tier: customer.tier,
      status: customer.status || "inactive",
      billing_cycle: customer.billing_cycle || "monthly",
      included_credits: customer.included_credits || 0,
      used_this_month: customer.used_this_month || 0,
      credit_balance: customer.credit_balance || 0,
      renews_at: customer.renews_at || null,
      ends_at: customer.ends_at || null,
      cancel_at_period_end: customer.cancel_at_period_end || false,
      trial_ends_at: customer.trial_ends_at || null,
      is_active: (customer.status || "inactive") === "active" || (customer.status || "inactive") === "trialing",
      is_past_due: (customer.status || "inactive") === "past_due",
      days_until_renewal: renewsAt ? Math.ceil((renewsAt - now) / (1000 * 60 * 60 * 24)) : null,
      days_until_expiry: endsAt ? Math.ceil((endsAt - now) / (1000 * 60 * 60 * 24)) : null,
      tier_limits: tierConfig ? {
        included_credits: tierConfig.included_credits,
        overage_rate: tierConfig.overage_rate,
        features: tierConfig.features
      } : null
    }
  }), { status: 200, headers: { "Content-Type": "application/json" } });
}

async function handlePost(request) {
  const customerId = extractCustomerId(request);
  if (!customerId) return new Response(JSON.stringify({ ok: false, error: "missing_customer_id" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const body = await request.json().catch(() => ({}));
  const { tier, billing_cycle } = body;
  const validTiers = ["starter", "professional", "enterprise"];
  const validCycles = ["monthly", "yearly"];

  if (!validTiers.includes(tier)) return new Response(JSON.stringify({ ok: false, error: "invalid_tier" }), { status: 400, headers: { "Content-Type": "application/json" } });
  if (!validCycles.includes(billing_cycle)) return new Response(JSON.stringify({ ok: false, error: "invalid_billing_cycle" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const tierConfig = getTierConfig(tier);
  if (!tierConfig) return new Response(JSON.stringify({ ok: false, error: "tier_not_configured" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const customer = await getCustomer(customerId);
  if (!customer) return new Response(JSON.stringify({ ok: false, error: "customer_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

  const now = new Date();
  const renewsAt = addMonths(now.toISOString(), billing_cycle === "monthly" ? 1 : 12);
  const endsAt = addMonths(now.toISOString(), billing_cycle === "monthly" ? 1 : 12);

  const updated = await saveCustomer({
    ...customer,
    tier,
    billing_cycle,
    status: "trialing",
    included_credits: tierConfig.included_credits || 0,
    used_this_month: 0,
    credit_balance: tierConfig.included_credits || 0,
    renews_at: renewsAt,
    ends_at: endsAt,
    cancel_at_period_end: false,
    trial_ends_at: addDays(now.toISOString(), 14).slice(0, 10) + "T00:00:00.000Z"
  });

  const checkoutUrl = `https://geo-audit-24xs.vercel.app/checkout?plan=${tier}&cycle=${billing_cycle}&customer=${customerId}`;

  return new Response(JSON.stringify({
    ok: true,
    data: {
      subscription: {
        customer_id: customerId,
        tier: updated.tier,
        billing_cycle: updated.billing_cycle,
        status: updated.status,
        renews_at: updated.renews_at,
        ends_at: updated.ends_at,
        trial_ends_at: updated.trial_ends_at
      },
      checkout_url: checkoutUrl
    }
  }), { status: 200, headers: { "Content-Type": "application/json" } });
}

async function handleChangePlan(request) {
  const customerId = extractCustomerId(request);
  if (!customerId) return new Response(JSON.stringify({ ok: false, error: "missing_customer_id" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const body = await request.json().catch(() => ({}));
  const { new_tier, new_billing_cycle } = body;
  const validTiers = ["starter", "professional", "enterprise"];
  if (!validTiers.includes(new_tier)) return new Response(JSON.stringify({ ok: false, error: "invalid_tier" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const customer = await getCustomer(customerId);
  if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

  const tierConfig = getTierConfig(new_tier);
  const cycle = new_billing_cycle || customer.billing_cycle;
  const renewsAt = addMonths(customer.renews_at || new Date().toISOString(), cycle === "monthly" ? 1 : 12);

  await saveCustomer({
    ...customer,
    tier: new_tier,
    billing_cycle: cycle,
    included_credits: tierConfig?.included_credits || 0,
    credit_balance: tierConfig?.included_credits || 0,
    renews_at: renewsAt,
    status: "active"
  });

  return new Response(JSON.stringify({ ok: true, data: { tier: new_tier, billing_cycle: cycle } }), { headers: { "Content-Type": "application/json" } });
}

async function handleCancel(request) {
  const customerId = extractCustomerId(request);
  if (!customerId) return new Response(JSON.stringify({ ok: false, error: "missing_customer_id" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const body = await request.json().catch(() => ({}));
  const { immediate = false } = body;
  const customer = await getCustomer(customerId);
  if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

  if (immediate) {
    await saveCustomer({ ...customer, status: "canceled", cancel_at_period_end: false, ends_at: new Date().toISOString() });
  } else {
    await saveCustomer({ ...customer, cancel_at_period_end: true, status: "active" });
  }

  return new Response(JSON.stringify({ ok: true, data: { canceled: true, immediate } }), { headers: { "Content-Type": "application/json" } });
}

async function handleReactivate(request) {
  const customerId = extractCustomerId(request);
  if (!customerId) return new Response(JSON.stringify({ ok: false, error: "missing_customer_id" }), { status: 400, headers: { "Content-Type": "application/json" } });

  const customer = await getCustomer(customerId);
  if (!customer) return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });

  const now = new Date();
  const renewsAt = addMonths(now.toISOString(), customer.billing_cycle === "monthly" ? 1 : 12);
  await saveCustomer({ ...customer, status: "active", cancel_at_period_end: false, ends_at: renewsAt, renews_at: renewsAt });

  return new Response(JSON.stringify({ ok: true, data: { reactivated: true, renews_at: renewsAt } }), { headers: { "Content-Type": "application/json" } });
}

export async function onRequest(context) {
  const { request, env, params, next } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "";

  if (request.method === "GET" && action === "") return handleGet(request);
  if (request.method === "POST" && action === "") return handlePost(request);
  if (request.method === "POST" && action === "change-plan") return handleChangePlan(request);
  if (request.method === "POST" && action === "cancel") return handleCancel(request);
  if (request.method === "POST" && action === "reactivate") return handleReactivate(request);

  return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
}