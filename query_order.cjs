const Database = require('better-sqlite3');
const db = new Database('F:/2026/24xs/11_数据资产/ccgp_production.db', { readonly: true });

// buyers table
try {
  const buyers = db.prepare('SELECT * FROM buyers').all();
  console.log('buyers count:', buyers.length);
  if (buyers.length) {
    console.log('buyers cols:', Object.keys(buyers[0]).join(', '));
    const m = buyers.filter(r => JSON.stringify(r).includes('buyer1') || JSON.stringify(r).includes('Buyer One') || JSON.stringify(r).includes('example.com'));
    console.log('buyers matching test data:', m.length);
    m.forEach(r => console.log(JSON.stringify(r)));
    console.log('sample buyers:');
    buyers.slice(0, 5).forEach(r => console.log(JSON.stringify(r).slice(0, 300)));
  }
} catch (e) { console.log('buyers err', e.message); }

// grid table
try {
  const grid = db.prepare('SELECT * FROM grid').all();
  console.log('\ngrid count:', grid.length);
  if (grid.length) console.log('grid cols:', Object.keys(grid[0]).join(', '));
  const m = grid.filter(r => JSON.stringify(r).includes('SO-20261010-RZ6L') || JSON.stringify(r).includes('buyer1@example'));
  console.log('grid matches:', m.length);
  m.forEach(r => console.log(JSON.stringify(r)));
} catch (e) { console.log('grid err', e.message); }

db.close();
