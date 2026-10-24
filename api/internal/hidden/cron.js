const { spawn } = require('child_process');
const path = require('path');
const { fileURLToPath } = require('url');
const fs = require('fs');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../../../');

function getHeader(req, name) {
  // Vercel Node.js runtime: headers are lowercase
  return req.headers[name.toLowerCase()] || '';
}

module.exports = async function handler(req, res) {
  // 仅允许 Vercel Cron 或内部调用
  const auth = getHeader(req, 'authorization') || getHeader(req, 'x-vercel-cron') || '';
  if (!auth && getHeader(req, 'x-forwarded-for') !== 'vercel-cron') {
    // 允许本地测试和 Vercel Cron
    const isLocal = getHeader(req, 'x-vercel-ip') === '::1' || getHeader(req, 'x-vercel-ip')?.startsWith('127.');
    if (!isLocal) {
      return res.status(401).json({ ok: false, error: 'unauthorized' });
    }
  }

  // Vercel Cron 每日触发（GitHub Actions 每15分钟为主力）
  // 这里不直接拉起编排器（scripts 目录未打包），仅记录触发
  console.log('Vercel Cron triggered at', new Date().toISOString());

  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    ok: true,
    hidden: true,
    triggered: 'vercel_cron_daily_backup',
    note: 'Primary orchestrator runs via GitHub Actions every 15min',
    ts: new Date().toISOString()
  });
};

module.exports.config = {
  runtime: 'nodejs',
  maxDuration: 30
};