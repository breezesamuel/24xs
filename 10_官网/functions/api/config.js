const fs = require("fs");
const path = require("path");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "get";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  if (action === "get") {
    const configPath = path.join(REG, "pricing_engine.json");
    if (!fs.existsSync(configPath)) {
      return new Response(JSON.stringify({ ok: false, error: "config_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
    return new Response(JSON.stringify({ ok: true, data: config }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "tiers") {
    const configPath = path.join(REG, "pricing_engine.json");
    if (!fs.existsSync(configPath)) {
      return new Response(JSON.stringify({ ok: false, error: "config_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
    const tiers = config.tiers || {};

    return new Response(JSON.stringify({
      ok: true,
      data: Object.entries(tiers).map(([key, value]) => ({
        key,
        name: value.name,
        price_monthly: value.price_monthly,
        price_yearly: value.price_yearly,
        included_credits: value.included_credits,
        features: value.features
      }))
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "features") {
    const configPath = path.join(REG, "pricing_engine.json");
    if (!fs.existsSync(configPath)) {
      return new Response(JSON.stringify({ ok: false, error: "config_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
    const tiers = config.tiers || {};

    const allFeatures = new Set();
    for (const tier of Object.values(tiers)) {
      for (const f of (tier.features || [])) {
        allFeatures.add(f);
      }
    }

    return new Response(JSON.stringify({
      ok: true,
      data: {
        all_features: Array.from(allFeatures),
        by_tier: Object.entries(tiers).map(([key, value]) => ({
          tier: key,
          features: value.features || []
        }))
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}