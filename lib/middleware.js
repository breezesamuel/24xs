const fs = require("fs");
const path = require("path");

const LOG_DIR = path.resolve(__dirname, "../10_官网/logs");
const AUDIT_LOG = path.resolve(__dirname, "../11_数据资产/registry_real_verified/audit_logs.jsonl");

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function getClientInfo(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  const customerId = auth?.startsWith("Bearer ") ? auth.slice(7) : request.headers.get("x-customer-id") || "anonymous";
  const ip = request.headers.get("x-forwarded-for") || request.headers.get("cf-connecting-ip") || "unknown";
  const ua = request.headers.get("user-agent") || "unknown";
  return { customerId, ip, ua };
}

function logRequest(request, response, duration) {
  try {
    ensureDir(LOG_DIR);
    const { customerId, ip, ua } = getClientInfo(request);
    const url = new URL(request.url);
    const entry = {
      ts: new Date().toISOString(),
      method: request.method,
      path: url.pathname,
      query: Object.fromEntries(url.searchParams),
      status: response.status,
      duration_ms: Math.round(duration),
      customer_id: customerId,
      ip,
      user_agent: ua,
    };
    const logFile = path.join(LOG_DIR, `${new Date().toISOString().slice(0, 10)}.jsonl`);
    fs.appendFileSync(logFile, JSON.stringify(entry) + "\n");
  } catch (e) {}
}

function logAudit(customerId, action, resource, details) {
  try {
    const entry = {
      ts: new Date().toISOString(),
      customer_id: customerId,
      action,
      resource,
      details: details || {},
    };
    fs.appendFileSync(AUDIT_LOG, JSON.stringify(entry) + "\n");
  } catch (e) {}
}

function corsHeaders(request) {
  const origin = request.headers.get("origin") || "*";
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, x-customer-id",
    "Access-Control-Max-Age": "86400",
  };
}

function handleOptions(request) {
  return new Response(null, { status: 204, headers: corsHeaders(request) });
}

function withMiddleware(handler) {
  return async function (context) {
    const { request } = context;
    if (request.method === "OPTIONS") return handleOptions(request);
    const start = Date.now();
    const response = await handler(context);
    const duration = Date.now() - start;
    logRequest(request, response, duration);
    const cors = corsHeaders(request);
    for (const [k, v] of Object.entries(cors)) {
      response.headers.set(k, v);
    }
    return response;
  };
}

module.exports = { withMiddleware, logRequest, logAudit, corsHeaders, handleOptions, getClientInfo };