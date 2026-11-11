'use strict';
// recovery.js - 找回被遗忘资产 (recovered/abandoned assets) 账本 (赚钱回路新维度)
//
// ⚠️ 诚实边界 (重要):
//   本模块 *只做账本记录*, 不扫描/侵占他人链上资金。
//   - 合法语义: 帮 "自己/注册用户" 找回 *本人* 遗忘在旧地址/旧交易所/旧项目的币,
//     或经 *用户授权* (owner 确认归属) 后, 平台协助找回并记服务佣金。
//   - 绝不做: 全网扫 "无主/被丢弃" 资金据为己有 (那是侵占他人财产, 违法 + 自毁)。
//   所有 "找回" 记录必须带: owner_ref (资产归属人, 须已注册) + 来源 (旧地址/旧交易所) + 授权标记。
//   无 owner_ref / 无授权 -> fail-closed 拒记 (防伪造 + 防侵占)。
//
// 原则:
//   - 服务器权威: 找回额/佣金 由服务器算, 客户端不能自报
//   - 佣金: 找回成功后按 RECOVERY_FEE_PCT (默认 10%) 记平台服务费 (合法, 已授权)
//   - 防刷: 同一 (owner_ref + source + amount) 幂等; 单 ref 上限
// Endpoints: /api/recovery?action=record|summary|ledger|rate
const RECOVERY_FEE_PCT = (function(){ var v=parseFloat(process.env.RECOVERY_FEE_PCT); return (isFinite(v)&&v>=0&&v<=50)?v:10; })();
const MAX_RECORDS_PER_REF = 50;
var ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up(){try{var u=process.env.SUPABASE_URL,k=process.env.SUPABASE_SERVICE_KEY||process.env.SUPABASE_KEY;return(u&&k)?{u:String(u).replace(/\/$/,''),k:k}:null;}catch(e){return null;}}
function kv(){try{var u=process.env.KV_REST_API_URL||process.env.UPSTASH_REDIS_REST_URL,t=process.env.KV_REST_API_TOKEN||process.env.UPSTASH_REDIS_REST_TOKEN;return(u&&t)?{u:String(u).replace(/\/$/,''),t:t}:null;}catch(e){return null;}}
function fileStore(){try{var d=process.env.FILE_STORE_DIR;return(d&&String(d).trim())?String(d).trim():null;}catch(e){return null;}}
function rcFilePath(key){var dir=fileStore();if(!dir)return null;var safe=String(key).replace(/[^A-Za-z0-9_.:-]/g,'_');try{var p=require('path');return p.join(dir,'recovery',safe+'.json');}catch(e){return null;}}
async function rcFileGet(key){var p=rcFilePath(key);if(!p)return null;try{return await require('node:fs/promises').readFile(p,'utf8');}catch(e){return null;}}
async function rcFileSet(key,val){var p=rcFilePath(key);if(!p)return false;try{var fs=require('node:fs/promises');var P=require('path');await fs.mkdir(P.dirname(p),{recursive:true});await fs.writeFile(p,val,'utf8');return true;}catch(e){return false;}}
async function kget(k){try{var m=kv();var r=m?await fetch(m.u+'/get/'+encodeURIComponent(k),{headers:{Authorization:'Bearer '+m.t},signal:AbortSignal.timeout(8000)}):null;if(r){var j=await r.json();if(j&&j.result!==null&&j.result!==undefined)return j.result;}return null;}catch(e){return null;}}
async function kset(k,v){try{var m=kv();if(m){var body=(typeof v==='string')?v:JSON.stringify(v);var r=await fetch(m.u+'/set/'+encodeURIComponent(k),{method:'POST',headers:{Authorization:'Bearer '+m.t,'Content-Type':'application/json'},body:body,signal:AbortSignal.timeout(8000)});if(r.ok)return true;}return false;}catch(e){return false;}}
async function dget(k){try{var v=await kget(k);if(v!==null&&v!==undefined)return v;}catch(e){}var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/recovery_kv?k=eq.'+encodeURIComponent(k)+'&select=v',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});var j=await r.json();if(Array.isArray(j)&&j[0])return j[0].v;}catch(e){}}if(fileStore()){var f=await rcFileGet(k);if(f!==null&&f!==undefined)return f;}return null;}
async function dset(k,v){if(await kset(k,v))return true;var s=up();if(s){try{var r=await fetch(s.u+'/rest/v1/recovery_kv',{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify([{k:k,v:v}]),signal:AbortSignal.timeout(8000)});if(r.ok)return true;}catch(e){}}if(fileStore()&&await rcFileSet(k,v))return true;return false;}
function hasStore(){return !!(kv()||up()||fileStore());}

function okRef(ref){return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref||''));}
async function load(ref){var raw=await dget('rc:'+ref);if(!raw)return [];try{var a=JSON.parse(raw);return Array.isArray(a)?a:[];}catch(e){return [];}}
async function save(ref,arr){return dset('rc:'+ref, JSON.stringify(arr));}

// record: 登记一笔 "找回本人资产" (须 owner_ref 已注册 + 授权标记 + 来源)。幂等 by (owner+source+amount+asset)。
async function record(ownerRef, found) {
  var ref = String(ownerRef||'').slice(0,64);
  if (!okRef(ref)) return { ok:false, error:'missing_owner_ref', note:'须资产归属人已注册 (防侵占他人资金)' };
  if (!hasStore()) return { ok:false, error:'store_failed' };
  var amt = parseFloat(found && found.amount);
  if (!isFinite(amt) || amt <= 0) return { ok:false, error:'invalid_amount' };
  var asset = String((found&&found.asset)||'USDC').slice(0,16);
  var source = String((found&&found.source)||'').slice(0,64);
  if (!source) return { ok:false, error:'missing_source', note:'须说明来源 (旧地址/旧交易所/旧项目)' };
  var authorized = !!(found&&found.authorized);   // 必须显式授权
  if (!authorized) return { ok:false, error:'not_authorized', note:'找回他人资产须用户/owner 显式授权, 否则拒记 (合规红线)' };
  var arr = await load(ref);
  var hash = ref+'|'+source+'|'+asset+'|'+amt;
  for (var i=0;i<arr.length;i++){ if(arr[i]&&arr[i].dedupe===hash) return { ok:true, duplicate:true, entry:arr[i] }; }
  if (arr.length >= MAX_RECORDS_PER_REF) return { ok:false, error:'record_cap_reached' };
  var feeC = Math.round(amt*1e6 * RECOVERY_FEE_PCT / 100);   // 佣金 (按 10^6 精度, 防浮点)
  var entry = { id:'RC'+Date.now().toString(36)+Math.floor(Math.random()*1e6).toString(36),
    dedupe:hash, asset:asset, amount:amt, source:source,
    fee_pct:RECOVERY_FEE_PCT, platform_fee: feeC/1e6,
    status:'recovered', at:Date.now() };
  arr.push(entry);
  var ok = await save(ref, arr);
  if (!ok) return { ok:false, error:'store_failed' };
  return { ok:true, entry:entry };
}

function summarize(ref, arr){
  var n=0, total=0, fee=0;
  for (var i=0;i<arr.length;i++){ var e=arr[i]||{}; if(e.status!=='recovered')continue; n++; total+=e.amount||0; fee+=e.platform_fee||0; }
  return { ref:ref, fee_pct:RECOVERY_FEE_PCT, recovered_count:n, total_recovered:total, platform_fee:fee,
    note:'仅本人/已授权资产; 不含任何扫描他人无主资金' };
}

async function onRequest(req, res, data) {
  var send = function(c,o){ try{ res.writeHead(c,{'Content-Type':'application/json;charset=utf-8'}); res.end(JSON.stringify(o)); }catch(e){} };
  var p = String((data&&data.path)||'').split('?')[0];
  var action = String((data&&data.action)||'').slice(0,24) || p.replace(/^\/api\/recovery\/?/,'') || 'rate';
  var ref = String((data&&data.ref)||'').slice(0,64);
  if (action === 'rate') { return send(200, { ok:true, fee_pct:RECOVERY_FEE_PCT, max_records:MAX_RECORDS_PER_REF, store:hasStore()?storeName():'none', note:'合法找回账本, 拒扫描他人无主资金' }); }
  if (!okRef(ref)) return send(200, { ok:false, error:'missing_or_invalid_ref' });
  try {
    if (action === 'summary') { var arr = await load(ref); return send(200, Object.assign({ok:true, store:hasStore()?storeName():'none'}, summarize(ref, arr))); }
    if (action === 'ledger' || action === 'list') { var arr2 = await load(ref); arr2.sort(function(a,b){return (b.at||0)-(a.at||0);}); return send(200, { ok:true, count:arr2.length, entries:arr2.slice(0,200) }); }
    if (action === 'record') {
      // 接受两种 body: 扁平 {ref, amount, asset, source, authorized} 或 嵌套 {ref, found:{...}}
      var f = (data&&data.found) && typeof data.found === 'object' ? data.found : (data&&data.found && typeof data.found === 'string' ? (function(){ try{return JSON.parse(data.found);}catch(e){return {};}})() : {});
      var found = {
        amount: f.amount != null ? f.amount : data.amount,
        asset: f.asset != null ? f.asset : data.asset,
        source: f.source != null ? f.source : data.source,
        authorized: f.authorized != null ? f.authorized : data.authorized
      };
      // authorized 可能是 URL 序列化的字符串
      found.authorized = (found.authorized === 'true' || found.authorized === true || found.authorized === 1 || found.authorized === '1');
      var r = await record(ref, found);
      return send(r.ok ? 200 : 400, r);
    }
    return send(404, { ok:false, error:'no_route', action:action });
  } catch (e) { return send(500, { ok:false, error:'exception', detail:String(e&&e.message) }); }
}
function storeName(){ return kv()?'kv':(up()?'supabase':(fileStore()?'file':'none')); }

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.record = record;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.load = load;
module.exports.default = onRequest;
