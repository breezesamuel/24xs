import sqlite3
total = 0
# yield
conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/yield_test.db")
cur = conn.cursor()
cur.execute("SELECT count(*) FROM n"); total += cur.fetchone()[0]
conn.close()
print("yield", total)
