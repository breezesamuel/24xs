from pathlib import Path
p = Path(r"F:/2026/24xs/11_数据资产/cf-pages/index.html")
html = p.read_text(encoding="utf-8")
if "资产目录" not in html:
    sec = '''<section class="section">
      <h2>资产目录（可验证）</h2>
      <p>总资产：<strong>1,000,000</strong> 条数字资产。每条附带 SHA256 校验证明（proof），可离线校验。</p>
      <div class="grid">
        <div class="card">
          <h3>资产清单</h3>
          <p><a href="/api/assets?limit=100">GET /api/assets</a></p>
        </div>
        <div class="card">
          <h3>校验接口</h3>
          <p>POST /api/verify</p>
        </div>
      </div>
    </section>'''
    if "</main>" in html:
        html = html.replace("</main>", sec + "</main>")
    else:
        html += sec
    p.write_text(html, encoding="utf-8")
print("ok")
