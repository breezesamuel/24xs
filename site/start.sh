#!/bin/sh
# start.sh - 同时启动 nginx 和 Node.js API 服务器

set -e

echo "=== bingdashan 阿里云启动 ==="

# 生成 API 服务器入口文件（聚合所有 Vercel 函数）
cat > /app/api-server.js <<'EOF'
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

// 加载所有 API 函数
const apiDir = '/app/functions/api';
const handlers = {};

if (fs.existsSync(apiDir)) {
  fs.readdirSync(apiDir).forEach(dir => {
    const funcPath = path.join(apiDir, dir, 'func.js');
    if (fs.existsSync(funcPath)) {
      try {
        handlers['/api/' + dir] = require(funcPath);
        console.log('Loaded API:', '/api/' + dir);
      } catch (e) {
        console.error('Failed to load', dir, ':', e.message);
      }
    }
  });
}

// 创建 HTTP 服务器
const server = http.createServer(async (req, res) => {
  const parsed = url.parse(req.url, true);
  const pathname = parsed.pathname;

  // 设置 CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Stripe-Signature');
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // 匹配处理器
  let matched = false;
  for (const [pattern, handler] of Object.entries(handlers)) {
    if (pathname === pattern || pathname.startsWith(pattern + '/') || pathname.startsWith(pattern + '?')) {
      matched = true;
      try {
        // 模拟 Vercel req/res
        const data = Object.assign({}, parsed.query);
        if (req.method === 'POST' || req.method === 'PUT') {
          let body = '';
          req.on('data', chunk => body += chunk);
          req.on('end', async () => {
            try { Object.assign(data, JSON.parse(body || '{}')); } catch (e) {}
            await handleRequest(req, res, pathname, data, handler);
          });
          return;
        }
        await handleRequest(req, res, pathname, data, handler);
      } catch (e) {
        console.error('Handler error:', e);
        res.writeHead(500, {'Content-Type': 'application/json'});
        res.end(JSON.stringify({ok:false,error:e.message}));
      }
      return;
    }
  }

  if (!matched) {
    res.writeHead(404, {'Content-Type': 'application/json'});
    res.end(JSON.stringify({ok:false,error:'not found',path:pathname}));
  }
});

async function handleRequest(req, res, pathname, data, handler) {
  const send = (code, obj) => {
    res.writeHead(code, {'Content-Type': 'application/json; charset=utf-8'});
    res.end(JSON.stringify(obj));
  };
  const text = (code, str, ct) => {
    res.writeHead(code, {'Content-Type': ct || 'text/plain; charset=utf-8'});
    res.end(str);
  };
  const readBody = () => new Promise(r => { let d=''; req.on('data',c=>d+=c); req.on('end',()=>r(d)); });
  const raw = await readBody();
  let form = {};
  if (raw) {
    try { Object.assign(form, JSON.parse(raw)); } catch (e) {
      try { const u = new URL('http://x/?'+raw); u.searchParams.forEach((v,k)=>form[k]=v); } catch(e2) {}
    }
  }
  const merged = Object.assign({}, data, form);
  try {
    await handler(req, res, merged);
  } catch (e) {
    console.error('Handler threw:', e);
    send(500, {ok:false,error:e.message});
  }
}

const PORT = process.env.PORT || 3000;
server.listen(PORT, '127.0.0.1', () => {
  console.log('API server listening on 127.0.0.1:' + PORT);
});
EOF

# 启动 Node.js API 服务器（后台）
echo "Starting Node.js API server on port 3000..."
node /app/api-server.js &
API_PID=$!

# 等待 API 就绪
sleep 2

# 启动 nginx（前台）
echo "Starting nginx..."
exec nginx -g 'daemon off;'