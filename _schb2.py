import sqlite3
conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='buyers'")
r = cur.fetchone()
if r: print(r[0])
conn.close()
