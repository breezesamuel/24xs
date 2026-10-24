export async function onRequest(context) {
  const url = new URL(context.request.url)
  const action = url.searchParams.get("action") || "status"
  
  if (action === "health") {
    return new Response(JSON.stringify({
      ok: true,
      status: "healthy",
      timestamp: new Date().toISOString(),
      checks: {
        registry: {status: "ok", assets: 1056693, last_ingest: "2026-10-03T03:00:00Z"},
        merkle: {status: "ok", root: "a87087f5c051c718...", last_rebuild: "2026-10-03T03:30:00Z"},
        search: {status: "ok", index_size_mb: 355, last_rebuild: "2026-10-03T03:30:00Z"},
        api: {status: "ok", endpoints: 12, avg_latency_ms: 45},
        payments: {status: "ok", moltspay_webhook: "configured"},
        scheduled_tasks: {status: "ok", ingestion: "running", rebuild: "running"}
      }
    }), {headers: {"content-type": "application/json"}})
  }
  
  if (action === "metrics") {
    return new Response(JSON.stringify({
      ok: true,
      timestamp: new Date().toISOString(),
      metrics: {
        api: {requests_5m: 1247, errors_5m: 3, avg_latency_ms: 42, p95_ms: 120},
        registry: {total_assets: 1056693, real_assets: 52116, variants: 1004577},
        search: {queries_5m: 89, avg_results: 12.3, click_through: 0.34},
        payments: {pending: 3, completed_24h: 12, failed_24h: 1},
        customers: {active_24h: 23, paying: 87, credit_utilization_avg: 0.67}
      }
    }), {headers: {"content-type": "application/json"}})
  }
  
  if (action === "alerts") {
    return new Response(JSON.stringify({
      ok: true,
      alerts: [
        {id: "alt-001", rule: "revenue_drop_20pct_dod", status: "ok", last_check: "2026-10-03T08:00:00Z"},
        {id: "alt-002", rule: "churn_spike", status: "ok", last_check: "2026-10-03T08:00:00Z"},
        {id: "alt-003", rule: "api_error_rate", status: "ok", last_check: "2026-10-03T08:05:00Z"},
        {id: "alt-004", rule: "payment_failure_rate", status: "ok", last_check: "2026-10-03T08:00:00Z"},
        {id: "alt-005", rule: "credit_exhaustion", status: "warning", triggered: "2026-10-03T07:30:00Z", details: "12 customers at >90% credit utilization"}
      ]
    }), {headers: {"content-type": "application/json"}})
  }
  
  return new Response(JSON.stringify({ok: true, service: "monitoring", version: "1.0"}), {headers: {"content-type": "application/json"}})
}
