#!/usr/bin/env node
/**
 * hidden_orderaudit.mjs — 订单账本审计（后端，无前端展示）
 *
 * 每轮编排拉取门面订单全量（a=orders），分类：探针单（通道验证时产生）vs 真实单，
 * 触发门面 purge_probes 清理从未支付的探针单，并把审计结论落库：
 *   autoops/hidden/order_audit.jsonl  —— 每轮一行（总量/探针/真实/清掉了谁）
 *
 * 诚实原则：只删"我们自己的验证探针"且"从未支付"的单；真实用户单永不触碰。
 * 探针前缀白名单：BDS_PPTEST1/PPTEST2/CASElder/P1/P2/PROBEREF1（均为通道验证时所用 ref）。
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic } from './brain/hidden_brain.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const H = path.join(__dirname, '../../autoops/hidden');
const STORE = process.env.STOREFRONT_BASE || 'https://tools.highkingflower.com';
const SECRET = process.env.AUTOOPS_SECRET || '';
const AUD = path.join(H, 'order_audit.jsonl');
const PROBE = /^BDS_(PPTEST1|PPTEST2|CASElder|P1|P2|PROBEREF1)_/;

function append(file, obj) {
  try { fs.mkdirSync(H, { recursive: true }); fs.appendFileSync(file, JSON.stringify(obj) + '\n'); } catch (e) {}
}

async function main() {
  if (!SECRET) { console.log('[orderaudit] no AUTOOPS_SECRET, skip'); return 0; }
  // 1) 全量拉单（门面已有动作，n 上限 50 足够当前量级）
  const r1 = await fetch(`${STORE}/api/autoops.js?a=orders&n=50&k=${encodeURIComponent(SECRET)}`, { signal: AbortSignal.timeout(20000) });
  if (!r1.ok) { console.log('[orderaudit] orders http_' + r1.status); return 0; }
  const j1 = await r1.json();
  const orders = (j1 && j1.orders) || [];
  const probes = orders.filter(o => PROBE.test(o.out_trade_no) && o.status !== 'paid' && !o.paid_at);
  const real = orders.filter(o => !PROBE.test(o.out_trade_no));
  const realUnpaid = real.filter(o => o.status !== 'paid');

  // 2) 清理探针（门面二次校验同白名单+未支付）
  let purged = [];
  if (probes.length) {
    try {
      const r2 = await fetch(`${STORE}/api/autoops.js?a=purge_probes&k=${encodeURIComponent(SECRET)}`, { signal: AbortSignal.timeout(30000) });
      const j2 = await r2.json();
      purged = (j2 && j2.removed) || [];
    } catch (e) { console.log('[orderaudit] purge error', String(e).slice(0, 80)); }
  }

  // 3) 真实未支付单明细（供人工/后续跟进；绝不删除）
  const realDetail = realUnpaid.map(o => ({ id: o.out_trade_no, ref: o.ref, plan: o.plan, amount: o.amount, at: o.created_at }));

  const rec = { at: new Date().toISOString(), total: orders.length, probe_unpaid: probes.length, purged: purged.length,
                real_total: real.length, real_unpaid: realUnpaid.length, real_detail: realDetail };
  append(AUD, rec);
  episodic('order_audit', { total: rec.total, purged: rec.purged, real_unpaid: rec.real_unpaid });
  console.log(`[orderaudit] total=${rec.total} probe_purged=${rec.purged} real=${rec.real_total} real_unpaid=${rec.real_unpaid}`);
  return 0;
}
const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop());
if (isMain) main().then(() => process.exit(0)).catch(e => { console.error('[orderaudit] fatal', e); process.exit(1); });
