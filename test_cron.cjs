const https = require('https');
const options = {
  hostname: 'deploy-full-hpq4qbztw-solmount.vercel.app',
  path: '/api/test',
  method: 'GET',
  timeout: 30000
};
console.log('Starting request...');
const req = https.request(options, (res) => {
  console.log('Status:', res.statusCode);
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    console.log('Response:', data);
    process.exit(0);
  });
});
req.on('error', (e) => {
  console.error('Error:', e.message);
  process.exit(1);
});
req.on('timeout', () => {
  console.error('Timeout');
  req.destroy();
  process.exit(1);
});
req.end();
console.log('Request sent, waiting...');