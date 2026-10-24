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
  const action = url.searchParams.get("action") || "overview";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
  if (!fs.existsSync(assetsPath)) {
    return new Response(JSON.stringify({ ok: false, error: "assets_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  if (action === "overview") {
    const stats = fs.statSync(assetsPath);
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n").filter(l => l.trim());

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total_assets: lines.length,
        file_size_mb: (stats.size / 1024 / 1024).toFixed(2),
        last_modified: stats.mtime.toISOString(),
        index_status: "active",
        search_engine: "FTS5"
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "by_type") {
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");
    const typeCounts = {};

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const asset = JSON.parse(line);
        typeCounts[asset.type] = (typeCounts[asset.type] || 0) + 1;
      } catch (e) {}
    }

    const sorted = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total_types: sorted.length,
        distribution: sorted.map(([type, count]) => ({ type, count, percentage: ((count / lines.length) * 100).toFixed(2) + "%" }))
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "by_tag") {
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");
    const tagCounts = {};

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const asset = JSON.parse(line);
        for (const tag of (asset.tags || [])) {
          tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        }
      } catch (e) {}
    }

    const sorted = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 50);

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total_tags: Object.keys(tagCounts).length,
        top_tags: sorted.map(([tag, count]) => ({ tag, count }))
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "by_price") {
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");
    const priceRanges = {
      "0-10": 0,
      "10-50": 0,
      "50-100": 0,
      "100-500": 0,
      "500-1000": 0,
      "1000+": 0
    };

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const asset = JSON.parse(line);
        const price = asset.price_cny_ref || 0;
        if (price < 10) priceRanges["0-10"]++;
        else if (price < 50) priceRanges["10-50"]++;
        else if (price < 100) priceRanges["50-100"]++;
        else if (price < 500) priceRanges["100-500"]++;
        else if (price < 1000) priceRanges["500-1000"]++;
        else priceRanges["1000+"]++;
      } catch (e) {}
    }

    return new Response(JSON.stringify({
      ok: true,
      data: {
        distribution: Object.entries(priceRanges).map(([range, count]) => ({ range, count, percentage: ((count / lines.length) * 100).toFixed(2) + "%" }))
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}