'use strict';
// bandwidth.js - 带宽/闲置资源共享账本 (赚钱回路新维度: 共享闲置带宽得币)
// 语义: 用户端上报闲置带宽贡献 (GB/s) -> 平台按费率记账 -> 累计得币 -> 达门槛可提现。
// 原则 (诚实, 防刷):
//   - 服务端权威: 费率/得币 由服务器算, 客户端上报只是 *原始量*, 不能自报得币额
//   - 计量: 按 贡献GB * 费率(币/GB) 记; 单日上限 (max_gb_per_day) 防刷
//   - 防伪造: 每 ref 每日累计上限; 异常量 (超物理上限) 拒记
//   - 合规: 真实带宽共享需 P2P 网络 + 结算; 本模块只做 *计量账本*, 不自动打款
// 存储: 复用同款 KV/Supabase + CN 文件回退 (key 前缀 bw:)
// Endpoints: /api/bandwidth?action=meter|summary|ledger|settle
const RATE_TOKENS_PER_GB = (function(){ var v=parseFloat(process.env.BANDWIDTH_TOKENS_PER_GB); return (isFinite(v)&&v>0)?v:0.5; })();
const MAX_GB_PER_DAY = (function(){ var v=parseFloat(process.env.BANDWIDTH_MAX_GB_DAY); return (isFinite(v)&&v>0)?v:50; })();
const MAX_GBS_PER_SAMPLE = (function(){ var v=parseFloat(process.env.BANDWIDTH_MAX_GBS_SAMPLE); return (isFinite(v)&&v>0)?v:10; })(); // 单采样物理上限 (10 Gbps 防伪造)
var SETTLE_THRESHOLD = 100;
var ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up(){try{var u=process.env.SUPABASE_URL,k=process.env.SUPABASE_SERVICE_KEY||process.env.SUPABASE_KEY;return(u&&k)?{u:String(u).replace(/\/$/,''),k:k}:null;}catch(e){return null;}}
function kv(){try{var u=process.env.KV_REST_API_URL||process.env.UPSTASH_REDIS_REST_URL,t=process.env.KV_REST_API_TOKEN||process.env.UPSTASH_REDIS_REST_TOKEN;return(u&&t)?{u:String(u).replace(/\/$/,''),t:t}:null;}catch(e){return null;}}
function fileStore(){try{var d=process.env.FILE_STORE_DIR;return(d&&String(d).trim())?String(d).trim():null;}catch(e){return null;}}
function bwFilePath(key){var dir=fileStore();if(!dir)return null;var safe=String(key).replace(/[^A-Za-z0-9_.:-]/g,'_');try{var p=require('path');return p.join(dir,'bandwidth',safe+'.json');}catch(e){return null;}}
async function bwFileGet(key){var p=bwFilePath(key);if(!p)return null;try{return await require('node:fs/promises').readFile(p,'utf8');}catch(e){return null;}}
async function bwFileSet(key,val){var p=bwFilePath(key);if(!p)return false;try{var fs=require('node:fs/promises');var P=require('path');await fs.mkdir(P.dirname(p),{recursive:true});await fs.writeFile(p,val,'utf8');return true;}catch(e){return false;}}
async function kget(k){try{var m=kv();var r=m?await fetch(m.u+'/get/'+encodeURIComponent(k),{headers:{Authorization:'Bearer '+m.t},signal:AbortSignal.timeout(8000)}):null;if(r){var j=await r.json();if(j&&j.result!==null&&j.result!==undefined)return j.result;}return null;}catch(e){return null;}}
async function kset(k,v){try{var m=kv();if(m){var body=(typeof v==='string')?v:JSON.stringify(v);var r=await fetch(m.u+'/set/'+encodeURIComponent(k),{method:'POST',headers:{Authorization:'Bearer '+m.t,'Content-Type':'application/json'},body:body,signal:AbortSignal.timeout(8000)});if(r.ok)return true;}return false;}catch(e){return false;}}
async function dget(k){try{var v=await kget(k);if(v!==null&&v!==undefined)return v;}catch(e){}var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/bandwidth_kv?k=eq.'+encodeURIComponent(k)+'&select=v',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});var j=await r.json();if(Array.isArray(j)&&j[0])return j[0].v;}catch(e){}}if(fileStore()){var f=await bwFileGet(k);if(f!==null&&f!==undefined)return f;}return null;}
async function dset(k,v){if(await kset(k,v))return true;var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/bandwidth_kv',{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify([{k:k,v:v}]),signal:AbortSignal.timeout(8000)});if(r.ok)return true;}catch(e){}}if(fileStore()&&await bwFileSet(k,v))return true;return false;}
function hasStore(){return !!(kv()||up()||fileStore());}

function keyOf(ref){return 'bw:'+ref;}
function okRef(ref){return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref||''));}
async function load(ref){var raw=await dget(keyOf(ref));if(!raw)return [];try{var a=JSON.parse(raw);return Array.isArray(a)?a:[];}catch(e){return [];}}
async function save(ref,arr){return dset(keyOf(ref),JSON.stringify(arr));}

// meter: 上报一段带宽贡献 (gb + 时长), 服务端按费率记币 (日上限 + 物理上限防刷)
async function meter(ref, gb, meta) {
  ref = String(ref||'').slice(0,64);
  if (!okRef(ref)) return { ok:false, error:'missing_or_invalid_ref' };
  if (!hasStore()) return { ok:false, error:'store_failed' };
  var g = parseFloat(gb);
  if (!isFinite(g) || g<=0) return { ok:false, error:'invalid_gb' };
  if (g > MAX_GB_PER_DAY) return { ok:false, error:'gb_exceeds_daily_cap', cap: MAX_GB_PER_DAY };
  // 单采样速率上限 (若 meta.gbs 提供) 防伪造
  if (meta && meta.gbs != null) { var s=parseFloat(meta.gbs); if(isFinite(s)&&s>MAX_GBS_PER_SAMPLE) return { ok:false, error:'gbs_exceeds_physical_cap', cap: MAX_GBS_PER_SAMPLE }; }
  var day = new Date().toISOString().slice(0,10);
  var arr = await load(ref);
  // 当日已贡献 (防日刷)
  var todayGB = 0;
  for (var i=0;i<arr.length;i++){ if(arr[i]&&String(arr[i].day)===day) todayGB += arr[i].gb||0; }
  var remaining = MAX_GB_PER_DAY - todayGB;
  var acceptedGB = Math.min(g, remaining);
  if (acceptedGB <= 0) return { ok:false, error:'daily_cap_reached', cap: MAX_GB_PER_DAY, already_gb: todayGB };
  var tokens = Math.round(acceptedGB * RATE_TOKENS_PER_GB * 100)/100;
  var entry = { id:'BW'+Date.now().toString(36)+Math.floor(Math.random()*1e6).toString(36),
    gb: acceptedGB, tokens: tokens, day: day, at: Date.now(),
    gbs: (meta&&meta.gbs!=null)?parseFloat(meta.gbs):null,
    source: String((meta&&meta.source)||'client').slice(0,24),
    status:'pending' };
  arr.push(entry);
  var ok = await save(ref, arr);
  if (!ok) return { ok:false, error:'store_failed' };
  return { ok:true, entry:entry, tokens_awarded: tokens, today_gb: todayGB+acceptedGB, cap: MAX_GB_PER_DAY };
}

function summarize(ref, arr) {
  var totalTokens=0, pending=0, settled=0, totalGB=0, n=0;
  for (var i=0;i<arr.length;i++){
    var e=arr[i]||{}; if(e.status==='rejected')continue;
    totalGB += e.gb||0;
    if(e.status==='settled'){ settled+=e.tokens||0; n++; } else pending+=e.tokens||0;
    totalTokens += e.tokens||0;
  }
  return { ref:ref, rate_tokens_per_gb: RATE_TOKENS_PER_GB, max_gb_per_day: MAX_GB_PER_DAY, settle_threshold: SETTLE_THRESHOLD,
    samples: arr.length, settled_count: n, total_gb: totalGB, tokens_total: totalTokens, pending: pending, settled: settled,
    can_settle: totalTokens>=SETTLE_THRESHOLD && pending>0 };
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
    cnt++; amt+=e.tokens||0;
  }
  var ok = await save(ref, arr);
  if (!ok) return { ok:false, error:'store_failed' };
  return { ok:true, settled_count:cnt, settled_tokens: amt };
}

async function onRequest(req, res, data) {
  var send = function(c,o){ try{ res.writeHead(c,{'Content-Type':'application/json;charset=utf-8'}); res.end(JSON.stringify(o)); }catch(e){} };
  var p = String((data&&data.path)||'').split('?')[0];
  var action = String((data&&data.action)||'').slice(0,24) || p.replace(/^\/api\/bandwidth\/?/,'') || 'rate';
  var ref = String((data&&data.ref)||'').slice(0,64);
  if (action === 'rate') { return send(200, { ok:true, rate_tokens_per_gb: RATE_TOKENS_PER_GB, max_gb_per_day: MAX_GB_PER_DAY, max_gbs_per_sample: MAX_GBS_PER_SAMPLE, settle_threshold: SETTLE_THRESHOLD, store: hasStore()?storeName():'none' }); }
  if (!okRef(ref)) return send(200, { ok:false, error:'missing_or_invalid_ref' });
  try {
    if (action === 'summary') { var arr = await load(ref); return send(200, Object.assign({ok:true, store:hasStore()?storeName():'none'}, summarize(ref, arr))); }
    if (action === 'ledger' || action === 'list') { var arr2 = await load(ref); arr2.sort(function(a,b){return (b.at||0)-(a.at||0);}); return send(200, { ok:true, count: arr2.length, entries: arr2.slice(0,200) }); }
    if (action === 'meter') {
      var gb = (data&&data.gb)!=null ? data.gb : (data&&data.gb==null ? (req.headers&&req.headers['x-bandwidth-gb']) : null);
      var r = await meter(ref, gb, { gbs: data&&data.gbs, source: data&&data.source });
      return send(r.ok ? 200 : 400, r);
    }
    if (action === 'settle') {
      var secret = String((data&&(data.secret||data.key))||(req.headers&&(req.headers['x-admin-secret']||req.headers['x-admin-key']))||'');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok:false, error:'forbidden' });
      var r2 = await settle(ref, { method: data&&data.method });
      return send(200, r2);
    }
    return send(404, { ok:false, error:'no_route', action:action });
  } catch (e) { return send(500, { ok:false, error:'exception', detail: String(e&&e.message) }); }
}
function storeName(){ return kv()?'kv':(up()?'supabase':(fileStore()?'file':'none')); }

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.meter = meter;
module.exports.summarize = summarize;
module.exports.settle = settle;
module.exports.hasStore = hasStore;
module.exports.load = load;
module.exports.default = onRequest;
