import sqlite3, json
db = r'F:\2026\24xs\99_产出\_data\factory.sqlite3'
try:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [x[0] for x in cur.fetchall()]
    stats = {}
    for t in tables:
        try:
            c = cur.execute('SELECT count(*) FROM "' + t + '"').fetchone()[0]
            stats[t] = c
        except:
            stats[t] = 0
    conn.close()
    print('FACT', json.dumps(stats))
except Exception as e:
    print('ERR', e)
