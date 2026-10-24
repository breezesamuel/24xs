const fs = require('fs');
const c = fs.readFileSync('scripts/hidden/agent/hidden_outreach.mjs', 'utf8');
const lines = c.split('\n');
console.log('L31:', lines[31]);
const m = lines[31].match(/content:'([^']+)'/);
if (m) {
  const b = Buffer.from(m[1], 'utf8');
  console.log('Local bytes:', b.toString('hex'));
  console.log('Decoded:', b.toString('utf8'));
}