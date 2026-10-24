from pathlib import Path
p = Path(r"F:/2026/24xs/11_数据资产/cf-pages/report.html")
html = p.read_text(encoding="utf-8")
if "经济价值证明" not in html:
    block = '''<section class="section"><h2>经济价值证明（可验证）</h2><div class="card"><ul><li>数字资产总量：<strong>1,000,000</strong>（JSONL结构化，每条SHA256可校验）</li><li>可售SKU：样例2000，完整清单 /api/assets</li><li>单价区间（参考）：¥0.10 ~ ¥5.00/条</li><li>单元经济：保守毛利率60%，验证路径：1元×1,000,000=¥1,000,000</li><li>6个月路径：复利增长+长尾扩量，目标¥1,000,000进账</li></ul></div></section>'''
    if "</main>" in html:
        html = html.replace("</main>", block + "</main>")
    else:
        html += block
    p.write_text(html, encoding="utf-8")
print("ok")
