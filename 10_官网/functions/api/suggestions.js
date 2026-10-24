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
  const action = url.searchParams.get("action") || "search";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  if (action === "search") {
    const q = url.searchParams.get("q") || "";
    const limit = Math.min(parseInt(url.searchParams.get("limit") || "10"), 50);

    if (!q || q.length < 2) {
      return new Response(JSON.stringify({ ok: true, data: [] }), { headers: { "Content-Type": "application/json" } });
    }

    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    if (!fs.existsSync(assetsPath)) {
      return new Response(JSON.stringify({ ok: true, data: [] }), { headers: { "Content-Type": "application/json" } });
    }

    const suggestions = [];
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");
    const qLower = q.toLowerCase();

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const asset = JSON.parse(line);
        const nameMatch = (asset.name || "").toLowerCase().includes(qLower);
        const typeMatch = (asset.type || "").toLowerCase().includes(qLower);
        const tagMatch = (asset.tags || []).some(t => t.toLowerCase().includes(qLower));

        if (nameMatch || typeMatch || tagMatch) {
          suggestions.push({
            asset_id: asset.asset_id,
            name: asset.name,
            type: asset.type,
            tags: asset.tags?.slice(0, 3)
          });
          if (suggestions.length >= limit) break;
        }
      } catch (e) {}
    }

    return new Response(JSON.stringify({ ok: true, data: suggestions }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "popular") {
    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    if (!fs.existsSync(assetsPath)) {
      return new Response(JSON.stringify({ ok: true, data: [] }), { headers: { "Content-Type": "application/json" } });
    }

    const typeCounts = {};
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");

    for (const line of lines.slice(0, 50000)) {
      if (!line.trim()) continue;
      try {
        const asset = JSON.parse(line);
        typeCounts[asset.type] = (typeCounts[asset.type] || 0) + 1;
      } catch (e) {}
    }

    const popular = Object.entries(typeCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([type, count]) => ({ type, count }));

    return new Response(JSON.stringify({ ok: true, data: popular }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "recent") {
    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    if (!fs.existsSync(assetsPath)) {
      return new Response(JSON.stringify({ ok: true, data: [] }), { headers: { "Content-Type": "application/json" } });
    }

    const recent = [];
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");

    for (let i = lines.length - 1; i >= 0 && recent.length < 20; i--) {
      if (!lines[i].trim()) continue;
      try {
        const asset = JSON.parse(lines[i]);
        recent.push({
          asset_id: asset.asset_id,
          name: asset.name,
          type: asset.type,
          created_at: asset.created_at
        });
      } catch (e) {}
    }

    return new Response(JSON.stringify({ ok: true, data: recent }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}