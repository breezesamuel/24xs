import sqlite3, json, os
# CCGP
ccgp = r'F:\2026\24xs\11_数据资产\ccgp_production.db'
try:
    conn = sqlite3.connect(ccgp)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [x[0] for x in cur.fetchall()]
    stats = {}
    for t in tables:
        try:
            c = cur.execute('SELECT count(*) FROM "' + t + '"').fetchone()[0]
            stats[t] = c
        except Exception as e:
            stats[t] = 0
    conn.close()
    print('CCGP', json.dumps(stats, ensure_ascii=False))
except Exception as e:
    print('ERR', e)
