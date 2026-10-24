const Database = require('better-sqlite3');
const db = new Database('F:/2026/24xs/11_数据资产/ccgp_production.db', { readonly: true });

const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
console.log('Tables:', tables.map(t => t.name).join(', '));

for (const t of tables) {
  const rows = db.prepare(`SELECT * FROM "${t.name}" LIMIT 5`).all();
  if (rows.length > 0) {
    const cols = Object.keys(rows[0]);
    const match = rows.filter(r => JSON.stringify(r).includes('SO-20261010-RZ6L') || JSON.stringify(r).includes('260.00') || JSON.stringify(r).includes('buyer1@example.com'));
    if (match.length > 0) {
      console.log(`\n=== ${t.name} ===`);
      console.log('Columns:', cols.join(', '));
      match.forEach(r => console.log(JSON.stringify(r)));
    }
  }
}

db.close();
