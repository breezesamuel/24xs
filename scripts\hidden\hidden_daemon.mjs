#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import { episodic } from './brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../');
const H = path.join(ROOT, 'autoops/hidden');
const LOG = path.join(H, 'log/daemon.log');
const HB = path.join(H, 'state/heartbeat.json');
const HEALTH = path.join(H, 'state/health.json');

const INT = parseInt(process.env.HIDDEN_INT_MIN || '15', 10) * 60 * 1000;
const MAX_CONSECUTIVE_FAILURES = 5;
const FAILURE_BACKOFF_MS = 5 * 60 * 1000; // 5 min backoff

let consecutiveFailures = 0;
let isShuttingDown = false;
let currentOrchestratorPid = null;

function log(m){
  const ts = new Date().toISOString();
  const line = JSON.stringify({ts, src:'hidden_daemon', m});
  console.log(line);
  try { fs.appendFileSync(LOG, line + '\n'); } catch(e){}
}

function writeHealth(status, details = {}){
  try {
    fs.writeFileSync(HEALTH, JSON.stringify({
      status,
      last_check: new Date().toISOString(),
      uptime_ms: Date.now() - startTime,
      consecutive_failures: consecutiveFailures,
      pid: process.pid,
      ...details
    }, null, 2));
  } catch(e){}
}

const startTime = Date.now();

function run(){
  return new Promise(resolve => {
    const p = spawn('node', [path.join(__dirname, 'hidden_orchestrator.mjs')], {
      cwd: ROOT,
      stdio: 'inherit',
      detached: false
    });
    currentOrchestratorPid = p.pid;
    writeHealth('running', { orchestrator_pid: p.pid });

    let resolved = false;
    const timeout = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        log('orchestrator_timeout');
        try { p.kill('SIGTERM'); } catch(e){}
        setTimeout(() => { try { p.kill('SIGKILL'); } catch(e){} }, 5000);
        resolve({ code: 124, timed_out: true });
      }
    }, 10 * 60 * 1000); // 10 min max per orchestrator run

    p.on('close', code => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timeout);
      currentOrchestratorPid = null;
      resolve({ code });
    });
    p.on('error', err => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timeout);
      currentOrchestratorPid = null;
      log({ orchestrator_spawn_error: err.message });
      resolve({ code: 1, error: err.message });
    });
  });
}

async function tick(){
  if (isShuttingDown) return { code: 0, skipped: true };

  log('tick_start');
  const result = await run();

  if (result.code === 0) {
    consecutiveFailures = 0;
  } else {
    consecutiveFailures++;
    log({ tick_failed: true, code: result.code, consecutive_failures: consecutiveFailures });
  }

  try {
    fs.writeFileSync(HB, JSON.stringify({
      last_heartbeat: new Date().toISOString(),
      interval_min: INT / 60000,
      status: result.code === 0 ? 'ok' : 'warn',
      mode: 'full_autonomous_hidden',
      consecutive_failures: consecutiveFailures
    }, null, 2));
  } catch(e){}

  writeHealth(result.code === 0 ? 'healthy' : 'degraded', {
    last_tick_code: result.code,
    consecutive_failures: consecutiveFailures
  });

  episodic('hidden_daemon_tick', { code: result.code, consecutive_failures: consecutiveFailures });

  return result;
}

async function gracefulShutdown(signal){
  if (isShuttingDown) return;
  isShuttingDown = true;
  log({ shutdown_signal: signal, pid: process.pid });

  writeHealth('shutting_down', { signal });

  // Kill current orchestrator if running
  if (currentOrchestratorPid) {
    try {
      process.kill(currentOrchestratorPid, 'SIGTERM');
      await new Promise(r => setTimeout(r, 3000));
      try { process.kill(currentOrchestratorPid, 'SIGKILL'); } catch(e){}
    } catch(e){}
  }

  log('shutdown_complete');
  writeHealth('stopped', { signal });
  process.exit(0);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGHUP', () => gracefulShutdown('SIGHUP'));

async function loop(){
  if(!fs.existsSync(H)) fs.mkdirSync(H,{recursive:true});
  if(!fs.existsSync(path.dirname(LOG))) fs.mkdirSync(path.dirname(LOG),{recursive:true});
  if(!fs.existsSync(path.dirname(HB))) fs.mkdirSync(path.dirname(HB),{recursive:true});
  if(!fs.existsSync(path.dirname(HEALTH))) fs.mkdirSync(path.dirname(HEALTH),{recursive:true});

  log(`start hidden_daemon int=${INT/60000}min`);
  writeHealth('starting');

  await tick();

  while(!isShuttingDown){
    let waitMs = INT + Math.floor(Math.random() * 45000); // 0-45s jitter

    // Exponential backoff on repeated failures
    if (consecutiveFailures > 0) {
      waitMs = Math.min(waitMs + FAILURE_BACKOFF_MS * Math.pow(2, Math.min(consecutiveFailures - 1, 4)), 60 * 60 * 1000); // max 1 hour
    }

    log({ waiting_ms: waitMs, consecutive_failures: consecutiveFailures });
    await new Promise(r => setTimeout(r, waitMs));
    await tick();
  }
}

loop();