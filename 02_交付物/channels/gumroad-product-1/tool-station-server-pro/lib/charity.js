'use strict';
// charity.js - 公益基金 (donation) 账本 (赚钱回路新维度: 公益捐赠 + 透明账本)
// 语义: 用户捐赠 (走支付宝收款 or 账本记一笔) -> 记入公益账本 (透明, 可按 ref 查总额)。
//   区别于其他渠道: 公益是 *支出* (平台把捐赠的钱拨给公益项目), 不是用户赚币。
// 原则 (诚实, 合规):
//   - 服务器权威: 捐赠额/记录 由服务器记, 客户端不能伪造
//   - 透明: 每笔捐赠可查 (ref + 金额 + 时间 + 项目), 总账公示
//   - fail-closed: 无存储 / 金额非法 -> ok:false, 绝不假成功
//   - 合规: 真实公益需 owner 备案 + 受赠方资质; 本模块只做 *账本记录*, 不自动打款
// 存储: 复用 cashback/bounty 同款 KV/Supabase + CN 文件回退 (key 前缀 dy:)
// Endpoints: /api/charity?action=donate|summary|ledger|total
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up(){try{var u=process.env.SUPABASE_URL,k=process.env.SUPABASE_SERVICE_KEY||process.env.SUPABASE_KEY;return(u&&k)?{u:String(u).replace(/\/$/,''),k:k}:null;}catch(e){return null;}}
function kv(){try{var u=process.env.KV_REST_API_URL||process.env.UPSTASH_REDIS_REST_URL,t=process.env.KV_REST_API_TOKEN||process.env.UPSTASH_REDIS_REST_TOKEN;return(u&&t)?{u:String(u).replace(/\/$/,''),t:t}:null;}catch(e){return null;}}
function fileStore(){try{var d=process.env.FILE_STORE_DIR;return(d&&String(d).trim())?String(d).trim():null;}catch(e){return null;}}
function dyFilePath(key){var dir=fileStore();if(!dir)return null;var safe=String(key).replace(/[^A-Za-z0-9_.:-]/g,'_');try{var p=require('path');return p.join(dir,'charity',safe+'.json');}catch(e){return null;}}
async function dyFileGet(key){var p=dyFilePath(key);if(!p)return null;try{return await require('node:fs/promises').readFile(p,'utf8');}catch(e){return null;}}
async function dyFileSet(key,val){var p=dyFilePath(key);if(!p)return false;try{var fs=require('node:fs/promises');var P=require('path');await fs.mkdir(P.dirname(p),{recursive:true});await fs.writeFile(p,val,'utf8');return true;}catch(e){return false;}}
async function kget(k){try{var m=kv();var r=m?await fetch(m.u+'/get/'+encodeURIComponent(k),{headers:{Authorization:'Bearer '+m.t},signal:AbortSignal.timeout(8000)}):null;if(r){var j=await r.json();if(j&&j.result!==null&&j.result!==undefined)return j.result;}return null;}catch(e){return null;}}
async function kset(k,v){try{var m=kv();if(m){var body=(typeof v==='string')?v:JSON.stringify(v);var r=await fetch(m.u+'/set/'+encodeURIComponent(k),{method:'POST',headers:{Authorization:'Bearer '+m.t,'Content-Type':'application/json'},body:body,signal:AbortSignal.timeout(8000)});if(r.ok)return true;}return false;}catch(e){return false;}}
// 公益账本: 全局总账 (charity:total) + 按 ref 的捐赠记录 (charity:<ref>)
async function dget(k){try{var v=await kget(k);if(v!==null&&v!==undefined)return v;}catch(e){}var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/charity_kv?k=eq.'+encodeURIComponent(k)+'&select=v',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});var j=await r.json();if(Array.isArray(j)&&j[0])return j[0].v;}catch(e){}}if(fileStore()){var f=await dyFileGet(k);if(f!==null&&f!==undefined)return f;}return null;}
async function dset(k,v){if(await kset(k,v))return true;var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/charity_kv',{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify([{k:k,v:v}]),signal:AbortSignal.timeout(8000)});if(r.ok)return true;}catch(e){}}if(fileStore()&&await dyFileSet(k,v))return true;return false;}
function hasStore(){return !!(kv()||up()||fileStore());}

function okRef(ref){return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref||''));}
function okAmt(x){var n=parseFloat(x);return isFinite(n)&&n>=1&&n<=100000;}   // 1 元 ~ 10 万元 (单笔合理区间)

// donate: 记一笔捐赠 (ref + 金额 + 项目)。幂等 by donor_ref+amount+project+day (防重复记)
async function donate(ref, amount, project, meta) {
  ref = String(ref||'anonymous').slice(0,64);
  if (!okRef(ref)) return { ok:false, error:'missing_or_invalid_ref' };
  if (!hasStore()) return { ok:false, error:'store_failed' };
  if (!okAmt(amount)) return { ok:false, error:'invalid_amount', range:'1~100000' };
  var amtC = Math.round(parseFloat(amount)*100);
  var proj = String(project||'general').slice(0,40);
  // 个人捐赠记录
  var rk = 'dy:' + ref;
  var rarr = [];
  var raw = await dget(rk);
  try { rarr = JSON.parse(raw); if(!Array.isArray(rarr)) rarr=[]; } catch(e){ rarr=[]; }
  var day = new Date().toISOString().slice(0,10);
  // 幂等: 同 ref 同天同额同项目 视为重复
  var dup = rarr.some(function(e){ return e && e.amount===amtC && e.project===proj && e.day===day; });
  if (dup) return { ok:true, duplicate:true };
  var entry = { id:'DY'+Date.now().toString(36)+Math.floor(Math.random()*1e6).toString(36),
    amount:(amtC/100), project:proj, day:day, at:Date.now(),
    out_trade_no: String((meta&&meta.out_trade_no)||'').slice(0,64),
    source: String((meta&&meta.source)||'ledger').slice(0,24) };
  rarr.push(entry);
  var okR = await dset(rk, JSON.stringify(rarr));
  // 全局总账
  var gk = 'dy:total';
  var g = { count:0, total_c:0, by_project:{} };
  var graw = await dget(gk);
  try { var gg = JSON.parse(graw); if (gg && gg.total_c!=null) g = gg; } catch(e){}
  g.count += 1; g.total_c += amtC; g.by_project[proj] = (g.by_project[proj]||0) + amtC;
  var okG = await dset(gk, JSON.stringify(g));
  if (!okR || !okG) return { ok:false, error:'store_failed' };
  return { ok:true, entry:entry, global_total_yuan:(g.total_c/100) };
}

async function total() {
  var g = { count:0, total_c:0, by_project:{} };
  var raw = await dget('dy:total');
  try { var o = JSON.parse(raw); if (o && o.total_c!=null) g = o; } catch(e){}
  return { ok:true, store: hasStore()?storeName():'none',
    count:g.count, total_yuan:(g.total_c||0)/100, by_project: Object.keys(g.by_project||{}).map(function(p){ return {project:p, yuan:(g.by_project[p]/100)}; }) };
}
function summary(ref){ return dget('dy:'+ref).then(function(raw){ var a=[]; try{a=JSON.parse(raw);}catch(e){} if(!Array.isArray(a))a=[]; var t=0; for(var i=0;i<a.length;i++)t+=a[i].amount||0; return { ok:true, store:hasStore()?storeName():'none', ref:ref, count:a.length, total_yuan:t, recent:a.slice(-20).reverse() }; }); }
function ledger(ref, n){ return dget('dy:'+ref).then(function(raw){ var a=[]; try{a=JSON.parse(raw);}catch(e){} if(!Array.isArray(a))a=[]; a.sort(function(x,y){return (y.at||0)-(x.at||0);}); return { ok:true, count:a.length, entries:a.slice(0,Math.min(parseInt(n,10)||50,200)) }; }); }

async function onRequest(req, res, data) {
  var send = function(c,o){ try{ res.writeHead(c,{'Content-Type':'application/json;charset=utf-8'}); res.end(JSON.stringify(o)); }catch(e){} };
  var p = String((data&&data.path)||'').split('?')[0];
  var action = String((data&&data.action)||'').slice(0,24) || p.replace(/^\/api\/charity\/?/,'') || 'total';
  var ref = String((data&&data.ref)||'').slice(0,64);
  if (action === 'total') { var t = await total(); return send(200, t); }
  if (action === 'donate') {
    var amt = (data&&data.amount);
    var r = await donate(ref, amt, (data&&data.project), { out_trade_no:data&&data.out_trade_no, source:data&&data.source });
    return send(r.ok ? 200 : 400, Object.assign({ ok:r.ok }, r));
  }
  if (action === 'summary' || action === 'me') { if(!okRef(ref)) return send(200,{ok:false,error:'missing_or_invalid_ref'}); return send(200, await summary(ref)); }
  if (action === 'ledger' || action === 'list') { if(!okRef(ref)) return send(200,{ok:false,error:'missing_or_invalid_ref'}); return send(200, await ledger(ref, data&&data.n)); }
  return send(404, { ok:false, error:'no_route', action:action });
}
function storeName(){ return kv()?'kv':(up()?'supabase':(fileStore()?'file':'none')); }

// 支付成功时的挂钩 (由 alipay.js 在 /api/pay 成功后调用, 记公益账本)
async function onPaid(rec) {
  if (!rec || !rec.ref) return { ok:false, error:'no_ref' };
  return donate(rec.ref, rec.amount, String(rec.charity_project||'general'), { out_trade_no:rec.out_trade_no, source:'alipay_paid' });
}

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.donate = donate;
module.exports.onPaid = onPaid;
module.exports.total = total;
module.exports.summary = summary;
module.exports.ledger = ledger;
module.exports.hasStore = hasStore;
module.exports.default = onRequest;
