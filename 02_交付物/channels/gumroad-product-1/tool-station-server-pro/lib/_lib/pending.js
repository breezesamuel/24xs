// 订单持久化层：Upstash REST API
// Vercel 环境变量:
//   KV_REST_API_URL  - Upstash REST URL (Redis)
//   KV_REST_API_TOKEN - token
// 设计: 每个订单存 { plan, userId, returnUrl, createdAt, amountUsd }
//       TTL 72h 自动清理
//       key: pay_pending_{orderId}
//       fallback: 内存 Map（KV 不可用时不阻塞建单）

const KV_BASE = process.env.KV_REST_API_URL || "";
const KV_TOKEN = process.env.KV_REST_API_TOKEN || "";
const KV_TIMEOUT_MS = 4000;
const PENDING_TTL_S = 72 * 3600; // 72h

const memFallback = new Map();

function kvEnabled() {
  return !!(KV_BASE && KV_TOKEN);
}

async function kvExec(args) {
  if (!kvEnabled()) return { ok: false };
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), KV_TIMEOUT_MS);
  try {
    const resp = await fetch(KV_BASE, {
      method: "POST",
      headers: { Authorization: `Bearer ${KV_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify(args),
      signal: ctrl.signal,
    });
    const data = await resp.json().catch(() => ({}));
    return { ok: data.ok === true, data };
  } catch (e) {
    return { ok: false, error: String(e.message || e) };
  } finally {
    clearTimeout(t);
  }
}

export async function registerPending(orderId, info) {
  const record = { ...info, createdAt: Date.now() };
  const key = `pay_pending_${orderId}`;
  const kv = await kvExec([
    "SET", key, JSON.stringify(record), "EX", PENDING_TTL_S,
  ]);
  if (!kv.ok) {
    // fallback to memory (won't survive across Vercel instances, but works for same-instance)
    memFallback.set(key, record);
  }
}

export async function getPending(orderId) {
  const key = `pay_pending_${orderId}`;
  const kv = await kvExec(["GET", key]);
  if (kv.ok && kv.data[0] != null) {
    try { return JSON.parse(kv.data[0]); } catch { /* corrupt */ }
  }
  // fallback to memory
  return memFallback.get(key) || null;
}

export async function removePending(orderId) {
  const key = `pay_pending_${orderId}`;
  await kvExec(["DEL", key]);
  memFallback.delete(key);
}
