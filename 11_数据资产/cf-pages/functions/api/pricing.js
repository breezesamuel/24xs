export async function onRequest(context) {
  const url = new URL(context.request.url)
  const action = url.searchParams.get("action") || "get"
  
  // In production, load from KV/D1
  const pricing = {
    version: "2.0",
    currency: "CNY",
    rules: {
      volume_discounts: [
        {min_qty: 1, max_qty: 9, discount: 0.00},
        {min_qty: 10, max_qty: 49, discount: 0.05},
        {min_qty: 50, max_qty: 99, discount: 0.10},
        {min_qty: 100, max_qty: 499, discount: 0.15},
        {min_qty: 500, max_qty: 999, discount: 0.20},
        {min_qty: 1000, max_qty: 9999, discount: 0.25},
        {min_qty: 10000, max_qty: null, discount: 0.30}
      ],
      bundles: {
        ccgp_full_buyer: {name: "采购方全景包", base_price: 2000, bundle_discount: 0.20, final_price: 1600},
        geo_audit_full: {name: "GEO全平台审计包", base_price: 15000, bundle_discount: 0.15, final_price: 12750},
        sales_starter_pack: {name: "销售启动包", base_price: 15000, bundle_discount: 0.25, final_price: 11250},
        due_diligence_pack: {name: "尽调合规包", base_price: 8000, bundle_discount: 0.20, final_price: 6400},
        market_intel_quarterly: {name: "季度市场情报订阅", base_price: 50000, billing: "quarterly", bundle_discount: 0.10, final_price: 45000}
      },
      subscriptions: {
        starter: {name: "启动版", monthly_fee: 2999, included_credits: 5000, overage_rate: 0.80},
        professional: {name: "专业版", monthly_fee: 9999, included_credits: 20000, overage_rate: 0.60},
        enterprise: {name: "企业版", monthly_fee: 49999, included_credits: 100000, overage_rate: 0.40}
      },
      credits: {
        "采购方画像": 500, "品类市场分析": 2000, "区域市场分析": 1500,
        "项目全周期分析": 3000, "GEO客户端审计报告": 5000,
        "商业线索档案": 200, "企业全维档案": 100, "行业企业图谱": 2000
      }
    }
  }
  
  if (action === "calculate") {
    const asset_type = url.searchParams.get("asset_type") || ""
    const qty = parseInt(url.searchParams.get("qty") || "1")
    const bundle = url.searchParams.get("bundle") || ""
    const tier = url.searchParams.get("tier") || ""
    
    let unit_price = pricing.rules.credits[asset_type] || 100
    let discount = 0
    
    // volume discount
    for (const d of pricing.rules.volume_discounts) {
      const max = d.max_qty === null ? Infinity : d.max_qty
      if (qty >= d.min_qty && qty <= max) { discount = d.discount; break }
    }
    
    // bundle override
    if (bundle && pricing.rules.bundles[bundle]) {
      return new Response(JSON.stringify({ok: true, pricing: pricing.rules.bundles[bundle], qty, total: pricing.rules.bundles[bundle].final_price * qty}), {headers: {"content-type": "application/json"}})
    }
    
    const final_unit = unit_price * (1 - discount)
    const total = final_unit * qty
    
    return new Response(JSON.stringify({
      ok: true,
      asset_type, qty, unit_price, discount, final_unit_price: final_unit, total,
      tier_pricing: tier ? pricing.rules.subscriptions[tier] : null
    }), {headers: {"content-type": "application/json"}})
  }
  
  return new Response(JSON.stringify({ok: true, pricing}), {headers: {"content-type": "application/json"}})
}
