export async function onRequest(context) {
  const url = new URL(context.request.url)
  const dashboard = url.searchParams.get("dashboard") || "executive"
  const period = url.searchParams.get("period") || "30d"
  
  // Mock data - production queries D1/analytics DB
  const mock = {
    executive: {
      mrr: 1250000, arr: 15000000, paying_customers: 87, ltv_cac_ratio: 4.2,
      gmv_30d: [120000, 135000, 128000, 142000, 155000, 168000, 180000],
      net_revenue_30d: [100000, 112000, 108000, 120000, 130000, 140000, 150000]
    },
    product: {
      top_assets: [
        {asset_id: "V-20261003-001234", type: "采购方画像", revenue: 450000, purchases: 900},
        {asset_id: "V-20261003-002345", type: "品类市场分析", revenue: 380000, purchases: 190},
        {asset_id: "V-20261003-003456", type: "GEO客户端审计报告", revenue: 350000, purchases: 70}
      ],
      conversion: {"采购方画像": 0.12, "品类市场分析": 0.08, "GEO客户端审计报告": 0.15, "商业线索档案": 0.22}
    },
    customer: {
      lifecycle: {"signup": 1250, "activated": 890, "first_purchase": 340, "repeat_purchase": 180, "champion": 45},
      tier_dist: {"starter": 45, "professional": 32, "enterprise": 10}
    }
  }
  
  return new Response(JSON.stringify({ok: true, dashboard, period, data: mock[dashboard] || {}}), {headers: {"content-type": "application/json"}})
}
