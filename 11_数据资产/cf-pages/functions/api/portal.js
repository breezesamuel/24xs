# Customer self-service portal API
export async function onRequest(context) {
  const url = new URL(context.request.url)
  const path = url.pathname.replace("/api/portal", "") || "/"
  const method = context.request.method
  
  // Auth - customer JWT
  const auth = context.request.headers.get("Authorization") || ""
  if (!auth.startsWith("Bearer ")) {
    return new Response(JSON.stringify({ok: false, error: "unauthorized"}), {status: 401, headers: {"content-type": "application/json"}})
  }
  const token = auth.slice(7)
  // Mock: extract customer_id from token
  const customer_id = token.startsWith("cust_") ? token.slice(5) : null
  if (!customer_id) {
    return new Response(JSON.stringify({ok: false, error: "invalid_token"}), {status: 401, headers: {"content-type": "application/json"}})
  }
  
  // Mock customer data
  const mockCustomer = {
    customer_id,
    email: "buyer@company.com",
    company_name: "Acme Corp",
    tier: "professional",
    status: "active",
    credit_balance: 15000,
    total_spent: 45000,
    total_assets_purchased: 12,
    billing_cycle: "monthly",
    created_at: "2026-09-15T10:30:00Z",
    moltspay_customer_id: "molt_cust_abc123"
  }
  
  const mockPurchases = [
    {purchase_id: "PUR-20261001-A1B2C3", asset_ids: ["V-20261003-001234"], bundle_id: null, license_type: "commercial-multi-v1", amount_cny: 500, credits_used: 500, status: "completed", payment_txn_id: "moltspay_txn_abc123", created_at: "2026-10-01T10:30:00Z", completed_at: "2026-10-01T10:31:00Z", delivery_status: "delivered", delivery_url: "https://geo-audit-24xs.vercel.app/api/deliver?token=xyz", delivery_expires_at: "2026-10-02T10:31:00Z"},
    {purchase_id: "PUR-20261002-D4E5F6", asset_ids: ["V-20261003-002345"], bundle_id: null, license_type: "commercial-single-v1", amount_cny: 2000, credits_used: 2000, status: "completed", payment_txn_id: "moltspay_txn_def456", created_at: "2026-10-02T14:20:00Z", completed_at: "2026-10-02T14:21:00Z", delivery_status: "delivered", delivery_url: "https://geo-audit-24xs.vercel.app/api/deliver?token=abc", delivery_expires_at: "2026-10-03T14:21:00Z"}
  ]
  
  const mockApiKeys = [
    {key_id: "KEY-A1B2C3D4", name: "Production API", permissions: ["read", "search", "verify"], rate_limit: 60, status: "active", created_at: "2026-09-20T10:00:00Z", last_used_at: "2026-10-03T08:30:00Z", expires_at: "2027-03-20T10:00:00Z"},
    {key_id: "KEY-E5F6G7H8", name: "Development", permissions: ["read"], rate_limit: 20, status: "active", created_at: "2026-10-01T15:00:00Z", last_used_at: null, expires_at: "2027-04-01T15:00:00Z"}
  ]
  
  const mockInvoices = [
    {invoice_id: "INV-20261001-001", purchase_id: "PUR-20261001-A1B2C3", amount_cny: 500, tax_cny: 0, status: "issued", issued_at: "2026-10-01T10:31:00Z", pdf_url: "https://geo-audit-24xs.vercel.app/api/invoice/INV-20261001-001.pdf"},
    {invoice_id: "INV-20261002-001", purchase_id: "PUR-20261002-D4E5F6", amount_cny: 2000, tax_cny: 0, status: "issued", issued_at: "2026-10-02T14:21:00Z", pdf_url: "https://geo-audit-24xs.vercel.app/api/invoice/INV-20261002-001.pdf"}
  ]
  
  try {
    // GET /api/portal/profile
    if (path === "/profile" && method === "GET") {
      return new Response(JSON.stringify({ok: true, data: mockCustomer}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/portal/credits
    if (path === "/credits" && method === "GET") {
      const tierInfo = {
        starter: {monthly_fee: 2999, included_credits: 5000, overage_rate: 0.80},
        professional: {monthly_fee: 9999, included_credits: 20000, overage_rate: 0.60},
        enterprise: {monthly_fee: 49999, included_credits: 100000, overage_rate: 0.40}
      }[mockCustomer.tier] || {monthly_fee: 0, included_credits: 0, overage_rate: 1.0}
      
      const usedThisMonth = 5000 // mock
      const remaining = Math.max(0, tierInfo.included_credits - usedThisMonth)
      const utilization = (usedThisMonth / tierInfo.included_credits * 100).toFixed(1)
      
      return new Response(JSON.stringify({ok: true, data: {
        balance: mockCustomer.credit_balance,
        tier: mockCustomer.tier,
        included_credits: tierInfo.included_credits,
        used_this_month: usedThisMonth,
        remaining,
        utilization_pct: parseFloat(utilization),
        overage_rate: tierInfo.overage_rate,
        renews_at: "2026-11-01T00:00:00Z"
      }}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/portal/purchases
    if (path === "/purchases" && method === "GET") {
      const page = parseInt(url.searchParams.get("page") || "1")
      const limit = Math.min(parseInt(url.searchParams.get("limit") || "20"), 100)
      const start = (page - 1) * limit
      return new Response(JSON.stringify({ok: true, data: mockPurchases.slice(start, start + limit), total: mockPurchases.length, page, limit}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/portal/purchases/:id
    if (path.startsWith("/purchases/") && method === "GET") {
      const purchase_id = path.split("/")[2]
      const purchase = mockPurchases.find(p => p.purchase_id === purchase_id)
      if (!purchase) return new Response(JSON.stringify({ok: false, error: "not_found"}), {status: 404, headers: {"content-type": "application/json"}})
      return new Response(JSON.stringify({ok: true, data: purchase}), {headers: {"content-type": "application/json"}})
    }
    
    // POST /api/portal/purchases/:id/redeliver
    if (path.match(/^\/purchases\/[^/]+\/redeliver$/) && method === "POST") {
      const purchase_id = path.split("/")[2]
      const purchase = mockPurchases.find(p => p.purchase_id === purchase_id)
      if (!purchase) return new Response(JSON.stringify({ok: false, error: "not_found"}), {status: 404, headers: {"content-type": "application/json"}})
      if (purchase.delivery_status !== "delivered") return new Response(JSON.stringify({ok: false, error: "not_delivered"}), {status: 400, headers: {"content-type": "application/json"}})
      // Generate new delivery token
      const newToken = "dlv_" + Math.random().toString(36).substr(2, 32)
      return new Response(JSON.stringify({ok: true, purchase_id, delivery_url: "https://geo-audit-24xs.vercel.app/api/deliver?token=" + newToken, expires_at: new Date(Date.now() + 24*3600*1000).toISOString()}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/portal/api-keys
    if (path === "/api-keys" && method === "GET") {
      return new Response(JSON.stringify({ok: true, data: mockApiKeys}), {headers: {"content-type": "application/json"}})
    }
    
    // POST /api/portal/api-keys
    if (path === "/api-keys" && method === "POST") {
      const body = await context.request.json()
      const keyId = "KEY-" + Math.random().toString(36).substr(2, 8).toUpperCase()
      const rawKey = "sk_live_" + Math.random().toString(36).substr(2, 32)
      const newKey = {
        key_id: keyId,
        name: body.name || "New Key",
        permissions: body.permissions || ["read"],
        rate_limit: body.rate_limit || 60,
        status: "active",
        created_at: new Date().toISOString(),
        last_used_at: null,
        expires_at: new Date(Date.now() + 180*24*3600*1000).toISOString()
      }
      return new Response(JSON.stringify({ok: true, data: {...newKey, api_key: rawKey}}), {status: 201, headers: {"content-type": "application/json"}})
    }
    
    // DELETE /api/portal/api-keys/:id
    if (path.startsWith("/api-keys/") && method === "DELETE") {
      const key_id = path.split("/")[2]
      return new Response(JSON.stringify({ok: true, key_id, status: "revoked"}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/portal/invoices
    if (path === "/invoices" && method === "GET") {
      return new Response(JSON.stringify({ok: true, data: mockInvoices}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/portal/invoices/:id
    if (path.startsWith("/invoices/") && method === "GET") {
      const invoice_id = path.split("/")[2]
      const invoice = mockInvoices.find(i => i.invoice_id === invoice_id)
      if (!invoice) return new Response(JSON.stringify({ok: false, error: "not_found"}), {status: 404, headers: {"content-type": "application/json"}})
      return new Response(JSON.stringify({ok: true, data: invoice}), {headers: {"content-type": "application/json"}})
    }
    
    // GET /api/portal/usage
    if (path === "/usage" && method === "GET") {
      const days = parseInt(url.searchParams.get("days") || "30")
      const usage = []
      for (let i = days - 1; i >= 0; i--) {
        const date = new Date()
        date.setDate(date.getDate() - i)
        usage.push({
          date: date.toISOString().split("T")[0],
          api_calls: Math.floor(Math.random() * 500) + 100,
          search_queries: Math.floor(Math.random() * 50) + 10,
          assets_viewed: Math.floor(Math.random() * 20) + 5,
          credits_consumed: Math.floor(Math.random() * 200)
        })
      }
      return new Response(JSON.stringify({ok: true, data: usage}), {headers: {"content-type": "application/json"}})
    }
    
    // POST /api/portal/upgrade
    if (path === "/upgrade" && method === "POST") {
      const body = await context.request.json()
      const newTier = body.tier
      const validTiers = ["starter", "professional", "enterprise"]
      if (!validTiers.includes(newTier)) return new Response(JSON.stringify({ok: false, error: "invalid_tier"}), {status: 400, headers: {"content-type": "application/json"}})
      return new Response(JSON.stringify({ok: true, customer_id, new_tier: newTier, effective_at: "2026-11-01T00:00:00Z", proration_credit: 1250}), {headers: {"content-type": "application/json"}})
    }
    
    return new Response(JSON.stringify({ok: false, error: "not_found"}), {status: 404, headers: {"content-type": "application/json"}})
  } catch (e) {
    return new Response(JSON.stringify({ok: false, error: "internal_error"}), {status: 500, headers: {"content-type": "application/json"}})
  }
}
