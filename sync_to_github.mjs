// sync_to_github.mjs — 上传指定文件到 breezesamuel/24xs（Contents API）
// 用法: node sync_to_github.mjs <localPath> <repoPath>
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const [,, localPath, repoPath] = process.argv;
if(!localPath || !repoPath){
  console.error('usage: node sync_to_github.mjs <localPath> <repoPath>');
  process.exit(1);
}

const REPO = 'breezesamuel/24xs';
const API = `https://api.github.com/repos/${REPO}/contents/${repoPath}`;

const token = execSync('gh auth token', { encoding: 'utf8' }).trim();

// 读原始字节 → 转 LF → base64（避免 Windows CRLF 与编码问题）
const raw = fs.readFileSync(localPath);
const lf = Buffer.from(raw.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
const b64 = lf.toString('base64');

const headers = {
  Authorization: `Bearer ${token}`,
  Accept: 'application/vnd.github+json',
  'User-Agent': 'autoops-sync',
  'Content-Type': 'application/json',
};

async function main(){
  // 现有文件需要 sha
  let sha = null;
  try{
    const res = await fetch(API, { headers });
    if(res.ok){
      const j = await res.json();
      sha = j.sha;
    }
  }catch(e){}

  const body = JSON.stringify({
    message: `autoops: sync ${repoPath} (realops bridge)`,
    content: b64,
    ...(sha ? { sha } : {}),
    branch: 'main',
  });

  const res = await fetch(API, {
    method: 'PUT',
    headers,
    body,
  });
  const text = await res.text();
  if(res.ok){
    const j = JSON.parse(text);
    console.log(`OK ${repoPath} -> ${j.content?.html_url || 'committed'}`);
  }else{
    console.log(`FAIL ${res.status} ${repoPath}`);
    console.log(text.slice(0, 400));
    process.exit(1);
  }
}
main().catch(e => { console.error(e); process.exit(1); });
