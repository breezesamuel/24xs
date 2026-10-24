const https = require('https');
https.get('https://api.github.com/repos/breezesamuel/24xs/contents/scripts/hidden/agent/hidden_outreach.mjs', {
  headers: {'User-Agent': 'test', 'Accept': 'application/vnd.github+json'}
}, res => {
  let d = '';
  res.on('data', c => d += c);
  res.on('end', () => {
    const j = JSON.parse(d);
    const buf = Buffer.from(j.content, 'base64');
    const text = buf.toString('utf8');
    const lines = text.split('\n');
    console.log('L31:', lines[31]);
    // Check the actual bytes of the Chinese part
    const chinesePart = lines[31].match(/content:'([^']+)'/);
    if (chinesePart) {
      const bytes = Buffer.from(chinesePart[1], 'utf8');
      console.log('Chinese bytes:', bytes.toString('hex'));
      console.log('Decoded back:', bytes.toString('utf8'));
    }
  });
}).on('error', console.error);