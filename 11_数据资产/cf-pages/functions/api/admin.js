# Admin Dashboard API endpoints
export async function onRequest(context) {
  const url = new URL(context.request.url)
  const path = url.pathname.replace("/api/admin", "") || "/"
  const method = context.request.method
  
  // Auth check (simplified - production uses JWT + RBAC)
  const auth = context.request.headers.get("Authorization") || ""
  if (!auth.startsWith("Bearer ")) {
    return new Response(JSON.stringify({ok: false, error: "unauthorized"}), {status: 401, headers: {"content-type": "application/json"}})
  }
  const token = auth.slice(7)
  // Verify token against admin list / JWT
  const isAdmin = token.startsWith("admin_") // placeholder
  if (!isAdmin) {
    return new Response(JSON.stringify({ok: false, error: "forbidden"}), {status: 403, headers: {"content-type": "application/json"}})
  }
  
  // Mock data - production queries D1/PostgreSQL
  const mockData = {
    customers: [
      {customer_id: "CUST-20261001-A1B2C3", email: "buyer1@company.com", company: "Acme Corp", tier: "professional", status: "active", credit_balance: 15000, total_spent: 45000, created_at: "2026-09-15T10:30:00Z"},
      {customer_id: "CUST-20261002-D4E5F6", email: "buyer2@startup.io", company: "StartupXYZ", tier: "starter", status: "active", credit_balance: 3200, total_spent: 8900, created_at: "2026-09-20T14:15:00Z"},
      {customer_id: "CUST-20261003-G7H8I9", email: "procurement@bigcorp.cn", company: "BigCorp China", tier: "enterprise", status: "active", credit_balance: 85000, total_spent: 320000, created_at: "2026-09-01T09:00:00Z"}
    ],
    purchases: [
      {purchase_id: "PUR-20261001-A1B2C3", customer_id: "CUST-20261001-A1B2C3", asset_ids: ["V-20261003-001234"], bundle_id: null, license_type: "commercial-multi-v1", amount_cny: 500, credits_used: 500, status: "completed", payment_txn_id: "moltspay_txn_abc123", created_at: "2026-10-01T10:30:00Z", completed_at: "2026-10-01T10:31:00Z", delivery_status: "delivered"},
      {purchase_id: "PUR-20261002-D4E5F6", customer_id: "CUST-20261002-D4E5F6", asset_ids: ["V-20261003-002345", "V-20261003-003456"], bundle_id: "sales_starter_pack", license_type: "commercial-multi-v1", amount_cny: 11250, credits_used: 11250, status: "completed", payment_txn_id: "moltspay_txn_def456", created_at: "2026-10-02T14:20:00Z", completed_at: "2026-10-02T14:21:00Z", delivery_status: "delivered"}
    ],
    assets_summary: {total: 1056693, real: 52116, variants: 1004577, by_type: {"采购方画像": 6493, "品类市场分析": 32, "招采公告": 17290}},
    revenue: {mrr: 1250000, arr: 15000000, paying_customers: 87, gmv_30d: 1250000}
  }
  
  try {
    // GET /api/admin/dashboard
    if (path === "/dashboard" && method === "GET") {
      return new Response(JSON.stringify({ok: true, data: {revenue: mockData.revenue, assets: mockData.assets_summary, recent_purchases: mockData.purchases.slice(0,10)}}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/admin/customers
    if (path === "/customers" && method === "GET") {
      const page = parseInt(url.searchParams.get("page") || "1")
      const limit = Math.min(parseInt(url.searchParams.get("limit") || "20"), 100)
      const search = url.searchParams.get("search") || ""
      let filtered = mockData.customers
      if (search) {
        filtered = filtered.filter(c => c.email.includes(search) || c.company.includes(search) || c.customer_id.includes(search))
      }
      const start = (page - 1) * limit
      return new Response(JSON.stringify({ok: true, data: filtered.slice(start, start + limit), total: filtered.length, page, limit}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/admin/customers/:id
    if (path.startsWith("/customers/") && method === "GET") {
      const customer_id = path.split("/")[2]
      const customer = mockData.customers.find(c => c.customer_id === customer_id)
      if (!customer) return new Response(JSON.stringify({ok: false, error: "not_found"}), {status: 404, headers: {"content-type": "application/json"}})
      const purchases = mockData.purchases.filter(p => p.customer_id === customer_id)
      return new Response(JSON.stringify({ok: true, data: {...customer, purchases}}), {headers: {"content-type": "application/json"}})
    }
    
    // POST /api/admin/customers/:id/suspend
    if (path.match(/^\/customers\/[^/]+\/suspend$/) && method === "POST") {
      const customer_id = path.split("/")[2]
      return new Response(JSON.stringify({ok: true, customer_id, status: "suspended"}), {headers: {"content-type": "application/json"}})
    }
    
    // POST /api/admin/customers/:id/credits
    if (path.match(/^\/customers\/[^/]+\/credits$/) && method === "POST") {
      const body = await context.request.json()
      const customer_id = path.split("/")[2]
      const amount = body.amount || 0
      return new Response(JSON.stringify({ok: true, customer_id, credited: amount, new_balance: 15000 + amount}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/admin/purchases
    if (path === "/purchases" && method === "GET") {
      const page = parseInt(url.searchParams.get("page") || "1")
      const limit = Math.min(parseInt(url.searchParams.get("limit") || "20"), 100)
      const status = url.searchParams.get("status") || ""
      let filtered = mockData.purchases
      if (status) filtered = filtered.filter(p => p.status === status)
      const start = (page - 1) * limit
      return new Response(JSON.stringify({ok: true, data: filtered.slice(start, start + limit), total: filtered.length, page, limit}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/admin/assets
    if (path === "/assets" && method === "GET") {
      return new Response(JSON.stringify({ok: true, data: mockData.assets_summary}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/admin/analytics
    if (path === "/analytics" && method === "GET") {
      return new Response(JSON.stringify({ok: true, data: mockData.revenue}), {headers: {"content-type": "application/json"}})
    }
    
    return new Response(JSON.stringify({ok: false, error: "not_found"}), {status: 404, headers: {"content-type": "application/json"}})
  } catch (e) {
    return new Response(JSON.stringify({ok: false, error: "internal_error"}), {status: 500, headers: {"content-type": "application/json"}})
  }
}
