const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');
function findDb(dir){let e;try{e=fs.readdirSync(dir,{withFileTypes:true})}catch{return null}for(const x of e){const p=path.join(dir,x.name);if(x.isDirectory()){const r=findDb(p);if(r)return r}else if(x.name==='commerce.db')return p}return null}
const db = new Database(findDb('F:/2026'), { readonly: true });

console.log('=== settings (site/payment) ===');
db.prepare("SELECT key,value FROM settings").all()
  .filter(r => /url|name|domain|payment|alipay|mail|host|api/i.test(r.key))
  .forEach(r => console.log('  ' + r.key + ' = ' + String(r.value).slice(0, 120)));

console.log('\n=== 5 most recent orders ===');
db.prepare('SELECT id,order_no,customer_id,total,currency,status,payment_status,payment_method,placed_at FROM orders ORDER BY id DESC LIMIT 5').all()
  .forEach(r => console.log('  ' + JSON.stringify(r)));

console.log('\n=== customers named buyer/one ===');
db.prepare("SELECT id,email,name,country,orders_count,ltv FROM customers").all()
  .filter(r => /buyer|one|example\.com/i.test((r.email||'')+(r.name||'')))
  .forEach(r => console.log('  ' + JSON.stringify(r)));

console.log('\n=== payments providers ===');
db.prepare('SELECT provider,COUNT(*) n FROM payments GROUP BY provider').all()
  .forEach(r => console.log('  ' + JSON.stringify(r)));
db.close();
