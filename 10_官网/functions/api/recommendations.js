const { getCustomer, loadDb, saveDb, checkEntitlement } = require("../../../lib/entitlements.js");
const fs = require("fs");
const path = require("path");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

function cosineSimilarity(a, b) {
  const setA = new Set(a || []);
  const setB = new Set(b || []);
  const intersection = new Set([...setA].filter(x => setB.has(x)));
  const union = new Set([...setA, ...setB]);
  return union.size === 0 ? 0 : intersection.size / union.size;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "for_you";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const customer = await getCustomer(customerId);
  if (!customer) {
    return new Response(JSON.stringify({ ok: false, error: "not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  const db = loadDb();

  if (action === "for_you") {
    const usage = (db.usage_records || []).filter(r => r.customer_id === customerId);
    const purchases = (db.purchases || []).filter(p => p.customer_id === customerId);

    const preferredTypes = {};
    const preferredTags = {};

    for (const p of purchases) {
      const assetIds = p.asset_ids || [];
      for (const aid of assetIds) {
        const asset = (db.assets_cache || []).find(a => a.asset_id === aid);
        if (asset) {
          preferredTypes[asset.type] = (preferredTypes[asset.type] || 0) + 1;
          for (const tag of (asset.tags || [])) {
            preferredTags[tag] = (preferredTags[tag] || 0) + 1;
          }
        }
      }
    }

    for (const u of usage) {
      if (u.metadata?.type) {
        preferredTypes[u.metadata.type] = (preferredTypes[u.metadata.type] || 0) + 1;
      }
    }

    const topTypes = Object.entries(preferredTypes).sort((a, b) => b[1] - a[1]).slice(0, 5).map(e => e[0]);
    const topTags = Object.entries(preferredTags).sort((a, b) => b[1] - a[1]).slice(0, 10).map(e => e[0]);

    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    const recommendations = [];

    if (fs.existsSync(assetsPath) && (topTypes.length > 0 || topTags.length > 0)) {
      const content = fs.readFileSync(assetsPath, "utf8");
      const lines = content.split("\n");
      const purchasedIds = new Set(purchases.flatMap(p => p.asset_ids || []));

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const asset = JSON.parse(line);
          if (purchasedIds.has(asset.asset_id)) continue;

          let score = 0;
          if (topTypes.includes(asset.type)) score += 3;
          for (const tag of (asset.tags || [])) {
            if (topTags.includes(tag)) score += 1;
          }

          if (score > 0) {
            recommendations.push({ ...asset, _score: score });
            if (recommendations.length >= 100) break;
          }
        } catch (e) {}
      }
    }

    recommendations.sort((a, b) => b._score - a._score);
    const topRecommendations = recommendations.slice(0, 20).map(r => {
      const { _score, ...asset } = r;
      return asset;
    });

    return new Response(JSON.stringify({
      ok: true,
      data: {
        recommendations: topRecommendations,
        based_on: {
          purchase_count: purchases.length,
          usage_count: usage.length,
          preferred_types: topTypes,
          preferred_tags: topTags
        }
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "similar") {
    const assetId = url.searchParams.get("asset_id");
    if (!assetId) {
      return new Response(JSON.stringify({ ok: false, error: "asset_id_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    let targetAsset = null;
    const allAssets = [];

    if (fs.existsSync(assetsPath)) {
      const content = fs.readFileSync(assetsPath, "utf8");
      const lines = content.split("\n");
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const asset = JSON.parse(line);
          if (asset.asset_id === assetId) {
            targetAsset = asset;
          }
          if (allAssets.length < 50000) {
            allAssets.push(asset);
          }
        } catch (e) {}
      }
    }

    if (!targetAsset) {
      return new Response(JSON.stringify({ ok: false, error: "asset_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const similarities = [];
    for (const asset of allAssets) {
      if (asset.asset_id === assetId) continue;
      const typeMatch = asset.type === targetAsset.type ? 1 : 0;
      const tagSim = cosineSimilarity(asset.tags, targetAsset.tags);
      const score = typeMatch * 0.5 + tagSim * 0.5;
      if (score > 0.3) {
        similarities.push({ ...asset, _score: score });
      }
    }

    similarities.sort((a, b) => b._score - a._score);
    const topSimilar = similarities.slice(0, 20).map(r => {
      const { _score, ...asset } = r;
      return asset;
    });

    return new Response(JSON.stringify({
      ok: true,
      data: {
        target: targetAsset,
        similar: topSimilar
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "trending") {
    const usage = db.usage_records || [];
    const assetCounts = {};

    for (const u of usage) {
      if (u.metadata?.asset_id) {
        assetCounts[u.metadata.asset_id] = (assetCounts[u.metadata.asset_id] || 0) + 1;
      }
    }

    const trendingIds = Object.entries(assetCounts).sort((a, b) => b[1] - a[1]).slice(0, 20).map(e => e[0]);

    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    const trending = [];

    if (fs.existsSync(assetsPath)) {
      const content = fs.readFileSync(assetsPath, "utf8");
      const lines = content.split("\n");
      const idSet = new Set(trendingIds);

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const asset = JSON.parse(line);
          if (idSet.has(asset.asset_id)) {
            trending.push(asset);
            if (trending.length >= 20) break;
          }
        } catch (e) {}
      }
    }

    return new Response(JSON.stringify({ ok: true, data: trending }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}