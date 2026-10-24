#!/usr/bin/env node
// Force re-upload hidden_planner.mjs with correct UTF-8 content
import fs from 'fs';
import { execSync } from 'child_process';

const REPO = 'breezesamuel/24xs';
const BRANCH = 'main';
const FILE = 'scripts/hidden/agent/hidden_planner.mjs';

let token;
try {
  token = execSync('gh auth token', { encoding: 'utf8' }).trim();
} catch (e) {
  console.error('gh auth token failed:', e.message);
  process.exit(1);
}

const raw = fs.readFileSync(FILE);
console.log('Local file size:', raw.length);
const b64 = raw.toString('base64');

const getRes = await fetch(`https://api.github.com/repos/${REPO}/contents/${FILE}?ref=${BRANCH}`, {
  headers: { Authorization: `Bearer ${token}`, 'User-Agent': '24xs-fix', 'Accept': 'application/vnd.github+json' }
});
let sha = null;
if (getRes.ok) {
  const data = await getRes.json();
  sha = data.sha;
  console.log('Current sha:', sha);
}

const body = { message: 'fix: restore correct UTF-8 encoding for hidden_planner.mjs', content: b64, branch: BRANCH };
if (sha) body.sha = sha;

const putRes = await fetch(`https://api.github.com/repos/${REPO}/contents/${FILE}`, {
  method: 'PUT',
  headers: { Authorization: `Bearer ${token}`, 'User-Agent': '24xs-fix', 'Content-Type': 'application/json', 'Accept': 'application/vnd.github+json' },
  body: JSON.stringify(body)
});

const result = await putRes.json();
if (putRes.ok) {
  console.log('[OK] File re-uploaded');
  console.log('New sha:', result.content?.sha);
} else {
  console.error('[FAILED]', result.message);
  process.exit(1);
}

// Verify
const verify = await fetch(`https://api.github.com/repos/${REPO}/contents/${FILE}?ref=${BRANCH}`, {
  headers: { Authorization: `Bearer ${token}`, 'Accept': 'application/vnd.github+json' }
});
const vdata = await verify.json();
const vbuf = Buffer.from(vdata.content, 'base64');
const vtext = vbuf.toString('utf8');
console.log('Verified size:', vbuf.length);
console.log('Has Chinese:', /[\u4e00-\u9fff]/.test(vtext));