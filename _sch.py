import sqlite3
conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='notices'")
res = cur.fetchone()
if res:
    print(res[0])
conn.close()
