// Vercel rewrite target for dashboard (optional - serves the HTML dashboard)
export default function handler(req, res) {
  const html = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>AI 获客运营看板</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#f8fafc;--card:#fff;--text:#111827;--muted:#6b7280;--border:#e5e7eb;--pri:#2563eb;--ok:#059669;--err:#dc2626}
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:24px;line-height:1.5}
h1{font-size:1.4rem;margin:0 0 16px}.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.stat{background:#f9fafb;border:1px solid var(--border);border-radius:8px;padding:12px}
.stat .label{font-size:.8rem;color:var(--muted);margin-bottom:4px}
.stat .val{font-size:1.3rem;font-weight:600}
.btn{display:inline-block;padding:10px 16px;border-radius:8px;font-weight:500;cursor:pointer;border:1px solid transparent;text-decoration:none}
.btn.pri{background:var(--pri);color:#fff}.btn.sec{background:#fff;color:var(--pri);border-color:var(--pri)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.muted{color:var(--muted);font-size:.85rem}
a{color:var(--pri)}pre{background:#f3f4f6;padding:12px;border-radius:8px;overflow:auto;font-size:.8rem}
</style></head><body>
<h1>📊 AI 获客运营看板</h1>

<div class="card">
  <strong>系统模式：</strong><span id="mode">加载中…</span> &nbsp;
  <strong>部署：</strong>Vercel Serverless (PayPal 闭环入口)
</div>

<div class="card">
  <strong>实时 KPI</strong>
  <div class="grid" id="kpi">
    <div class="stat"><div class="label">触达</div><div class="val" id="kpi_touch">—</div></div>
    <div class="stat"><div class="label">深聊</div><div class="val" id="kpi_deepchat">—</div></div>
    <div class="stat"><div class="label">报价</div><div class="val" id="kpi_quote">—</div></div>
    <div class="stat"><div class="label">定金</div><div class="val" id="kpi_deposit">—</div></div>
    <div class="stat"><div class="label">收入</div><div class="val" id="kpi_revenue">—</div></div>
    <div class="stat"><div class="label">运营轮次</div><div class="val" id="kpi_ops">—</div></div>
  </div>
  <p class="muted">数据来源：本机 <code>run_all.py</code> 持久化到 <code>artifacts/state.json</code>；此看板定时拉取 <code>/api/state</code>（需本机端口映射或统一后端）</p>
</div>

<div class="card">
  <strong>订阅套餐（点一次即完成，无需再点任何按钮）</strong>
  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px" id="plans"></div>
  <p id="payStatus" style="display:none;margin-top:10px;font-size:14px"></p>
  <p class="muted">流程：点套餐 → 弹出 PayPal 窗口付款 → 窗口自动关闭、本页自动确认到账、订阅自动激活、收据自动发邮箱。全程不需要客户切回本页、点"返回"或等人工核账。</p>
</div>

<div class="card">
  <strong>最近动作</strong>
  <pre id="recent">加载中…</pre>
</div>

<script>
const API = "/api"; // relative to this Vercel deployment
async function fetchJson(url, opts) {
  const r = await fetch(url, opts);
  return r.ok ? r.json() : { error: await r.text() };
}
async function loadState() {
  try {
    const d = await fetchJson(API + "/state");
    if (d.error) throw d.error;
    document.getElementById("mode").textContent = d.mode || "unknown";
    document.getElementById("kpi_touch").textContent = d.kpi?.touch ?? "—";
    document.getElementById("kpi_deepchat").textContent = d.kpi?.deepchat ?? "—";
    document.getElementById("kpi_quote").textContent = d.kpi?.quote ?? "—";
    document.getElementById("kpi_deposit").textContent = d.kpi?.deposit ?? "—";
    document.getElementById("kpi_revenue").textContent = d.kpi?.revenue ?? "—";
    document.getElementById("kpi_ops").textContent = d.runtime?.total_operations ?? "—";
    if (d.subscription) {
      document.getElementById("recent").textContent = JSON.stringify(d.subscription, null, 2);
    }
    if (d.targets) {
      // could show targets
    }
  } catch (e) {
    document.getElementById("mode").innerHTML = '<span style="color:red">无法连接本机 API（需端口映射或统一后端）</span>';
    console.error(e);
  }
}
async function loadPlans() {
  try {
    const res = await fetchJson(API + "/plans");
    if (res.error) throw res.error;
    const plans = res.plans || {};
    const container = document.getElementById("plans");
    container.innerHTML = "";
    for (const [k, v] of Object.entries(plans)) {
      const a = document.createElement("a");
      a.className = "btn " + (v.is_popular ? "pri" : "sec");
      a.href = "/api/paypal/order?plan=" + k; // will be intercepted by JS below
      a.textContent = v.name + " · ¥" + v.price + (v.is_popular ? " ⭐" : "");
      a.onclick = (e) => { e.preventDefault(); buy(k); };
      container.appendChild(a);
    }
  } catch (e) {
    console.error(e);
  }
}
async function buy(plan) {
  // 注意: 本段位于服务端的反引号模板字符串内 —— 不能出现未转义的反引号，
  // 也不能出现 dollar-brace 表达式（会被服务端提前求值）。因此一律用普通引号 + 字符串拼接。
  var btn = document.querySelector('a[onclick*="' + plan + '"]');
  if (btn) { btn.disabled = true; btn.textContent = "下单中…"; }
  setStatus("正在创建订单…");
  let res;
  try {
    res = await fetchJson(API + "/paypal/order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan, user_id: "web_visitor" })
    });
  } catch (e) {
    setStatus("请求异常：" + e, true);
    if (btn) { btn.disabled = false; btn.textContent = "重试"; }
    return;
  }
  if (!res.approve_url) {
    setStatus("下单失败：" + (res.message || JSON.stringify(res)), true);
    if (btn) { btn.disabled = false; btn.textContent = "重试"; }
    return;
  }
  if (btn) { btn.textContent = "支付中…"; }
  setStatus("请在弹出的 PayPal 窗口完成支付，完成后本页会自动确认（无需任何点击）");

  // 零操作核心: 弹窗支付 → 弹窗自动关闭并通知本页 → 本页自动轮询确认
  const popup = window.open(res.approve_url, "paypal_" + plan,
      "width=520,height=700,left=" + Math.max(0, (screen.width - 520) / 2) + ",top=80");
  if (!popup) {
    // 弹窗被拦截 → 退回同页跳转（PayPal 仍会跳回 /pay/return 并自动回跳看板）
    window.location.href = res.approve_url;
    return;
  }
  watchOrder(res.order_id, plan, btn, popup);
}

// 监听弹窗回调 + 轮询订单状态，直到确认到账
function watchOrder(orderId, plan, btn, popup) {
  let tries = 0;
  const timer = setInterval(async () => {
    tries++;
    if (popup && popup.closed) { /* 弹窗已关，等状态 */ }
    if (tries > 60) { clearInterval(timer); setStatus("支付未完成（可在订单邮箱里查收据）", true); if (btn) { btn.disabled = false; btn.textContent = "重试"; } return; }
    try {
      const s = await fetchJson(API + "/paypal/status?order_id=" + encodeURIComponent(orderId));
      if (s && s.completed) {
        clearInterval(timer);
        setStatus("✅ 支付成功，订阅已自动激活（收据将自动发送到你的邮箱）");
        if (btn) { btn.textContent = "✅ 已购买"; }
        loadState();
        return;
      }
    } catch (e) { /* 轮询失败不打扰用户 */ }
  }, 2000);
}

// 接收 /pay/return 弹窗的 postMessage → 立刻确认（比轮询更快）
window.addEventListener("message", (ev) => {
  if (ev.data && ev.data.type === "paypal:completed") {
    setStatus("✅ 支付成功，订阅已自动激活（收据将自动发送到你的邮箱）");
    loadState();
  }
});
function setStatus(msg, isErr) {
  const el = document.getElementById("payStatus");
  if (!el) return;
  el.textContent = msg || "";
  el.style.color = isErr ? "#dc2626" : "#059669";
  el.style.display = msg ? "block" : "none";
}
loadState();
loadPlans();
setInterval(loadState, 10000);
</script>
</body></html>`;
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.send(html);
}