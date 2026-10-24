import sqlite3
conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()
# Check notices columns
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='notices'")
print("NOTICES:", cur.fetchone()[0])
# Check if there are other tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("TABLES:", [r[0] for r in cur.fetchall()])
# Sample notice
cur.execute("SELECT * FROM notices LIMIT 1")
cols = [d[0] for d in cur.description]
row = cur.fetchone()
print("SAMPLE:", dict(zip(cols, row)))
conn.close()
