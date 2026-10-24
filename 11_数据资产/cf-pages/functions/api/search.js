export async function onRequest(context) {
  const url = new URL(context.request.url)
  const q = url.searchParams.get("q") || ""
  const type = url.searchParams.get("type") || ""
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 200)
  
  if (!q && !type) {
    return new Response(JSON.stringify({ok: false, error: "query_required"}), {status: 400, headers: {"content-type": "application/json"}})
  }
  
  // In CF Pages, we cannot easily access local SQLite. 
  // This endpoint documents the query format; production would connect to D1 or external search.
  return new Response(JSON.stringify({
    ok: true,
    query: {q, type, limit},
    note: "Production: connect to Cloudflare D1 or external search service. Local: assets_search.db FTS5",
    example: "SELECT asset_id,name,type,tags FROM assets_fts WHERE assets_fts MATCH ? LIMIT ?"
  }), {headers: {"content-type": "application/json; charset=utf-8"}})
}
