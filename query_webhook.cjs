const Database = require('better-sqlite3');
const db = new Database('F:/2026/24xs/10_官网/webhook_queue.db', { readonly: true });

const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
console.log('Tables:', tables.map(t => t.name).join(', '));

for (const t of tables) {
  try {
    const rows = db.prepare(`SELECT * FROM "${t.name}" LIMIT 20`).all();
    console.log(`\n=== ${t.name} (${rows.length} rows shown) ===`);
    if (rows.length) {
      console.log('Cols:', Object.keys(rows[0]).join(', '));
    }
    const all = db.prepare(`SELECT COUNT(*) as c FROM "${t.name}"`).get();
    console.log('Total rows:', all.c);
    const matches = db.prepare(`SELECT * FROM "${t.name}"`).all().filter(r => JSON.stringify(r).includes('SO-20261010-RZ6L') || JSON.stringify(r).includes('buyer1@example.com') || JSON.stringify(r).includes('receipt-20260101') || JSON.stringify(r).includes('Buyer One'));
    if (matches.length) {
      console.log('*** MATCHES FOUND ***');
      matches.forEach(r => console.log(JSON.stringify(r)));
    }
  } catch (e) {
    console.log(`${t.name} err:`, e.message);
  }
}

db.close();
