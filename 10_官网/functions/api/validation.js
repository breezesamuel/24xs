const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { checkEntitlement, consumeEntitlement } = require("../../../lib/entitlements.js");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "verify";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  if (action === "verify") {
    const body = await request.json().catch(() => ({}));
    const { proof, data, parent_proof, variant_index } = body;

    if (!proof) {
      return new Response(JSON.stringify({ ok: false, error: "proof_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const entitlement = await checkEntitlement({ customerId, action: "verify", cost: 1, requireActive: true });
    if (!entitlement.allowed) {
      return new Response(JSON.stringify({ ok: false, ...entitlement }), { status: entitlement.code || 403, headers: { "Content-Type": "application/json" } });
    }

    let match = false;
    let computed = "";
    let type = "";

    if (parent_proof && variant_index) {
      const enc = new TextEncoder();
      const chain = parent_proof + ":variant:" + variant_index;
      const h = await crypto.subtle.digest("SHA-256", enc.encode(chain));
      computed = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
      match = computed === proof;
      type = "chain";
    } else if (data) {
      const enc = new TextEncoder();
      const h = await crypto.subtle.digest("SHA-256", enc.encode(typeof data === "string" ? data : JSON.stringify(data)));
      computed = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
      match = computed === proof;
      type = "direct";
    } else {
      const assetsPath = path.join(REG, "assets_verifiable_1M.jsonl");
      if (fs.existsSync(assetsPath)) {
        const content = fs.readFileSync(assetsPath, "utf8");
        const lines = content.split("\n");
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const asset = JSON.parse(line);
            if (asset.proof === proof) {
              match = true;
              type = "asset";
              computed = proof;
              break;
            }
          } catch (e) {}
        }
      }
    }

    await consumeEntitlement({ customerId, action: "verify", cost: 1, metadata: { proof: proof.slice(0, 16), match } });

    return new Response(JSON.stringify({
      ok: true,
      data: {
        match,
        type,
        computed: computed.slice(0, 32) + (computed.length > 32 ? "..." : ""),
        proof: proof.slice(0, 32) + (proof.length > 32 ? "..." : ""),
        verified_at: new Date().toISOString()
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "batch") {
    const body = await request.json().catch(() => ({}));
    const { proofs } = body;

    if (!proofs || !Array.isArray(proofs) || proofs.length === 0) {
      return new Response(JSON.stringify({ ok: false, error: "proofs_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    if (proofs.length > 100) {
      return new Response(JSON.stringify({ ok: false, error: "too_many_proofs" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const entitlement = await checkEntitlement({ customerId, action: "verify", cost: proofs.length, requireActive: true });
    if (!entitlement.allowed) {
      return new Response(JSON.stringify({ ok: false, ...entitlement }), { status: entitlement.code || 403, headers: { "Content-Type": "application/json" } });
    }

    const results = [];
    for (const p of proofs) {
      const { proof, data, parent_proof, variant_index } = p;
      let match = false;
      let computed = "";

      if (parent_proof && variant_index) {
        const enc = new TextEncoder();
        const chain = parent_proof + ":variant:" + variant_index;
        const h = await crypto.subtle.digest("SHA-256", enc.encode(chain));
        computed = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
        match = computed === proof;
      } else if (data) {
        const enc = new TextEncoder();
        const h = await crypto.subtle.digest("SHA-256", enc.encode(typeof data === "string" ? data : JSON.stringify(data)));
        computed = Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, "0")).join("");
        match = computed === proof;
      }

      results.push({ proof: proof?.slice(0, 16), match, computed: computed.slice(0, 16) });
    }

    await consumeEntitlement({ customerId, action: "verify", cost: proofs.length, metadata: { batch_size: proofs.length } });

    return new Response(JSON.stringify({
      ok: true,
      data: {
        total: results.length,
        matched: results.filter(r => r.match).length,
        failed: results.filter(r => !r.match).length,
        results
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}