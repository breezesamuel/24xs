import sqlite3
conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()
cur.execute("SELECT count(*) FROM notices")
print(cur.fetchone()[0])
conn.close()
