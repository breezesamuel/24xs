'use strict';
// subwall.js - 订阅墙 独立 serverless 模块
// 原则: 与 morning-youth.js 同 mode-switch 模式, 服务端权威(库存/过期/权益由服务端计算, 客户端不能伪造);
//       fail-closed: 缺存储/缺配置时返回 ok:false, 不假装成功; 纯 ASCII + \u 转义; 幂等设计.
// 端点: /api/subwall?action=check|list|subscribe|unsubscribe|extend|entitle
//       (也支持 REST 风格 /api/subwall/check 等)
// 存储: Supabase -> Vercel KV -> in-memory (与 alipay.js / morning-youth.js 一致)
const PLANS={
  free:    {label:'\u514d\u8d39',       cny:0,   usd:0,   days:0,   features:['dashboard','basic_report'], free_uses:10},
  trial:   {label:'\u9996\u5468\u4f53\u9a8c\uff087\u5929\uff09', cny:1,   usd:1,   days:7,   features:['dashboard','automation','reports','api','data_export','priority_mail'], trial:true, free_uses:10},
  pro:     {label:'\u4e13\u4e1a\u00b7\u6708\u5ea6',       cny:60,  usd:9.9, days:31,  features:['dashboard','automation','reports','api','data_export','priority_mail'], free_uses:10},
  pro3:    {label:'\u4e13\u4e1a\u00b7\u5b63\u5ea6',       cny:150, usd:25,  days:93,  features:['dashboard','automation','reports','api','data_export','priority_mail'], free_uses:10},
  proY:    {label:'\u4e13\u4e1a\u00b7\u5e74\u5ea6',       cny:500, usd:99,  days:366, features:['dashboard','automation','reports','api','data_export','priority_mail'], free_uses:10},
  team:    {label:'\u56e2\u961f\u00b7\u5e74\u5ea6',       cny:299, usd:41.5,days:366, features:['dashboard','automation','reports','api','data_export','dedicated_support','multi_seat'], free_uses:10}
};
const FREE={'':'free',free:'free'};
function up(){try{const u=process.env.SUPABASE_URL,k=process.env.SUPABASE_SERVICE_KEY||process.env.SUPABASE_KEY;return (u&&k)?{u:String(u).replace(/\/$/,''),k:k}:null;}catch(e){return null;}}
function kv(){try{const u=process.env.KV_REST_API_URL||process.env.UPSTASH_REDIS_REST_URL,t=process.env.KV_REST_API_TOKEN||process.env.UPSTASH_REDIS_REST_TOKEN;return (u&&t)?{u:String(u).replace(/\/$/,''),t:t}:null;}catch(e){return null;}}
async function kget(k){try{const m=kv();const r=m?await fetch(m.u+'/get/'+encodeURIComponent(k),{headers:{Authorization:'Bearer '+m.t},signal:AbortSignal.timeout(8000)}):null;if(r){const j=await r.json();if(j&&j.result!==null&&j.result!==undefined)return j.result;}return null;}catch(e){return null;}}
async function kset(k,v){try{const m=kv();if(m){const body=(typeof v==='string')?v:JSON.stringify(v);const r=await fetch(m.u+'/set/'+encodeURIComponent(k),{method:'POST',headers:{Authorization:'Bearer '+m.t,'Content-Type':'application/json'},body:body,signal:AbortSignal.timeout(8000)});if(r.ok)return true;}return false;}catch(e){return false;}}
async function dget(k){try{const v=await kget(k);if(v!==null&&v!==undefined)return v;}catch(e){}
  const s=up();if(!s)return null;
  try{const r=await fetch(s.u+'/rest/v1/subwall_kv?k=eq.'+encodeURIComponent(k)+'&select=v',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});
    const j=await r.json();if(Array.isArray(j)&&j[0])return j[0].v;}catch(e){}
  return null;}
async function dset(k,v){if(await kset(k,v))return true;
  const s=up();if(!s)return false;
  try{const r=await fetch(s.u+'/rest/v1/subwall_kv',{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify([{k:k,v:v}]),signal:AbortSignal.timeout(8000)});return r.ok;}catch(e){return false;}}
function keyOf(ref){return 'subwall:'+ref;}
async function load(ref){const raw=await dget(keyOf(ref));if(!raw)return [];try{const a=JSON.parse(raw);return Array.isArray(a)?a:[];}catch(e){return [];}}
async function save(ref,arr){return dset(keyOf(ref),JSON.stringify(arr));}
function daysLeft(s){if(!s||!s.expires)return null;return Math.max(0,Math.ceil((s.expires-Date.now())/86400000));}
function active(s){return s&&s.status==='active'&&(!s.expires||Date.now()<s.expires);}
// 服务端权威激活：由支付回调（alipay.js notify/order 校验支付成功后）调用，绝不信任客户端。
// 幂等由调用方的订单 status 保证；此处仅做存储与叠加：同类生效中订阅叠加时长，否则新增。
// trial 仅允许每用户一次（用 paid_out 去重）。
// 激活后由 alipay.js 统一处理推荐奖励（避免循环依赖）
async function activate(ref, plan, opts){
  ref=String(ref||'').slice(0,64);
  if(!/^[A-Za-z0-9_.-]{1,64}$/.test(ref))return {ok:false,error:'missing_or_invalid_ref'};
  const p=PLANS[plan];
  if(!p||(p.cny<=0 && p.usd<=0))return {ok:false,error:'unknown_plan'};
  const subs=await load(ref);
  const now=Date.now();
  const cur=subs.filter(active).sort(function(a,b){return (b.expires||9e15)-(a.expires||9e15);})[0];
  const addDays=p.days*86400000;
  // trial 去重：同一用户只能用一次
  if(p.trial && subs.some(s=>s.plan==='trial' && s.paid_out))return {ok:false,error:'trial_used'};
  if(cur&&cur.plan===plan){cur.expires=(cur.expires||now)+addDays;cur.renewed_at=now;}
  else{subs.push({plan:plan,status:'active',since:now,expires:now+addDays,paid_out:opts&&opts.out_trade_no?String(opts.out_trade_no).slice(0,64):undefined});}
  const ok=await save(ref,subs);
  if(!ok)return {ok:false,error:'store_failed'};
  const applied=cur&&cur.plan===plan?cur:subs[subs.length-1];
  return {ok:true,plan:plan,expires:applied.expires,days_remaining:daysLeft(applied),stacked:!!(cur&&cur.plan===plan)};
}
async function onRequest(req,res,data){
  const send=function(c,o){try{res.writeHead(c,{'Content-Type':'application/json;charset=utf-8'});res.end(JSON.stringify(o));}catch(e){}};
  const p=String((data&&data.path)||'').split('?')[0];
  const action=String((data&&data.action)||'').slice(0,24)||p.replace(/^\/api\/subwall\/?/,'')||'check';
  // plans action: 公开计划列表，不需要 ref
  if(action==='plans'){
    const out=Object.entries(PLANS).filter(([k,v])=>k!=='free').map(([k,v])=>({id:k,label:v.label,features:v.features,cny:v.cny,usd:v.usd,days:v.days,trial:v.trial||false}));
    return send(200,{ok:true,plans:out});
  }
  const ref=String((data&&data.ref)||'').slice(0,64);
  if(!/^[A-Za-z0-9_.-]{1,64}$/.test(ref))return send(200,{ok:false,error:'missing_or_invalid_ref'});
  try{
    if(action==='check'){
      const subs=await load(ref);
      const cur=subs.filter(active).sort(function(a,b){return (b.expires||9e15)-(a.expires||9e15);})[0]||null;
      const plan=cur?cur.plan:'free';
      return send(200,{ok:true,subscribed:!!cur,plan:plan,days_remaining:cur?daysLeft(cur):null,since:cur?cur.since:null});
    }
    if(action==='list'){
      const subs=await load(ref);
      const out=subs.map(function(s){return {plan:s.plan,status:s.status,since:s.since,expires:s.expires||null,days_remaining:daysLeft(s)};})
        .sort(function(a,b){return (b.expires||9e15)-(a.expires||9e15);});
      return send(200,{ok:true,count:out.filter(function(s){return s.status==='active';}).length,subscriptions:out});
    }
    if(action==='subscribe'){
      const plan=String((data&&data.plan)||'').slice(0,16);
      const p=PLANS[plan];
      if(!p||(p.cny<=0 && p.usd<=0))return send(200,{ok:false,error:'unknown_plan'});
      const subs=await load(ref);
      if(p.trial && subs.some(s=>s.plan==='trial' && s.paid_out))return send(200,{ok:false,error:'trial_used'});
      if(subs.some(active))return send(200,{ok:false,error:'already_active'});
      const now=Date.now();
      subs.push({plan:plan,status:'active',since:now,expires:now+p.days*86400000});
      const ok=await save(ref,subs);
      if(!ok)return send(500,{ok:false,error:'store_failed'});
      return send(200,{ok:true,plan:plan,days:p.days,expires:now+p.days*86400000});
    }
    if(action==='unsubscribe'){
      const plan=String((data&&data.plan)||'').slice(0,16);
      const subs=await load(ref);
      subs.forEach(function(s){if(s.plan===plan||!plan)s.status='canceled';});
      await save(ref,subs);
      return send(200,{ok:true});
    }
    if(action==='extend'){
      const months=Math.max(1,Math.min(24,parseInt(String((data&&data.months)||'1'),10)||1));
      const subs=await load(ref);
      const cur=subs.filter(active).sort(function(a,b){return (b.expires||9e15)-(a.expires||9e15);})[0];
      if(!cur)return send(200,{ok:false,error:'no_active'});
      cur.expires=(cur.expires||Date.now())+months*30*86400000;
      await save(ref,subs);
      return send(200,{ok:true,plan:cur.plan,expires:cur.expires,days_remaining:daysLeft(cur)});
    }
    if(action==='entitle'){
      const subs=await load(ref);
      const cur=subs.filter(active).sort(function(a,b){return (b.expires||9e15)-(a.expires||9e15);})[0]||null;
      const plan=cur?cur.plan:'free';
      const features=(PLANS[plan]||PLANS.free).features;
      return send(200,{ok:true,plan:plan,subscribed:!!cur,features:features});
    }
    return send(404,{ok:false,error:'no_route'});
  }catch(e){return send(500,{ok:false,error:String(e&&e.message||e)});}
}
module.exports={onRequest:onRequest,plans:PLANS,activate:activate,freeUnlock:function(ref){return (ref in FREE)||!ref;}};