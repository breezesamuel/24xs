from pathlib import Path
p = Path(r"F:/2026/24xs/10_官网/index.html")
if p.exists():
    html = p.read_text(encoding="utf-8")
    if "/store.html" not in html:
        link = '<div style="margin-top:20px"><a href="/store.html" style="color:#22c55e;font-weight:600;">进入数字资产商城 &gt;</a></div>'
        if "</main>" in html:
            html = html.replace("</main>", link + "</main>")
        else:
            html += link
        p.write_text(html, encoding="utf-8")
print("ok")
