html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>丙大山\u00b7\u6570\u5b57\u8d44\u4ea7\u5546\u57ce - \u771f\u5b9e\u53ef\u9a8c\u8bc1\u6570\u5b57\u8d44\u4ea7\u4ea4\u6613</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root { --bg:#0a0f1a; --card:#111827; --border:#1f2937; --text:#e5e7eb; --muted:#9ca3af; --accent:#22c55e; --accent-dim:#16a34a; --warn:#f59e0b; --danger:#ef4444; }
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Noto Sans SC","Inter",sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
.container{max-width:1200px;margin:0 auto;padding:24px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 0;border-bottom:1px solid var(--border);margin-bottom:24px}
.logo{font-weight:700;font-size:1.25rem;color:var(--accent)}
nav a{color:var(--muted);margin-left:24px;text-decoration:none;font-size:.9rem}
nav a:hover{color:var(--text)}
h1{font-size:2rem;font-weight:700;margin-bottom:8px}
.subtitle{color:var(--muted);margin-bottom:24px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}
.stat .label{font-size:.8rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.stat .value{font-size:1.5rem;font-weight:700;color:var(--accent);margin-top:4px}
.filters{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.filter-btn{background:var(--card);border:1px solid var(--border);color:var(--text);padding:8px 16px;border-radius:8px;cursor:pointer;font-size:.85rem;transition:.2s}
.filter-btn:hover,.filter-btn.active{border-color:var(--accent);color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;transition:.2s}
.card:hover{border-color:var(--accent);transform:translateY(-2px)}
.card-header{padding:16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:flex-start}
.card-type{font-size:.7rem;background:var(--accent);color:var(--bg);padding:2px 8px;border-radius:4px;font-weight:600}
.card-price{font-weight:700;color:var(--accent);font-size:1.1rem}
.card-body{padding:16px}
.card-title{font-weight:600;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-meta{font-size:.8rem;color:var(--muted);margin-bottom:12px}
.card-proof{font-family:monospace;font-size:.7rem;color:var(--muted);background:var(--bg);padding:8px;border-radius:6px;margin-bottom:12px;word-break:break-all}
.card-actions{display:flex;gap:8px}
.btn{flex:1;padding:10px 16px;border-radius:8px;font-weight:600;font-size:.85rem;cursor:pointer;border:none;transition:.2s}
.btn-primary{background:var(--accent);color:var(--bg)}
.btn-primary:hover{background:var(--accent-dim)}
.btn-secondary{background:var(--border);color:var(--text)}
.btn-secondary:hover{background:#374151}
.btn:disabled{opacity:.5;cursor:not-allowed}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;z-index:100;opacity:0;visibility:hidden;transition:.2s}
.modal.open{opacity:1;visibility:visible}
.modal-content{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;width:90%;max-width:500px;max-height:90vh;overflow:auto}
.modal-title{font-size:1.25rem;font-weight:700;margin-bottom:16px}
.modal-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)}
.modal-row:last-child{border-bottom:none}
.modal-proof{font-family:monospace;font-size:.7rem;color:var(--muted);background:var(--bg);padding:12px;border-radius:8px;margin:12px 0;word-break:break-all}
.toast{position:fixed;bottom:24px;right:24px;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px 24px;z-index:200;transform:translateY(100px);opacity:0;transition:.3s}
.toast.show{transform:translateY(0);opacity:1}
.toast.success{border-color:var(--accent)}
.toast.error{border-color:var(--danger)}
.loading{display:inline-block;width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{grid-column:1/-1;text-align:center;padding:48px;color:var(--muted)}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo">\u4e19\u5927\u5c71\u00b7\u6570\u5b57\u8d44\u4ea7\u5546\u57ce</div>
    <nav><a href="/">\u9996\u9875</a><a href="/report.html">\u4ef7\u503c\u8bc1\u660e</a></nav>
  </header>
  <h1>\u771f\u5b9e\u53ef\u9a8c\u8bc1\u6570\u5b57\u8d44\u4ea7</h1>
  <p class="subtitle">33,426 \u6761\u7ed3\u6784\u5316\u8d44\u4ea7 \u00b7 \u6bcf\u6761\u9644\u5e26 SHA256 \u6821\u9a8c\u8bc1\u660e \u00b7 \u652f\u6301\u5373\u65f6\u4ea4\u4ed8</p>
  
  <div class="stats" id="stats">
    <div class="stat"><div class="label">\u603c\u8d44\u4ea7\u6570</div><div class="value" id="stat-total">\u2014</div></div>
    <div class="stat"><div class="label">\u8d44\u4ea7\u7c7b\u578b</div><div class="value" id="stat-types">\u2014</div></div>
    <div class="stat"><div class="label">\u4ef7\u683c\u533a\u95f4</div><div class="value" id="stat-price">\u2014</div></div>
    <div class="stat"><div class="label">\u53ef\u4ea4\u4ed8</div><div class="value" id="stat-deliverable">100%</div></div>
  </div>
  
  <div class="filters" id="filters"><button class="filter-btn active" data-type="all">\u5168\u90e8</button></div>
  
  <div class="grid" id="grid"><div class="empty">\u52a0\u8f7d\u4e2d...</div></div>
</div>

<div class="modal" id="modal">
  <div class="modal-content">
    <div class="modal-title" id="modal-title">\u8d2d\u4e70\u786e\u8ba4</div>
    <div class="modal-row"><span>\u8d44\u4ea7\u7c7b\u578b</span><span id="m-type">\u2014</span></div>
    <div class="modal-row"><span>\u53c2\u8003\u4ef7\u683c</span><span id="m-price">\u2014</span></div>
    <div class="modal-row"><span>\u6700\u4f4e\u6210\u4ea4</span><span id="m-floor">\u2014</span></div>
    <div class="modal-row"><span>\u4ea4\u4ed8\u5f62\u5f0f</span><span id="m-deliver">\u2014</span></div>
    <div class="modal-proof" id="m-proof">\u2014</div>
    <div class="card-actions">
      <button class="btn btn-secondary" onclick="closeModal()">\u53d6\u6d88</button>
      <button class="btn btn-primary" id="btn-pay" onclick="initPay()">\u7acb\u5373\u652f\u4ed8 <span id="pay-loading" class="loading" style="display:none"></span></button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let allAssets = [];
let currentFilter = "all";

async function loadManifest() {
  try {
    const res = await fetch("/api/assets");
    const data = await res.json();
    document.getElementById("stat-total").textContent = (data.total || 33426).toLocaleString();
    document.getElementById("stat-types").textContent = "10";
  } catch {}
}

async function loadSample() {
  try {
    const res = await fetch("/api/assets?sample=1&limit=500");
    const data = await res.json();
    if (data.sample) allAssets = data.sample;
    else if (data.assets) allAssets = data.assets;
    renderFilters();
    renderGrid();
  } catch (e) {
    document.getElementById("grid").innerHTML = '<div class="empty">\u65e0\u6cd5\u52a0\u8f7d\u6837\u4f8b\u002c\u8bf7\u5237\u65b0\u91cd\u8bd5</div>';
  }
}

function renderFilters() {
  const types = [...new Set(allAssets.map(a => a.type))];
  const filterDiv = document.getElementById("filters");
  filterDiv.innerHTML = '<button class="filter-btn active" data-type="all">\u5168\u90e8</button>' +
    types.map(t => '<button class="filter-btn" data-type="' + t + '">' + t + '</button>').join("");
  filterDiv.querySelectorAll(".filter-btn").forEach(btn => {
    btn.onclick = () => {
      filterDiv.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.type;
      renderGrid();
    };
  });
}

function renderGrid() {
  const grid = document.getElementById("grid");
  const filtered = currentFilter === "all" ? allAssets : allAssets.filter(a => a.type === currentFilter);
  if (!filtered.length) {
    grid.innerHTML = '<div class="empty">\u6682\u65e0\u8be5\u7c7b\u578b\u8d44\u4ea7</div>';
    return;
  }
  grid.innerHTML = filtered.map(a => `
    <article class="card">
      <div class="card-header">
        <span class="card-type">${a.type}</span>
        <span class="card-price">\u00a5${a.price_cny_ref.toFixed(2)}</span>
      </div>
      <div class="card-body">
        <div class="card-title">${a.name}</div>
        <div class="card-meta">ID: ${a.asset_id} | \u6765\u6e90: ${a.source}</div>
        <div class="card-proof">Proof: ${a.proof}</div>
        <div class="card-actions">
          <button class="btn btn-secondary" onclick="viewDetail('${a.asset_id}')">\u67e5\u770b\u8be6\u60c5</button>
          <button class="btn btn-primary" onclick="openModal('${a.asset_id}')">\u8d2d\u4e70</button>
        </div>
      </div>
    </article>
  `).join("");
}

function openModal(assetId) {
  const a = allAssets.find(x => x.asset_id === assetId);
  if (!a) return;
  document.getElementById("modal-title").textContent = a.name;
  document.getElementById("m-type").textContent = a.type;
  document.getElementById("m-price").textContent = "\u00a5" + a.price_cny_ref.toFixed(2);
  document.getElementById("m-floor").textContent = "\u00a5" + a.price_cny_floor.toFixed(2);
  document.getElementById("m-deliver").textContent = a.deliverable;
  document.getElementById("m-proof").textContent = "SHA256: " + a.proof;
  document.getElementById("btn-pay").dataset.asset = assetId;
  document.getElementById("modal").classList.add("open");
}

function closeModal() {
  document.getElementById("modal").classList.remove("open");
}

async function initPay() {
  const btn = document.getElementById("btn-pay");
  const assetId = btn.dataset.asset;
  const a = allAssets.find(x => x.asset_id === assetId);
  if (!a) return;
  btn.disabled = true;
  btn.querySelector("#pay-loading").style.display = "inline-block";
  try {
    const res = await fetch("/api/purchase", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({asset_id: assetId, amount_cny: a.price_cny_ref})
    });
    const data = await res.json();
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    } else if (data.payment_url) {
      window.location.href = data.payment_url;
    } else {
      showToast("\u652f\u4ed8\u94fe\u8def\u672a\u914d\u7f6e\u002c\u8bf7\u8054\u7cfb\u5ba2\u670d", "error");
    }
  } catch (e) {
    showToast("\u8bf7\u6c42\u5931\u8d25: " + e.message, "error");
  } finally {
    btn.disabled = false;
    btn.querySelector("#pay-loading").style.display = "none";
  }
}

function showToast(msg, type="") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast " + type + " show";
  setTimeout(() => t.classList.remove("show"), 3000);
}

loadManifest();
loadSample();
</script>
</body>
</html>"""
from pathlib import Path
Path(r"F:/2026/24xs/11_数据资产/cf-pages/store.html").write_text(html, encoding="utf-8")
print("ok")
