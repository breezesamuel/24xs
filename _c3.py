import sqlite3
total = 0
conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
cur = conn.cursor()
for t in ["geo_probes","corpus","leads","outreach","clients","money_in","money_out","runs","tasks"]:
    try:
        cur.execute("SELECT count(*) FROM " + t)
        total += cur.fetchone()[0]
    except:
        pass
conn.close()
print("factory", total)
