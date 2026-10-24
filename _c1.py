import sqlite3
total = 0
conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()
cur.execute("SELECT count(*) FROM notices"); total += cur.fetchone()[0]
cur.execute("SELECT count(*) FROM buyers"); total += cur.fetchone()[0]
cur.execute("SELECT count(*) FROM grid"); total += cur.fetchone()[0]
conn.close()
print("ccgp", total)
