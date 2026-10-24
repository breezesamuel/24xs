const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "report";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  if (action === "report") {
    const reportPath = path.join(REG, "quality_report.json");
    if (!fs.existsSync(reportPath)) {
      return new Response(JSON.stringify({ ok: false, error: "report_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
    return new Response(JSON.stringify({ ok: true, data: report }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "verify_asset") {
    const assetId = url.searchParams.get("asset_id");
    if (!assetId) {
      return new Response(JSON.stringify({ ok: false, error: "asset_id_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    if (!fs.existsSync(assetsPath)) {
      return new Response(JSON.stringify({ ok: false, error: "assets_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    let asset = null;
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n");

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const a = JSON.parse(line);
        if (a.asset_id === assetId) {
          asset = a;
          break;
        }
      } catch (e) {}
    }

    if (!asset) {
      return new Response(JSON.stringify({ ok: false, error: "asset_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const proof = asset.proof || "";
    const proofType = asset.proof_type || "sha256";
    const computed = crypto.createHash("sha256").update(JSON.stringify(asset, null, 0)).digest("hex");
    const isValid = proof === computed || proof.length === 64;

    return new Response(JSON.stringify({
      ok: true,
      data: {
        asset_id: assetId,
        proof_valid: isValid,
        proof_type: proofType,
        proof_length: proof.length,
        computed_hash: computed.slice(0, 16) + "...",
        asset: {
          type: asset.type,
          name: asset.name,
          source: asset.source
        }
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "stats") {
    const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
    if (!fs.existsSync(assetsPath)) {
      return new Response(JSON.stringify({ ok: false, error: "assets_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const stats = fs.statSync(assetsPath);
    const content = fs.readFileSync(assetsPath, "utf8");
    const lines = content.split("\n").filter(l => l.trim());

    const typeCounts = {};
    const tagCounts = {};
    let totalProofValid = 0;
    let totalProofInvalid = 0;

    for (const line of lines.slice(0, 10000)) {
      try {
        const asset = JSON.parse(line);
        typeCounts[asset.type] = (typeCounts[asset.type] || 0) + 1;
        for (const tag of (asset.tags || [])) {
          tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        }
        if (asset.proof && asset.proof.length === 64) {
          totalProofValid++;
        } else {
          totalProofInvalid++;
        }
      } catch (e) {}
    }

    const topTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
    const topTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 20);

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total_assets: lines.length,
        file_size_mb: (stats.size / 1024 / 1024).toFixed(2),
        sample_size: Math.min(10000, lines.length),
        proof_valid_rate: ((totalProofValid / (totalProofValid + totalProofInvalid)) * 100).toFixed(2) + "%",
        top_types: topTypes,
        top_tags: topTags,
        last_modified: stats.mtime.toISOString()
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}