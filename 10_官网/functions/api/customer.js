export async function onRequest(context) {
  const url = new URL(context.request.url)
  const path = url.pathname.replace("/api/customer", "") || "/"
  
  // Mock responses - production uses D1/KV
  if (path === "/signup" && context.request.method === "POST") {
    const body = await context.request.json()
    const customer_id = "CUST-" + Date.now().toString(36).toUpperCase() + Math.random().toString(36).substr(2,4).toUpperCase()
    return new Response(JSON.stringify({ok: true, customer_id, tier: body.tier || "starter", status: "pending_verification"}), {headers: {"content-type": "application/json"}})
  }
  
  if (path === "/profile" && context.request.method === "GET") {
    const customer_id = url.searchParams.get("customer_id")
    if (!customer_id) return new Response(JSON.stringify({ok: false, error: "customer_id_required"}), {status: 400, headers: {"content-type": "application/json"}})
    return new Response(JSON.stringify({ok: true, customer_id, tier: "professional", credit_balance: 15000, total_spent: 45000, status: "active"}), {headers: {"content-type": "application/json"}})
  }
  
  if (path === "/purchases" && context.request.method === "GET") {
    return new Response(JSON.stringify({ok: true, purchases: []}), {headers: {"content-type": "application/json"}})
  }
  
  if (path === "/api-keys" && context.request.method === "POST") {
    const body = await context.request.json()
    const key_id = "KEY-" + Math.random().toString(36).substr(2,8).toUpperCase()
    const raw_key = "sk_live_" + Math.random().toString(36).substr(2,32)
    return new Response(JSON.stringify({ok: true, key_id, api_key: raw_key, permissions: body.permissions || ["read"]}), {headers: {"content-type": "application/json"}})
  }
  
  return new Response(JSON.stringify({ok: false, error: "not_found"}), {status: 404, headers: {"content-type": "application/json"}})
}
