#!/usr/bin/env node
/**
 * sync_deliverables.mjs — 把本轮已验证的 AutoOps 交付物通过 GitHub Contents API 同步到远程 main。
 *
 * 背景：本地 main 是以 autoops 为根的孤立历史（root 88d6ee7），无法 git push 到远程
 * （远程 root 9646a0d）。远程已有的同步通道是 Actions "realops bridge" + 本脚本
 * 同款 Contents API 逐文件 PUT（见 sync_github.mjs）。本脚本只碰 autoops 相关路径，
 * 不动仓库主线文件，逐文件 PUT 幂等，失败不影响其他文件。
 *
 * 用法: node sync_deliverables.mjs [--dry-run]
 */
import fs from 'fs';
import crypto from 'crypto';
import { execSync } from 'child_process';

const REPO = 'breezesamuel/24xs';
const BRANCH = 'main';

let token;
try {
  token = execSync('gh auth token', { encoding: 'utf8' }).trim();
} catch (e) {
  console.error('gh auth token 失败:', e.message);
  process.exit(1);
}

const DRY = process.argv.includes('--dry-run');

// [本地路径, 提交消息]——清单来自「本地 vs origin/main blob hash 对比」：
//   DIFFERS(内容不同) 或 MISSING_ON_REMOTE(远程没有) 才推送。
const FILES = [
  // ── 代码（本轮修复/新增，远程跑的是旧版或缺失）──
  ['scripts/hidden/commit_state.sh',                          'fix(commit_state): durable state writeback — health_status.json/alert_state.json now in writeback set'],
  ['scripts/hidden/agent/drive.js',                          'fix(cdp): implement 4 missing methods, remove illegal Input.enable, unref timers, id->targetId map'],
  ['scripts/hidden/agent/hidden_pay.mjs',                    'fix(pay): settleCallback + amount/order cross-check + reject audit (fail-closed)'],
  ['scripts/hidden/agent/hidden_watchdog.mjs',               'fix(watchdog): alert escalation/recovery/KV fallback/unknown-channel failure'],
  ['scripts/hidden/agent/hidden_realops.mjs',                'fix(realops): posted=true only on distributor exit 0'],
  ['scripts/hidden/agent/hidden_planner.mjs',                'fix(planner): honest plan/queue state'],
  ['scripts/hidden/agent/hidden_followup.mjs',               'fix(followup): plan-based chain'],
  ['scripts/hidden/agent/hidden_outreach.mjs',              'fix(outreach): honest drafted status (no fake sent), CRM stage=drafted'],
  ['scripts/hidden/agent/hidden_crm.mjs',                   'fix(crm): no auto order creation (simulated only), real orders from realops'],
  ['scripts/hidden/agent/hidden_oms.mjs',                   'fix(oms): only process real_storefront orders, skip simulated'],
  ['scripts/hidden/agent/hidden_planner.mjs',               'fix(planner): single schedule.json source, honest pendingPromos'],
  ['scripts/standards/restore_from_github.mjs',             'fix(restore): dynamic ROOT, lazy GH_TOKEN, isMain guard'],
  ['scripts/hidden/agent/hidden_guard.mjs',                  'refactor(guard): real policy module — loadGuard() export, CLI --check, orphan-flag audit'],
  ['scripts/hidden/agent/arcade-extra.js',                    'fix(arcade): /api/alert topic crash fix (KV fallback recovery)'],
  ['scripts/hidden/agent/content-distributor.js',            'fix(content): CDP 9223 gated dispatch'],
  ['scripts/hidden/crawler/hidden_crawler.mjs',               'fix(crawler): consume guard policy (robots/domain_allow/min_delay/write-domain) + isMain guard'],
  ['scripts/hidden/brain/hidden_brain.mjs',                   'feat(brain): standalone CLI cycle (verify stage 13/16 now real, not no-op)'],
  ['scripts/standards/select_wheel.mjs',                      'feat(standards): six-step anti-hallucination wheel vetting + security gate'],
  ['scripts/standards/verify_pipeline.cjs',                   'fix(verify): stage 13 = hidden_brain; default 180s (crawler token mode 156s real); args array for spawn'],
  ['scripts/hidden/hidden_orchestrator.mjs',                  'fix(orch): write heartbeat at tick start (not end) to fix CI watchdog false heartbeat_stale'],
  // ── 状态（线上大屏数据：health_status.json 此前从未成功回写远程）──
  // 注意：自 CI 的 commit_state.sh 起，health_status.json / alert_state.json 已由
  // GitHub Actions 每轮权威回写；手动同步会用过期本地状态覆盖新鲜线上状态，故移除。
  // ── 报告（纯文档增量，零风险）──
  ['standards/MODULE_GAP_AUDIT.md',                          'docs(standards): module gap audit P0/P1/P2'],
  ['standards/COMPETITOR_AND_BESTPRACTICE_AUDIT.md',         'docs(standards): competitor + best-practice audit'],
  ['standards/WHEEL_SELECTION_SOP.md',                       'docs(standards): wheel selection SOP v2 (security gate + six-step vetting)'],
  ['DEVELOPMENT_PROGRESS_REPORT.md',                         'docs: progress report sec9 gap audit'],
  // ── 工作流（去掉 || true 静默失败与假 cron ping；远程是旧版）──
  ['.github/workflows/hidden_autoops.yml',                   'fix(ci): do not swallow orchestrator exit code; drop fake Vercel cron ping'],
  // ── 推广分发计划（单一数据源：C:/bingdashan/promotion/schedule.json）──
  ['C:/bingdashan/promotion/schedule.json',                  'chore(promo): sync schedule.json from runtime dir (single source of truth)'],
];

// 以空文件 init 同步（checkFiles 只查存在性；不入库真实业务数据，仓库为 PUBLIC）
const INIT_EMPTY = [
  'autoops/hidden/leads_auto.jsonl',
  'autoops/hidden/crm_auto.jsonl',
  'autoops/hidden/real_orders.jsonl',
  'autoops/hidden/payments_auto.jsonl',
];

// git blob sha1：sha1("blob <n>\0" + content)
function gitBlobSha(buf) {
  const header = Buffer.from(`blob ${buf.length}\0`, 'utf8');
  return crypto.createHash('sha1').update(header).update(buf).digest('hex');
}

async function getRemoteSha(repoPath) {
  try {
    const res = await fetch(`https://api.github.com/repos/${REPO}/contents/${repoPath}?ref=${BRANCH}`, {
      headers: { Authorization: `Bearer ${token}`, 'User-Agent': '24xs-sync', Accept: 'application/vnd.github+json' }
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.sha || null;
  } catch (e) { return null; }
}

async function put(localPath, repoPath, message) {
  if (!fs.existsSync(localPath)) {
    console.log(`  [跳过] 本地不存在: ${localPath}`);
    return 'skip';
  }
  // LF 归一化（Windows 检出文件为 CRLF，同步统一 LF）
  const text = fs.readFileSync(localPath, 'utf8').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const buf = Buffer.from(text, 'utf8');
  const localSha = gitBlobSha(buf);
  const remoteSha = await getRemoteSha(repoPath);
  if (remoteSha && remoteSha === localSha) {
    console.log(`  [一致] ${repoPath}（跳过）`);
    return 'same';
  }
  if (DRY) {
    console.log(`  [dry-run] ${repoPath} remote=${remoteSha ? remoteSha.slice(0, 10) : '不存在'} local=${localSha.slice(0, 10)}`);
    return 'dry';
  }
  const body = { message, content: buf.toString('base64'), branch: BRANCH };
  if (remoteSha) body.sha = remoteSha;
  let res, data;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      res = await fetch(`https://api.github.com/repos/${REPO}/contents/${repoPath}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`, 'User-Agent': '24xs-sync',
          'Content-Type': 'application/json', Accept: 'application/vnd.github+json'
        },
        body: JSON.stringify(body)
      });
      data = await res.json().catch(() => ({}));
      if (res.ok) {
        console.log(`  [OK] ${repoPath} (${body.sha ? '更新' : '新增'})`);
        return 'ok';
      }
      if (res.status === 409 && attempt < 3) { // 并发提交导致 base sha 过期：刷新后重试
        const fresh = await getRemoteSha(repoPath);
        if (fresh) body.sha = fresh;
        continue;
      }
      break;
    } catch (e) {
      if (attempt === 3) { data = { message: e.message }; break; }
      await new Promise(r => setTimeout(r, 1000 * attempt));
    }
  }
  console.log(`  [失败] ${repoPath}: ${data.message || res.status}`);
  return 'fail';
}

async function putEmpty(repoPath) {
  const body = { message: 'chore(init): empty data file for watchdog checkFiles', content: '', branch: BRANCH };
  const remoteSha = await getRemoteSha(repoPath);
  if (remoteSha) body.sha = remoteSha;
  if (DRY) {
    console.log(`  [dry-run] ${repoPath} (empty) remote=${remoteSha ? remoteSha.slice(0, 10) : '不存在'}`);
    return 'dry';
  }
  let res, data;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      res = await fetch(`https://api.github.com/repos/${REPO}/contents/${repoPath}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`, 'User-Agent': '24xs-sync',
          'Content-Type': 'application/json', Accept: 'application/vnd.github+json'
        },
        body: JSON.stringify(body)
      });
      data = await res.json().catch(() => ({}));
      if (res.ok) {
        console.log(`  [OK] ${repoPath} (空文件${remoteSha ? '更新' : '新增'})`);
        return 'ok';
      }
      if (res.status === 409 && attempt < 3) {
        const fresh = await getRemoteSha(repoPath);
        if (fresh) body.sha = fresh;
        continue;
      }
      break;
    } catch (e) {
      if (attempt === 3) { data = { message: e.message }; break; }
      await new Promise(r => setTimeout(r, 1000 * attempt));
    }
  }
  console.log(`  [失败] ${repoPath}: ${data.message || res.status}`);
  return 'fail';
}

(async () => {
  console.log(`=== 同步交付物到 ${REPO} (branch=${BRANCH}) dry_run=${DRY} 共 ${FILES.length} 项 + ${INIT_EMPTY.length} 空 init ===`);
  const stats = { ok: 0, fail: 0, skip: 0, dry: 0, same: 0 };
  for (const [p, msg] of FILES) {
    const r = await put(p, p, msg);
    stats[r] = (stats[r] || 0) + 1;
  }
  // 空 init 文件：直接 PUT 空内容（不读本地，本地有真实数据不入库）
  for (const p of INIT_EMPTY) {
    const r = await putEmpty(p);
    stats[r] = (stats[r] || 0) + 1;
  }
  console.log(`=== 完成: ok=${stats.ok} same=${stats.same} fail=${stats.fail} skip=${stats.skip} dry=${stats.dry} ===`);
  process.exit(stats.fail ? 1 : 0);
})();
