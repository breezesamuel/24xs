const fs = require('fs');
const path = require('path');

const patterns = ['SO-20261010-RZ6L', 'receipt-20260101', 'buyer1@example.com', 'Buyer One', '260.00'];
const roots = ['C:/tmp/latest_run', 'C:/bingdashan/deploy-full', 'F:/2026/24xs/10_官网'];

function walk(dir) {
  try {
    const entries = fs.readdirSync(dir);
    for (const e of entries) {
      if (e === '.git' || e === 'node_modules') continue;
      const full = path.join(dir, e);
      const stat = fs.statSync(full);
      if (stat.isDirectory()) {
        walk(full);
      } else {
        try {
          const content = fs.readFileSync(full, 'utf8');
          for (const p of patterns) {
            if (content.includes(p)) {
              console.log('FOUND:', p, 'IN', full);
            }
          }
        } catch (err) {}
      }
    }
  } catch (err) {}
}

for (const r of roots) {
  console.log('Scanning:', r);
  walk(r);
}
console.log('SCAN DONE');
