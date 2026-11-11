'use strict';
// bounty.js - 劳动换币 (bounty 任务) 账本 (赚钱回路新维度: 完成任务得币)
// 语义: 平台发布 bounty 任务 (劳动), 用户完成后 *服务端* 验证 -> 记币。
//   区别于 "写作赚币" (内容质量门禁): bounty 是 *任务完成度* 门禁 (证据 + 校验)。
// 原则 (诚实, 防刷):
//   - 服务端权威: 币额/完成判定 由服务器做, 客户端不能自报 "我做完了给我 100 币"
//   - 防刷: 每任务每 ref 一次 (task_id 去重); 需提交 *证据* (proof, 非空 + 哈希) 才可记
//   - 不刷量: 任务由 owner 定义 (task catalog), 不自动造任务; 完成需真实证据
// 存储: 复用 cashback/writerewards 同款 KV/Supabase + CN 文件回退 (key 前缀 by:)
// Endpoints: /api/bounty?action=tasks|summary|ledger|claim|settle
const DEFAULT_BOUNTY_TOKENS = (function(){ var v=parseFloat(process.env.BOUNTY_TOKENS); return (isFinite(v)&&v>0)?v:20; })();
var MAX_CLAIMS_PER_REF = 50;              // 单 ref 累计领取上限 (防无限刷)
var SETTLE_THRESHOLD = 100;              // 累计币达到才可提现
var ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

// ---- 存储 (KV/Supabase + CN 文件回退, key 前缀 by:) ----
function up(){try{var u=process.env.SUPABASE_URL,k=process.env.SUPABASE_SERVICE_KEY||process.env.SUPABASE_KEY;return(u&&k)?{u:String(u).replace(/\/$/,''),k:k}:null;}catch(e){return null;}}
function kv(){try{var u=process.env.KV_REST_API_URL||process.env.UPSTASH_REDIS_REST_URL,t=process.env.KV_REST_API_TOKEN||process.env.UPSTASH_REDIS_REST_TOKEN;return(u&&t)?{u:String(u).replace(/\/$/,''),t:t}:null;}catch(e){return null;}}
function fileStore(){try{var d=process.env.FILE_STORE_DIR;return(d&&String(d).trim())?String(d).trim():null;}catch(e){return null;}}
function byFilePath(key){var dir=fileStore();if(!dir)return null;var safe=String(key).replace(/[^A-Za-z0-9_.:-]/g,'_');try{var p=require('path');return p.join(dir,'bounty',safe+'.json');}catch(e){return null;}}
async function byFileGet(key){var p=byFilePath(key);if(!p)return null;try{return await require('node:fs/promises').readFile(p,'utf8');}catch(e){return null;}}
async function byFileSet(key,val){var p=byFilePath(key);if(!p)return false;try{var fs=require('node:fs/promises');var P=require('path');await fs.mkdir(P.dirname(p),{recursive:true});await fs.writeFile(p,val,'utf8');return true;}catch(e){return false;}}
async function kget(k){try{var m=kv();var r=m?await fetch(m.u+'/get/'+encodeURIComponent(k),{headers:{Authorization:'Bearer '+m.t},signal:AbortSignal.timeout(8000)}):null;if(r){var j=await r.json();if(j&&j.result!==null&&j.result!==undefined)return j.result;}return null;}catch(e){return null;}}
async function kset(k,v){try{var m=kv();if(m){var body=(typeof v==='string')?v:JSON.stringify(v);var r=await fetch(m.u+'/set/'+encodeURIComponent(k),{method:'POST',headers:{Authorization:'Bearer '+m.t,'Content-Type':'application/json'},body:body,signal:AbortSignal.timeout(8000)});if(r.ok)return true;}return false;}catch(e){return false;}}
async function dget(k){try{var v=await kget(k);if(v!==null&&v!==undefined)return v;}catch(e){}var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/bounty_kv?k=eq.'+encodeURIComponent(k)+'&select=v',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});var j=await r.json();if(Array.isArray(j)&&j[0])return j[0].v;}catch(e){}}if(fileStore()){var f=await byFileGet(k);if(f!==null&&f!==undefined)return f;}return null;}
async function dset(k,v){if(await kset(k,v))return true;var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/bounty_kv',{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify([{k:k,v:v}]),signal:AbortSignal.timeout(8000)});if(r.ok)return true;}catch(e){}}if(fileStore()&&await byFileSet(k,v))return true;return false;}
function hasStore(){return !!(kv()||up()||fileStore());}

function keyOf(ref){return 'by:'+ref;}
function okRef(ref){return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref||''));}
async function load(ref){var raw=await dget(keyOf(ref));if(!raw)return [];try{var a=JSON.parse(raw);return Array.isArray(a)?a:[];}catch(e){return [];}}
async function save(ref,arr){return dset(keyOf(ref),JSON.stringify(arr));}

// 任务目录 (owner 可经 env 扩展; 默认 3 个示范任务)
function taskCatalog(){
  var base = [
    { id:'by_introduce', label:'介绍双足机器人项目给 3 人', reward: DEFAULT_BOUNTY_TOKENS, proof_min: 20 },
    { id:'by_trial', label:'试用 7 天并反馈 1 条改进建议', reward: DEFAULT_BOUNTY_TOKENS, proof_min: 30 },
    { id:'by_review', label:'写一篇使用评测 (>=200 字)', reward: Math.round(DEFAULT_BOUNTY_TOKENS*2), proof_min: 200 },
  ];
  try { var extra = JSON.parse(process.env.BOUNTY_TASKS || '[]'); if (Array.isArray(extra)) base = base.concat(extra); } catch(e){}
  return base;
}

// 完成校验 (服务端): 任务存在 + 证据非空且达到该任务 proof_min + 任务未重复
function verifyClaim(taskId, proof) {
  var t = null;
  for (var i=0;i<taskCatalog().length;i++){ if(taskCatalog()[i].id===taskId){ t=taskCatalog()[i]; break; } }
  if (!t) return { ok:false, reason:'unknown_task', task_id: taskId };
  var p = String(proof||'').trim();
  if (p.length < (t.proof_min||0)) return { ok:false, reason:'proof_too_short', need: t.proof_min, got: p.length };
  return { ok:true, task: t, proof_hash: contentHash(p), reward: t.reward };
}
function contentHash(s){var h=0x811c9dc5;for(var i=0;i<s.length;i++){h^=s.charCodeAt(i);h=(h*0x01000193)>>>0;}return h.toString(16);}

// claim: 提交任务完成 -> 服务端校验 -> 记币 (幂等 by task_id+ref)
async function claim(ref, taskId, proof, meta) {
  ref = String(ref||'').slice(0,64);
  if (!okRef(ref)) return { ok:false, error:'missing_or_invalid_ref' };
  if (!hasStore()) return { ok:false, error:'store_failed' };
  var v = verifyClaim(taskId, proof);
  if (!v.ok) return { ok:false, error:v.reason, need: v.need, got: v.got, task_id: taskId };
  var arr = await load(ref);
  for (var i=0;i<arr.length;i++){ if(arr[i] && arr[i].task_id===taskId && arr[i].proof_hash===v.proof_hash) return { ok:true, duplicate:true, entry:arr[i] }; }
  // 单 ref 累计领取上限 (防无限刷): 已领取任务数 (非 reject)
  var claimedCount = arr.filter(function(e){return e && e.status!=='rejected';}).length;
  if (claimedCount >= MAX_CLAIMS_PER_REF) return { ok:false, error:'claim_cap_reached', cap: MAX_CLAIMS_PER_REF };
  var entry = {
    id: 'BY'+Date.now().toString(36)+Math.floor(Math.random()*1e6).toString(36),
    task_id: String(taskId).slice(0,40),
    task_label: v.task.label,
    reward: v.reward,
    proof_hash: v.proof_hash,
    day: new Date().toISOString().slice(0,10),
    at: Date.now(),
    status: 'pending'
  };
  arr.push(entry);
  var ok = await save(ref, arr);
  if (!ok) return { ok:false, error:'store_failed' };
  return { ok:true, entry: entry, tokens_awarded: v.reward };
}

function summarize(ref, arr) {
  var total=0, pending=0, settled=0, n=0;
  for (var i=0;i<arr.length;i++){
    var e=arr[i]||{}; if(e.status==='rejected')continue;
    if(e.status==='settled'){settled+=e.reward||0;n++;}else pending+=e.reward||0;
    total+=e.reward||0;
  }
  return { ref:ref, task_count: taskCatalog().length, max_claims: MAX_CLAIMS_PER_REF, settle_threshold: SETTLE_THRESHOLD,
    claims: arr.length, settled_count: n, tokens_total: total, pending: pending, settled: settled,
    can_settle: total>=SETTLE_THRESHOLD && pending>0 };
}

async function settle(ref, meta) {
  if (!okRef(ref)) return { ok:false, error:'missing_or_invalid_ref' };
  if (!hasStore()) return { ok:false, error:'store_failed' };
  var arr = await load(ref);
  var sum = summarize(ref, arr);
  if (!sum.can_settle) return { ok:false, error:'below_threshold_or_nothing_pending', pending: sum.pending, threshold: sum.settle_threshold };
  var cnt=0, amt=0;
  for (var i=0;i<arr.length;i++){
    var e=arr[i]; if(!e||e.status==='settled'||e.status==='rejected')continue;
    e.status='settled'; e.settled_at=Date.now(); if(meta&&meta.method)e.method=String(meta.method).slice(0,32);
    cnt++; amt+=e.reward||0;
  }
  var ok = await save(ref, arr);
  if (!ok) return { ok:false, error:'store_failed' };
  return { ok:true, settled_count: cnt, settled_tokens: amt };
}

async function onRequest(req, res, data) {
  var send = function(c,o){ try{ res.writeHead(c,{'Content-Type':'application/json;charset=utf-8'}); res.end(JSON.stringify(o)); }catch(e){} };
  var p = String((data&&data.path)||'').split('?')[0];
  var action = String((data&&data.action)||'').slice(0,24) || p.replace(/^\/api\/bounty\/?/,'') || 'tasks';
  var ref = String((data&&data.ref)||'').slice(0,64);
  if (action === 'tasks') { return send(200, { ok:true, tasks: taskCatalog().map(function(t){return {id:t.id,label:t.label,reward:t.reward,proof_min:t.proof_min};}), store: hasStore()?storeName():'none' }); }
  if (action === 'rate') { return send(200, { ok:true, default_tokens: DEFAULT_BOUNTY_TOKENS, max_claims: MAX_CLAIMS_PER_REF, settle_threshold: SETTLE_THRESHOLD, store: hasStore()?storeName():'none' }); }
  if (!okRef(ref)) return send(200, { ok:false, error:'missing_or_invalid_ref' });
  try {
    if (action === 'summary') { var arr = await load(ref); return send(200, Object.assign({ok:true, store:hasStore()?storeName():'none'}, summarize(ref, arr))); }
    if (action === 'ledger' || action === 'list') { var arr2 = await load(ref); arr2.sort(function(a,b){return (b.at||0)-(a.at||0);}); return send(200, { ok:true, count: arr2.length, entries: arr2.slice(0,200) }); }
    if (action === 'claim') {
      var r = await claim(ref, String((data&&data.task_id)||'').slice(0,40), (data&&data.proof)||'', data);
      return send(r.ok ? 200 : 400, r);
    }
    if (action === 'settle') {
      var secret = String((data&&(data.secret||data.key))||(req.headers&&(req.headers['x-admin-secret']||req.headers['x-admin-key']))||'');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok:false, error:'forbidden' });
      var r2 = await settle(ref, { method: data&&data.method });
      return send(200, r2);
    }
    return send(404, { ok:false, error:'no_route', action: action });
  } catch (e) { return send(500, { ok:false, error:'exception', detail: String(e&&e.message) }); }
}
function storeName(){ return kv()?'kv':(up()?'supabase':(fileStore()?'file':'none')); }

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.claim = claim;
module.exports.summarize = summarize;
module.exports.settle = settle;
module.exports.verifyClaim = verifyClaim;
module.exports.taskCatalog = taskCatalog;
module.exports.hasStore = hasStore;
module.exports.load = load;
module.exports.default = onRequest;
