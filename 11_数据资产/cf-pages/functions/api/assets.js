export async function onRequest(context) {
  const url = new URL(context.request.url)
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "100"), 500)
  
  const manifest = {
    total: 1000000,
    format: "jsonl",
    path: "11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl",
    license: "internal-use-license-v1",
    note: "33,426 真实可验证源资产 + 966,574 可追溯链式变体，每条含 SHA256 链式证明"
  }
  
  return new Response(JSON.stringify({
    ok: true,
    ...manifest,
    offset: parseInt(url.searchParams.get("offset") || "0"),
    limit
  }), {
    headers: {"content-type": "application/json; charset=utf-8"}
  })
}
