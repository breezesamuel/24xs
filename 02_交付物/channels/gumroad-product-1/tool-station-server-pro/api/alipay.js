const crypto=require('crypto');
const billing=require('../lib/arcade_billing.js');
const stripeMod=require('../lib/stripe.js');
function ts(){const d=new Date(Date.now()+8*3600*1000);const p=n=>String(n).padStart(2,'0');return d.getUTCFullYear()+'-'+p(d.getUTCMonth()+1)+'-'+p(d.getUTCDate())+' '+p(d.getUTCHours())+':'+p(d.getUTCMinutes())+':'+p(d.getUTCSeconds());}
function get(k){return process.env[k]||'';}
// 密钥支持"文件"形式：ALIPAY_MERCHANT_PRIVATE_KEY_FILE / ALIPAY_ALIPAY_PUBLIC_KEY_FILE
// 为什么需要: systemd 的 EnvironmentFile **不会**把 \n 解成真换行
// （实测值里换行变成字面量 n）→ 多行 PEM 直接放进 env 会被毁掉。
// 自托管实例把 PEM 放文件里更安全（不进 env、不进进程命令行）。
const FILEKEY_CACHE={};
function getKey(name){
  if(FILEKEY_CACHE[name]!==undefined)return FILEKEY_CACHE[name];
  let v='';
  try{
    const f=process.env[name+'_FILE'];
    if(f&&require('node:fs').existsSync(f))v=require('node:fs').readFileSync(f,'utf8');
  }catch(e){}
  if(!v)v=get(name);
  FILEKEY_CACHE[name]=v;
  return v;
}

const PLANS={
  trial:  {cny:1,   usd:1,   days:7,   label:'首周体验(7天)'},
  pro:    {cny:60,  usd:9.9, days:31,  label:'专业·月度'},
  pro3:   {cny:150, usd:25,  days:93,  label:'专业·季度'},
  proY:   {cny:500, usd:99,  days:366, label:'专业·年度'},
  team:   {cny:299, usd:41.5,days:366, label:'团队·年度'},
  // 兼容旧 arcade 充值包
  m10:10,m30:30,m100:100,y99:99,y299:299,y999:999,t30:6,t60:12,t300:60,t1000:200
};
const MINPACK={t30:30,t60:60,t300:300,t1000:1000};
// 推荐返现阶梯: 封顶 30%。
// 原 [[1,10],[2,30],[3,50],[5,70],[10,100]] → 邀请 10 人=100% 免单，平台实收 ¥0、推荐人佣金也 ¥0（双输）。
// 无外部流量时自推荐=纯亏损，故把封顶压到 30%（净收入 = 标价×70%×70% ≈ 49%）。
const LADDER=[[1,10],[2,20],[3,30]];
// 每个游戏免费时长（秒）。默认 600 秒 = 10 分钟。与游戏端 FREE_SEC=600 契约一致。
// 2026-10-11 修复：此前该常量缺失，导致 /api/arcade 首次请求抛 ReferenceError 500，
// 免费时长永不入账、付费扣费全线失效（心跳计费形同虚设）。
const FREE_SEC=parseInt(process.env.ARCADE_FREE_SEC||'600',10);
const WALLETS={
  base_primary:{chain:'Base',asset:'USDC',address:'0xa75Cc8545B169F0BeF2f29c9CCF86bc686D039E8',role:'主收款(平台)'},
  evm_payout:{chain:'EVM',asset:'USDC/ETH/USDT',address:'0x52513A733D4b52282F2b4f5A91D965D38b64f3BB',role:'Direct EVM Payout'},
  payout_usdc:{chain:'Base',asset:'USDC',address:'0x2C5dF5f91642B1214c28E51C67aEf1c61CbE1824',role:'Payout(USDC on Base)'},
  payment_usdc:{chain:'Base',asset:'USDC',address:'0x047b2A7fc72862a0e3E772eb53b19d35929BEd46',role:'Payment(USDC on Base)'},
  evm_alipay:{chain:'EVM',asset:'USDC/ETH',address:'0xDe37cDc93fC425e14EBdB827086E2144b31E855a',role:'EVM 收款'},
  cn_wallet:{chain:'EVM',asset:'多币',address:'0x5D36F4c480F900F0E7Ad0DC4fA0402554b972bF8',role:'国内收款到钱包'},
  solana_bounty:{chain:'Solana',asset:'SOL/usdc',address:'4moYJshT1bW71iESvwJHMynA5NFV534PJzFiKraydV6Z',role:'bounty 收款'}
};
function ladderPct(n){let pct=0;for(let i=0;i<LADDER.length;i++){if(n>=LADDER[i][0])pct=LADDER[i][1];}return Math.max(0,Math.min(100,pct));}

function baseFrom(req){
  const env=get('SITE_BASE');if(env)return env.replace(/\/$/,'');
  const h=(req&&req.headers)||{};
  const host=h['x-forwarded-host']||h.host||'bingdashan-pain-tools.vercel.app';
  const proto=h['x-forwarded-proto']||'https';
  return proto+'://'+String(host).split(',')[0].trim();
}
function sigKey(raw){
  raw=String(raw||'').trim();
  if(!raw)throw new Error('私钥为空');
  // ① PEM 文本：直接用。⚠️ 旧实现把 PEM 去掉头尾后**又 base64 编码一次**，
  //    生成的是双重编码的垃圾 → "DECODER routines::unsupported"。
  //    另外 \n 可能被 systemd/env 压成字面量 "\n"，一并还原。
  if(raw.indexOf('-----BEGIN')>=0){
    const pem=raw.replace(/\\n/g,'\n').replace(/\r\n/g,'\n');
    try{return crypto.createPrivateKey(pem);}catch(e){}
  }
  // ② base64(DER) —— 线上 Vercel 用的就是这种形式（必须保持可用）
  const b=Buffer.from(raw.replace(/\s/g,''),'base64');
  if(Buffer.isBuffer(b)){try{return crypto.createPrivateKey({key:b,format:'der',type:'pkcs8'});}catch(e){}}
  // ③ base64(PEM 文本)
  try{return crypto.createPrivateKey(b.toString('utf8'));}catch(e){}
  throw new Error('私钥格式无法识别（需要 PEM 或 base64(DER)）');
}
function verKey(raw){
  raw=String(raw||'').trim();
  // ① PEM 文本（与 sigKey 同理：旧实现对 PEM 也是双重编码 → 坏）
  if(raw.indexOf('-----BEGIN')>=0){
    const pem=raw.replace(/\\n/g,'\n').replace(/\r\n/g,'\n');
    try{return crypto.createPublicKey(pem);}catch(e){}
  }
  // ② base64(DER)
  const b=Buffer.from(raw.replace(/\s/g,''),'base64');
  if(Buffer.isBuffer(b)){try{return crypto.createPublicKey({key:b,format:'der',type:'spki'});}catch(e){}}
  // ③ base64(PEM 文本)
  try{return crypto.createPublicKey(b.toString('utf8'));}catch(e){}
  throw new Error('公钥格式无法识别（需要 PEM 或 base64(DER)）');
}
function signParams(params,priv){
  const signStr=Object.keys(params).sort().filter(k=>params[k]!==''&&params[k]!==undefined&&params[k]!==null).map(k=>k+'='+params[k]).join('&');
  return crypto.createSign('RSA-SHA256').update(signStr,'utf8').sign(sigKey(priv),'base64');
}
function aesConf(){
  const k=get('ALIPAY_AES_KEY');
  if(!k)return null;
  let b;
  try{b=Buffer.from(k,'base64');}catch(e){b=null;}
  if(!b||(b.length!==16&&b.length!==24&&b.length!==32))return null;
  return {key:b,iv:Buffer.alloc(b.length>=16?16:b.length)};
}
function aesEncrypt(plain){
  const c=aesConf();if(!c)return plain;
  const cph=crypto.createCipheriv('aes-'+(c.key.length*8)+'-cbc',c.key,c.iv);
  return cph.update(String(plain),'utf8','base64')+cph.final('base64');
}
function aesDecrypt(ct){
  const c=aesConf();if(!c)return null;
  try{
    const dcp=crypto.createDecipheriv('aes-'+(c.key.length*8)+'-cbc',c.key,c.iv);
    return dcp.update(String(ct),'base64','utf8')+dcp.final('utf8');
  }catch(e){return null;}
}
function alipayParams(biz,method,base,extra){
  const APP=get('ALIPAY_APP_ID'),PRIV=getKey('ALIPAY_MERCHANT_PRIVATE_KEY');
  if(!APP||!PRIV)return{error:'服务端缺少 ALIPAY_APP_ID 或 ALIPAY_MERCHANT_PRIVATE_KEY(请在 Vercel 环境变量配置)'};
  const plainBiz=JSON.stringify(biz);
  const encrypted=aesEncrypt(plainBiz);
  const params=Object.assign({app_id:APP,method:method,charset:'utf-8',sign_type:'RSA2',timestamp:ts(),version:'1.0',notify_url:base+'/api/notify',return_url:base+'/paid.html',format:'JSON',biz_content:encrypted},extra||{});
  if(encrypted!==plainBiz)params.encrypt_type='AES';
  params.sign=signParams(params,PRIV);return{params:params};
}
function verifyNotify(form){
  const PUB=getKey('ALIPAY_ALIPAY_PUBLIC_KEY');if(!PUB)return{ok:false,error:'缺少支付宝公钥'};
  const clean={};Object.keys(form).forEach(k=>{if(form[k]!==undefined&&form[k]!==null&&form[k]!==''&&k!=='sign'&&k!=='sign_type')clean[k]=form[k];});
  const signStr=Object.keys(clean).sort().map(k=>k+'='+clean[k]).join('&');
  let ok=false;try{ok=crypto.createVerify('RSA-SHA256').update(signStr,'utf8').verify(verKey(PUB),String(form.sign||''),'base64');}catch(e){ok=false;}
  let eff=Object.assign({},form);
  if(ok&&form.encrypt_type==='AES'&&String(form.biz_content||'').length>0){
    const dec=aesDecrypt(form.biz_content);
    if(dec){try{const j=JSON.parse(dec);Object.assign(eff,Object.fromEntries(Object.entries(j).filter(([k,v])=>eff[k]===undefined&&v!==undefined)));}catch(e){}}
  }
  const paid=ok&&eff.app_id===get('ALIPAY_APP_ID')&&(eff.trade_status==='TRADE_SUCCESS'||eff.trade_status==='TRADE_FINISHED')&&!!eff.out_trade_no;
  return {ok:ok&&paid,verified:ok,paid:paid,out_trade_no:eff.out_trade_no,trade_status:eff.trade_status,trade_no:eff.trade_no,buyer:eff.buyer_logon_id||eff.buyer_id,total:eff.total_amount||eff.amount,subject:eff.subject,decrypted:eff.biz_content!==form.biz_content};
}

function privFingerprint(){
  const PRIV=getKey('ALIPAY_MERCHANT_PRIVATE_KEY');
  if(!PRIV)return null;
  try{
    const jwk=crypto.createPublicKey(sigKey(PRIV)).export({format:'jwk'});
    const jn=String(jwk.n||'');
    const b=Buffer.from(jn.replace(/-/g,'+').replace(/_/g,'/'),'base64');
    return b.toString('hex').slice(0,32);
  }catch(e){return 'ERR:'+e.message;}
}

// ========== WeChat Pay V3 ==========
function wxpaySign(method, url, timestamp, nonce, body, privateKey) {
  const msg = `${method}\n${url}\n${timestamp}\n${nonce}\n${body}\n`;
  return crypto.createSign('RSA-SHA256').update(msg).sign(privateKey, 'base64');
}
function wxpayVerify(headers, body, publicKey) {
  const timestamp = headers['wechatpay-timestamp'];
  const nonce = headers['wechatpay-nonce'];
  const signature = headers['wechatpay-signature'];
  const serial = headers['wechatpay-serial'];
  const msg = `${timestamp}\n${nonce}\n${body}\n`;
  const ver = crypto.createVerify('RSA-SHA256').update(msg);
  return ver.verify(publicKey, Buffer.from(signature, 'base64'));
}
async function wxpayCreateOrder(base, plan, ref, slug, inv, outTradeNo) {
  let sp = PLANS[plan];
  // 工具页数字套餐（m10/m30/…）与订阅对象套餐（trial/pro…）统一支持
  if (typeof sp === 'number') sp = { cny: sp };
  if (!sp) return {error:'unknown_plan'};
  const mchid = get('WECHAT_MCHID');
  const appid = get('WECHAT_APPID');
  const certSerial = get('WECHAT_CERT_SERIAL');
  const apiv3Key = get('WECHAT_APIV3_KEY');
  const notifyUrl = base + '/api/wxpay/notify';
  if (!mchid || !appid || !certSerial || !apiv3Key) {
    return {error:'wechat_pay_not_configured', missing: {
      mchid: !!mchid, appid: !!appid,
      certSerial: !!certSerial, apiv3Key: !!apiv3Key } };
  }
  // WECHAT_PRIVATE_KEY 存的是 base64(PEM)（Vercel Secret 限制，不可直接存 PEM）
  // 解 base64 → 得到 PEM 文本，再传给 crypto
  const b64raw = get('WECHAT_PRIVATE_KEY') || '';
  let privateKey;
  try {
    const pemText = Buffer.from(b64raw, 'base64').toString('utf8');
    privateKey = crypto.createPrivateKey({ key: pemText, format: 'pem' });
  } catch (e) {
    return {error:'wechat_private_key_decode_failed', detail: e.message};
  }
  const url = 'https://api.mch.weixin.qq.com/v3/pay/transactions/native';
  const timestamp = Math.floor(Date.now()/1000);
  const nonce = crypto.randomBytes(16).toString('hex');
  const body = JSON.stringify({
    appid, mchid, description: `bingdashan ${plan}`, out_trade_no: outTradeNo,
    notify_url: notifyUrl,
    amount: {total: Math.round(sp.cny * 100), currency: 'CNY'},
  });
  const signature = wxpaySign('POST', '/v3/pay/transactions/native', timestamp, nonce, body, privateKey);
  const auth = `WECHATPAY2-SHA256-RSA2048 mchid="${mchid}",nonce_str="${nonce}",timestamp="${timestamp}",serial_no="${certSerial}",signature="${signature}"`;
  try {
    const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json','Authorization':auth,'Accept':'application/json','User-Agent':'bingdashan/1.0'}, body, signal:AbortSignal.timeout(15000)});
    const j = await r.json();
    if (r.ok && j.code_url) {
      return {ok:true, code_url: j.code_url, out_trade_no: outTradeNo};
    }
    return {error:j.message||'wxpay_failed', detail:j};
  } catch(e) { return {error:e.message}; }
}
// 微信侧查单（Native 支付状态轮询）：GET /v3/pay/transactions/out-trade-no/{no}?mchid=
async function wxpayQueryOrder(outTradeNo) {
  const mchid = get('WECHAT_MCHID');
  const certSerial = get('WECHAT_CERT_SERIAL');
  const b64raw = get('WECHAT_PRIVATE_KEY') || '';
  let privateKey;
  try { privateKey = crypto.createPrivateKey({ key: Buffer.from(b64raw, 'base64').toString('utf8'), format: 'pem' }); }
  catch (e) { return {error:'wechat_private_key_decode_failed', detail:e.message}; }
  const path = '/v3/pay/transactions/out-trade-no/' + encodeURIComponent(outTradeNo) + '?mchid=' + encodeURIComponent(mchid);
  const timestamp = Math.floor(Date.now()/1000);
  const nonce = crypto.randomBytes(16).toString('hex');
  const msg = `GET\n${path}\n${timestamp}\n${nonce}\n\n`;
  const signature = crypto.createSign('RSA-SHA256').update(msg).sign(privateKey, 'base64');
  const auth = `WECHATPAY2-SHA256-RSA2048 mchid="${mchid}",nonce_str="${nonce}",timestamp="${timestamp}",serial_no="${certSerial}",signature="${signature}"`;
  try {
    const r = await fetch('https://api.mch.weixin.qq.com' + path, {headers:{Authorization:auth,'Accept':'application/json','User-Agent':'bingdashan/1.0'}, signal:AbortSignal.timeout(15000)});
    const j = await r.json();
    return { ok: r.ok, trade_state: j.trade_state, paid: j.trade_state === 'SUCCESS', amount: (j.amount && j.amount.total) ? (j.amount.total/100).toFixed(2) : null, detail: j };
  } catch(e) { return {error:e.message}; }
}
async function wxpayHandleNotify(rawBody, headers) {
  const publicKeyPem = get('WECHAT_PUBLIC_KEY');
  if (!publicKeyPem) return {ok:false, error:'wxpay_public_key_missing'};
  const publicKey = crypto.createPublicKey({key: publicKeyPem, format: 'pem'});
  if (!wxpayVerify(headers, rawBody, publicKey)) return {ok:false, error:'signature_invalid'};
  let j;
  try { j = JSON.parse(rawBody); } catch(e) { return {ok:false, error:'invalid_json'}; }
  const resource = j.resource;
  if (!resource) return {ok:false, error:'no_resource'};
  // 解密 AES-GCM
  const key = Buffer.from(get('WECHAT_APIV3_KEY'), 'utf8');
  const nonce = Buffer.from(resource.nonce, 'utf8');
  const ciphertext = Buffer.from(resource.ciphertext, 'base64');
  const associatedData = Buffer.from(resource.associated_data || '', 'utf8');
  let plaintext;
  try {
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, nonce);
    decipher.setAuthTag(Buffer.from(resource.auth_tag, 'base64'));
    decipher.setAAD(associatedData);
    plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf8');
  } catch(e) { return {ok:false, error:'decrypt_failed'}; }
  const data = JSON.parse(plaintext);
  const paid = data.trade_state === 'SUCCESS';
  return {ok:true, paid, out_trade_no: data.out_trade_no, trade_no: data.transaction_id, total: (data.amount?.total||0)/100, buyer: data.payer?.openid, trade_status: data.trade_state};
}

// ========== persistence ==========
const MEM=new Map();
function sb(){const u=get('SUPABASE_URL')||get('NEXT_PUBLIC_SUPABASE_URL');const k=get('SUPABASE_SERVICE_KEY')||get('SUPABASE_SERVICE_ROLE_KEY')||get('SUPABASE_KEY');return (u&&k)?{u:u.replace(/\/$/,''),k:k}:null;}
function kv(){const u=get('KV_REST_API_URL')||get('UPSTASH_REDIS_REST_URL');const t=get('KV_REST_API_TOKEN')||get('UPSTASH_REDIS_REST_TOKEN');return (u&&t)?{u:u.replace(/\/$/,''),t:t}:null;}
async function saveOrder(rec){
  rec.updated_at=new Date().toISOString();
  const s=sb();
  if(s){try{
    const r=await fetch(s.u+'/rest/v1/bds_orders',{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify([rec]),signal:AbortSignal.timeout(8000)});
    return {store:'supabase',ok:r.ok,status:r.status};
  }catch(e){return {store:'supabase',ok:false,error:e.message};}}
  const k=kv();
  if(k){try{
    const r=await fetch(k.u+'/set/bds_order_'+rec.out_trade_no,{method:'POST',headers:{Authorization:'Bearer '+k.t,'Content-Type':'application/json'},body:JSON.stringify(rec),signal:AbortSignal.timeout(8000)});
    // 维护 ref -> out_trade_no 索引（listByRef 的 KV 回退依赖它；幂等去重）
    if(rec.ref){
      try{
        const idx=await dbGet('orders_by_ref_'+rec.ref);
        const arr=Array.isArray(idx)?idx:[];
        if(arr.indexOf(rec.out_trade_no)<0){arr.push(rec.out_trade_no);await dbSet('orders_by_ref_'+rec.ref,arr);}
      }catch(e){}
    }
    return {store:'kv',ok:r.ok,status:r.status};
  }catch(e){return {store:'kv',ok:false,error:e.message};}}
  const prev=MEM.get(rec.out_trade_no)||{};MEM.set(rec.out_trade_no,Object.assign(prev,rec));
  return {store:'memory',ok:true};
}
async function getOrder(out){
  const s=sb();
  if(s){try{
    const r=await fetch(s.u+'/rest/v1/bds_orders?out_trade_no=eq.'+encodeURIComponent(out)+'&select=*',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});
    const j=await r.json();return (Array.isArray(j)&&j[0])?j[0]:null;
  }catch(e){return null;}}
  const k=kv();
  if(k){try{
    const r=await fetch(k.u+'/get/bds_order_'+out,{headers:{Authorization:'Bearer '+k.t},signal:AbortSignal.timeout(8000)});
    const j=await r.json();return j&&j.result?JSON.parse(j.result):null;
  }catch(e){return null;}}
  return MEM.get(out)||null;
}
async function countInvited(inv){
  const s=sb();if(!s||!inv)return null;
  try{
    const r=await fetch(s.u+'/rest/v1/bds_orders?invited_by=eq.'+encodeURIComponent(inv)+'&status=eq.paid&select=out_trade_no',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});
    const j=await r.json();return Array.isArray(j)?j.length:0;
  }catch(e){return null;}
}
async function listByRef(ref){
  if(!ref)return [];
  const s=sb();
  if(s){try{
    const r=await fetch(s.u+'/rest/v1/bds_orders?ref=eq.'+encodeURIComponent(ref)+'&status=eq.paid&select=slug,plan,out_trade_no,trade_no,amount',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});
    const j=await r.json();
    if(Array.isArray(j)&&j.length)return j;
  }catch(e){}}
  // KV 回退: orders_by_ref_<ref> 索引 -> 逐单读取 bds_order_<out_trade_no>
  // (修: 此前 listByRef 只查 Supabase，而 Vercel 部署无 Supabase → 付费用户的"已解锁列表"恒空)
  try{
    const idx=await dbGet('orders_by_ref_'+ref);
    const arr=Array.isArray(idx)?idx:[];
    const out=[];
    for(const o of arr){
      const rec=await getOrder(o);
      if(rec&&rec.status==='paid')out.push({slug:rec.slug,plan:rec.plan,out_trade_no:rec.out_trade_no,trade_no:rec.trade_no,amount:rec.amount});
    }
    return out;
  }catch(e){return [];}
}
function storeKind(){return sb()?'supabase':(kv()?'kv':(fileStore()?'file':'memory'));}
const MEMKV=new Map();

// 文件存储回退：仅当设置了 FILE_STORE_DIR 且没有远端存储时启用。
// 用途: 自托管实例（无 KV）也能持久化订单/权益，而不是进程一重启就丢。
// Vercel 上不设置该变量 → 行为完全不变（KV 优先）。
function fileStore(){
  try{const d=process.env.FILE_STORE_DIR;return (d&&String(d).trim())?String(d).trim():null;}catch(e){return null;}
}
function filePath(key){
  const dir=fileStore();if(!dir)return null;
  const safe=String(key).replace(/[^A-Za-z0-9_.-]/g,'_').slice(0,180);
  return dir+'/'+safe+'.json';
}
async function fileGet(key){
  const p=filePath(key);if(!p)return null;
  try{
    const fs=require('node:fs/promises');
    return JSON.parse(await fs.readFile(p,'utf8'));
  }catch(e){return null;}
}
async function fileSet(key,val){
  const p=filePath(key);if(!p)return false;
  try{
    const fs=require('node:fs/promises');
    await fs.mkdir(fileStore(),{recursive:true});
    const tmp=p+'.tmp';
    await fs.writeFile(tmp,JSON.stringify(val),'utf8');
    await fs.rename(tmp,p);        // 原子替换，避免半截文件
    return true;
  }catch(e){return false;}
}
async function dbGet(key){
  const k=kv();
  if(k){try{const r=await fetch(k.u+'/get/'+encodeURIComponent('bds_'+key),{headers:{Authorization:'Bearer '+k.t},signal:AbortSignal.timeout(8000)});const j=await r.json();return j&&j.result?JSON.parse(j.result):null;}catch(e){}}
  const s=sb();
  if(s){try{const r=await fetch(s.u+'/rest/v1/bds_kv?k=eq.'+encodeURIComponent(key)+'&select=v',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});const j=await r.json();return (Array.isArray(j)&&j[0])?j[0].v:null;}catch(e){}}
  if(fileStore()){const v=await fileGet(key);if(v!==null&&v!==undefined)return v;}
  return MEMKV.has(key)?MEMKV.get(key):null;
}
async function dbSet(key,val){
  const k=kv();
  if(k){try{await fetch(k.u+'/set/'+encodeURIComponent('bds_'+key),{method:'POST',headers:{Authorization:'Bearer '+k.t,'Content-Type':'application/json'},body:JSON.stringify(val),signal:AbortSignal.timeout(8000)});return true;}catch(e){}}
  const s=sb();
  if(s){try{await fetch(s.u+'/rest/v1/bds_kv',{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=minimal'},body:JSON.stringify([{k:key,v:val}]),signal:AbortSignal.timeout(8000)});return true;}catch(e){}}
  if(fileStore()&&await fileSet(key,val))return true;
  MEMKV.set(key,val);return true;
}
const INVITE_CAP=50;
async function arcBonus(ref){
  const list=(await dbGet('arc_inv_'+ref))||[];
  return {friends:list.length,bonusSeconds:Math.min(list.length,INVITE_CAP)*600};
}

// ---------- alipay calls ----------
async function probePagePay(base){
  const r=alipayParams({out_trade_no:'T'+Date.now(),total_amount:'0.01',subject:'probe',product_code:'FAST_INSTANT_TRADE_PAY'},'alipay.trade.page.pay',base);
  if(r.error)return{error:r.error};
  const res=await fetch('https://openapi.alipay.com/gateway.do',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(r.params).toString(),redirect:'manual',signal:AbortSignal.timeout(20000)});
  let final=res.headers.get('location')||'';
  const txt=final?'':await res.text();
  let hops=0;
  while(final&&hops<3&&/appAssign/.test(final)){const rr=await fetch(final,{redirect:'manual',signal:AbortSignal.timeout(15000)});const nx=rr.headers.get('location')||'';if(!nx)break;final=nx;hops++;}
  const cashier=/excashier\.alipay\.com\/(standard\/)?auth\.htm|excashier\.alipay\.com\/cashier/.test(final);
  const fish=/FISHING_RISK|钓鱼/.test(final)||/钓鱼/.test(txt);
  let bizCode=null;try{const m=txt.match(/"code"\s*:\s*"(\d+)"/);if(m)bizCode=m[1];}catch(e){}
  return {http:res.status,cashier:cashier,final:String(final).slice(0,160),code:bizCode,verdict:cashier?'PASS (已生成收银台订单)':(fish?'FISHING_RISK (服务端直连被风控;浏览器端实测正常)':'NO-PERM/ERROR')};
}
async function alipayQuery(outTradeNo,mode){
  const APP=get('ALIPAY_APP_ID'),PRIV=getKey('ALIPAY_MERCHANT_PRIVATE_KEY');
  if(!APP||!PRIV)return{error:'缺 ALIPAY_APP_ID/私钥'};
  const params={app_id:APP,method:'alipay.trade.query',charset:'utf-8',sign_type:'RSA2',timestamp:ts(),version:'1.0',format:'JSON'};
  const plainBiz=JSON.stringify({out_trade_no:outTradeNo});
  const encrypted=mode==='plain'?plainBiz:aesEncrypt(plainBiz);
  params.biz_content=encrypted;
  if(encrypted!==plainBiz)params.encrypt_type='AES';
  params.sign=signParams(params,PRIV);
  const res=await fetch('https://openapi.alipay.com/gateway.do',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(params).toString(),signal:AbortSignal.timeout(20000)});
  const txt=await res.text();let j={};try{j=JSON.parse(txt);}catch(e){return{http:res.status,raw:txt.slice(0,400)};}
  let r=j.alipay_trade_query_response||{};
  if((j.encrypt_type==='AES'||r.encrypt_type==='AES')&&typeof r==='string'){r=JSON.parse(aesDecrypt(r)||'{}');}
  if(j.encrypt_type==='AES'&&typeof r==='string'&&r.indexOf('{')!==0){r={raw_cipher:r};}
  const paid=(r.code==='10000'&&(r.trade_status==='TRADE_SUCCESS'||r.trade_status==='TRADE_FINISHED'));
  return {http:res.status,code:r.code,msg:r.msg,sub:r.sub_code,trade_status:r.trade_status,trade_no:r.trade_no,buyer:r.buyer_logon_id||r.buyer_user_id,amount:r.total_amount,paid:!!paid,detail:r,resp_encrypt:!!(j.encrypt_type||r.encrypt_type)};
}
function readBody(req){return new Promise(res=>{let d='';req.on('data',c=>d+=c);req.on('end',()=>res(d));});}
function esc(v){return String(v).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');}

module.exports=async(req,res)=>{
  const u=new URL((req.url||'/'),'http://x');
  let route=u.searchParams.get('r')||u.pathname;
  route='/'+String(route).replace(/^\/+/,'').replace(/^api\//,'');
  if(route.indexOf('/api/')!==0)route='/api'+route;
  const base=baseFrom(req);
  const send=(c,o)=>{res.writeHead(c,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(o));};
  const text=(c,s,ct)=>{res.writeHead(c,{'Content-Type':ct||'text/plain; charset=utf-8'});res.end(s);};
  const raw=await readBody(req);
  let form={};try{const u2=new URL(u.search.slice(1),'http://x');u2.searchParams.forEach((v,k)=>form[k]=v);}catch(e){}
  if(raw){try{Object.assign(form,JSON.parse(raw));}catch(e){try{const u3=new URL('http://x/?'+raw);u3.searchParams.forEach((v,k)=>form[k]=v);}catch(e2){}}}
  const data=Object.assign(Object.fromEntries(u.searchParams),form);
  try{
    // 创建付款单 → 返回自动提交的收银台表单
    if(route==='/api/pay'){
      const plan=data.plan||'m10';
      const subMod=require('../lib/subwall.js');
      const subPlan=subMod.plans[plan];
      const isSub=!!(subPlan&&subPlan.cny>0);
      const price=isSub?subPlan.cny:PLANS[plan];
      if(!price){send(200,{ok:false,error:'未知套餐 plan='+plan});return;}
      const slug=String(data.slug||'tool').slice(0,120);
      const ref=String(data.ref||'').slice(0,32);
      const inv=String(data.inv||'').slice(0,32);
      const out=data.out_trade_no||('BDS_'+ref+'_'+plan+'_'+Date.now());
      let pct=0;
      const cnt=await countInvited(inv);
      if(cnt!==null){pct=ladderPct(cnt);}
      else{const cp=parseInt(data.pct,10);pct=(isFinite(cp)?Math.max(0,Math.min(70,cp)):0);}
      const amount=(price*(1-pct/100)).toFixed(2);
      await saveOrder({out_trade_no:out,slug:slug,ref:ref,invited_by:inv,plan:plan,kind:isSub?'sub':'unlock',list_price:String(price),pct:pct,amount:amount,status:'created'});
      const r=alipayParams({out_trade_no:out,total_amount:amount,subject:String(data.subject||('bingdashan '+plan+' unlock')).replace(/[^\x20-\x7e]/g,'').slice(0,120)||('bingdashan '+plan),product_code:'FAST_INSTANT_TRADE_PAY',timeout_express:'15m'},'alipay.trade.page.pay',base,{passback_params:encodeURIComponent(JSON.stringify({slug:slug,plan:plan,ref:ref,inv:inv}))});
      if(r.error){send(200,{ok:false,error:r.error});return;}
      const html='<!DOCTYPE html><html><head><meta charset="utf-8"><title>正在跳转支付宝…</title></head><body style="font-family:system-ui;text-align:center;padding:40px">正在跳转支付宝收银台…<form id="f" action="https://openapi.alipay.com/gateway.do" method="POST" accept-charset="utf-8">'+Object.keys(r.params).map(k=>'<input type="hidden" name="'+k+'" value="'+esc(r.params[k])+'"/>').join('')+'</form><script>document.getElementById("f").submit();</script></body></html>';
      text(200,html,'text/html; charset=utf-8');return;
    }
    // Stripe Checkout 会话创建（USD/国际卡）
    if(route==='/api/stripe/checkout'){
      const plan=data.plan||'pro';
      const sp=stripeMod.SUB_PLANS[plan];
      if(!sp){send(200,{ok:false,error:'unknown_plan'});return;}
      const slug=String(data.slug||'tool').slice(0,120);
      const ref=String(data.ref||'').slice(0,32);
      const inv=String(data.inv||'').slice(0,32);
      const out=data.out_trade_no||('BDS_'+ref+'_'+plan+'_'+Date.now());
      await saveOrder({out_trade_no:out,slug:slug,ref:ref,invited_by:inv,plan:plan,kind:'sub',list_price:String(sp.usd),pct:0,amount:String(sp.usd),status:'created',currency:'usd'});
      const session=await stripeMod.createCheckoutSession(base,plan,ref,slug,inv,out);
      if(session.error){send(200,{ok:false,error:session.error});return;}
      send(200,{ok:true,sessionId:session.sessionId,url:session.url});
      return;
    }
    // Stripe Webhook
    if(route==='/api/stripe/webhook'){
      const sig=req.headers['stripe-signature']||'';
      const raw=await readBody(req);
      const result=await stripeMod.verifyWebhook(raw,sig);
      if(!result.ok){send(400,{ok:false,error:result.error});return;}
      const handled=await stripeMod.handlePaymentSuccess(result.event,saveOrder,async(ref,plan,opts)=>require('../lib/subwall.js').activate(ref,plan,opts),async(inv,rec)=>require('../lib/commission.js').record(inv,rec));
      send(200,handled);
      return;
    }
    // WeChat Pay 下单（Native 扫码）
    if(route==='/api/wxpay/create'){
      const plan=data.plan||'pro';
      const slug=String(data.slug||'tool').slice(0,120);
      const ref=String(data.ref||'').slice(0,32);
      const inv=String(data.inv||'').slice(0,32);
      // 微信要求 out_trade_no 6-32 字符（[a-zA-Z0-9_-]）；长 ref 会拼出超长单号被拒
      const out=data.out_trade_no||('BDSW_'+plan.slice(0,4)+'_'+Date.now().toString(36)+crypto.randomBytes(3).toString('hex')+(ref?'_'+ref:'')).replace(/[^a-zA-Z0-9_-]/g,'').slice(0,32);
      let sp=PLANS[plan];
      if(typeof sp==='number')sp={cny:sp};
      if(!sp||!sp.cny){send(200,{ok:false,error:'unknown_plan'});return;}
      await saveOrder({out_trade_no:out,slug:slug,ref:ref,invited_by:inv,plan:plan,kind:'sub',list_price:String(sp.cny),pct:0,amount:String(sp.cny),status:'created',currency:'cny',gateway:'wxpay'});
      const result=await wxpayCreateOrder(base,plan,ref,slug,inv,out);
      if(result.error){send(200,{ok:false,error:result.error});return;}
      send(200,{ok:true,code_url:result.code_url,out_trade_no:out});
      return;
    }
    // WeChat Pay 回调
    if(route==='/api/wxpay/notify'){
      const raw=await readBody(req);
      const headers={};
      req.headers && Object.keys(req.headers).forEach(k=>{headers[k.toLowerCase()]=req.headers[k];});
      const result=await wxpayHandleNotify(raw,headers);
      if(result.ok&&result.paid){
        const prev=(await getOrder(result.out_trade_no))||{};
        await saveOrder(Object.assign({},prev,{out_trade_no:result.out_trade_no,trade_no:result.trade_no,buyer:result.buyer,amount:result.total,trade_status:result.trade_status,status:'paid',paid_at:new Date().toISOString(),currency:'cny'}));
        if(prev.kind==='sub'&&prev.ref&&prev.status!=='paid'){
          try{ await require('../lib/subwall.js').activate(prev.ref,prev.plan,{out_trade_no:result.out_trade_no}); }catch(e){}
        }
        if(prev.invited_by&&prev.invited_by!==prev.ref&&prev.status!=='paid'){
          try{ await require('../lib/commission.js').record(prev.invited_by,{out_trade_no:result.out_trade_no,amount:result.total,plan:prev.plan,kind:prev.kind}); }catch(e){}
        }
        text(200,'SUCCESS');return;
      }
      text(400,'FAIL');return;
    }
    // 支付宝异步回调:验签 + 落库,必须返回纯文本 success
    if(route==='/api/notify'){
      const r=verifyNotify(data);
      if(r.ok){
        const prev=(await getOrder(r.out_trade_no))||{};
        await saveOrder(Object.assign({},prev,{out_trade_no:r.out_trade_no,trade_no:r.trade_no,buyer:r.buyer,amount:r.total,trade_status:r.trade_status,status:'paid',paid_at:new Date().toISOString()}));
        // 订阅单：支付成功 → 服务端权威激活（幂等：仅首次由 created→paid 时激活一次）
        if(prev.kind==='sub'&&prev.ref&&prev.status!=='paid'){
          try{ await require('../lib/subwall.js').activate(prev.ref,prev.plan,{out_trade_no:r.out_trade_no}); }catch(e){}
        }
        // 分佣：推荐人（invited_by）获得佣金入账（幂等：按 out_trade_no 去重）
        if(prev.invited_by&&prev.invited_by!==prev.ref&&prev.status!=='paid'){
          try{ await require('../lib/commission.js').record(prev.invited_by,{out_trade_no:r.out_trade_no,amount:r.total,plan:prev.plan,kind:prev.kind}); }catch(e){}
        }
        text(200,'success');return;
      }
      text(400,'fail');return;
    }
    // 查单:以支付宝为准(幂等),顺带回写落库
    if(route==='/api/order'){
      const out=String(data.out_trade_no||'');
      if(!out){send(200,{ok:false,error:'缺 out_trade_no'});return;}
      const rec0=(await getOrder(out))||{out_trade_no:out};
      // 按网关分流：微信单查微信、其余查支付宝（源均为支付方权威，幂等回写）
      if(rec0.gateway==='wxpay'){
        const wq=await wxpayQueryOrder(out);
        if(wq.paid){
          await saveOrder(Object.assign({},rec0,{out_trade_no:out,trade_status:'SUCCESS',amount:wq.amount||rec0.amount,status:'paid',paid_at:(rec0&&rec0.paid_at)||new Date().toISOString()}));
          if(rec0.kind==='sub'&&rec0.ref&&rec0.status!=='paid'){
            try{ await require('../lib/subwall.js').activate(rec0.ref,rec0.plan,{out_trade_no:out}); }catch(e){}
          }
        }
        send(200,{ok:true,paid:!!wq.paid,status:wq.paid?'paid':(rec0.status||'unknown'),trade_state:wq.trade_state||null,slug:rec0.slug||null,plan:rec0.plan||null,gateway:'wxpay'});
        return;
      }
      const q=await alipayQuery(out);
      const rec=(await getOrder(out))||{out_trade_no:out};
      if(q.paid){
        await saveOrder(Object.assign({},rec,{out_trade_no:out,trade_no:q.trade_no,buyer:q.buyer,amount:q.amount,trade_status:q.trade_status,status:'paid',paid_at:(rec&&rec.paid_at)||new Date().toISOString()}));
        // 订阅单：查单确认支付成功同样激活（幂等，覆盖 notify 未达的情形）
        if(rec.kind==='sub'&&rec.ref&&rec.status!=='paid'){
          try{ await require('../lib/subwall.js').activate(rec.ref,rec.plan,{out_trade_no:out}); }catch(e){}
        }
        if(rec.invited_by&&rec.invited_by!==rec.ref&&rec.status!=='paid'){
          try{ await require('../lib/commission.js').record(rec.invited_by,{out_trade_no:out,amount:q.amount,plan:rec.plan,kind:rec.kind}); }catch(e){}
        }
      }
      send(200,{ok:true,paid:!!q.paid,status:q.paid?'paid':(rec.status||'unknown'),trade_status:q.trade_status,trade_no:q.trade_no,slug:rec.slug||null,plan:rec.plan||null,code:q.code,sub:q.sub,msg:q.msg});
      return;
    }
    // 按推荐人 ref 查已解锁工具(跨设备)
    if(route==='/api/entitle'){
      const ref=String(data.ref||'').slice(0,32);
      if(!ref){send(200,{ok:false,error:'缺 ref'});return;}
      if(storeKind()==='memory'){send(200,{ok:true,store:'memory',ref:ref,slugs:[]});return;}
      const rows=await listByRef(ref);
      const slugs=Array.from(new Set(rows.map(x=>x.slug).filter(Boolean)));
      const cnt=await countInvited(ref);
      send(200,{ok:true,store:storeKind(),ref:ref,slugs:slugs,orders:rows.length,plans:rows.map(x=>x.plan).filter(Boolean),friends:cnt,pct:ladderPct(cnt||0)});
      return;
    }
    // AI 娱乐中心:时长状态 / 心跳 / 邀请奖励
    if(route==='/api/arcade'){
      const ref=String(data.ref||'').slice(0,32);
      const by=String(data.by||'').slice(0,32);
      const slugv=String(data.slug||'').slice(0,80);
      const act=String(data.a||'state');
      if(!ref){send(200,{ok:false,error:'缺 ref'});return;}
      if(act==='invite'&&by&&by!==ref){
        const list=(await dbGet('arc_inv_'+ref))||[];
        if(list.indexOf(by)<0)list.push(by);
        await dbSet('arc_inv_'+ref,list);
        const inviterBonus=Math.min(list.length,INVITE_CAP)*600;
        await dbSet('arc_bonus_'+ref,inviterBonus);
        await dbSet('arc_bonus_'+by,Math.max(600,parseInt((await dbGet('arc_bonus_'+by))||0,10)||0));
        const mine=await dbGet('arc_inv_'+by);
        send(200,{ok:true,friends:list.length,bonusSeconds:inviterBonus,inviteeBonus:600,store:storeKind()});return;
      }
      // 服务器权威计费:免费额度一次性入账、心跳按服务器时钟扣钱,绝不信任客户端自报 bal
      // 邀请奖励（friends/bonusSeconds）——修复：此前此处缺少 const b=await arcBonus(ref)，
      // 导致 state 分支与 tick 分支均抛 ReferenceError(b is not defined)，心跳计费全线失效。
      const b=await arcBonus(ref);
      const freeLeft=parseInt((await dbGet('arc_free_'+ref))||0,10)||0;
      if(!(await dbGet('arc_init_'+ref))&&freeLeft<=0){
        await dbSet('arc_free_'+ref,FREE_SEC);
        await dbSet('arc_init_'+ref,'1');
      }
      let balanceSeconds=parseInt((await dbGet('arc_bal_'+ref))||0,10)||0;
      if(act==='tick'){
        const now=Date.now();
        const hb=parseInt((await dbGet('arc_hb_'+ref))||0,10)||0;
        // 服务器自己计时:相邻两次心跳之间的真实时间(上限 90s,防刷新/跳时间戳刷秒)
        let elapsed=0;
        if(hb)elapsed=Math.max(0,Math.min(90,Math.floor((now-hb)/1000)));
        await dbSet('arc_hb_'+ref,now);
        if(slugv)await dbSet('arc_use_'+ref,{slug:slugv,at:new Date().toISOString()});
        if(elapsed>0){
          // 服务器权威计费（arcade_billing.js 纯函数，可单测）：
          // 免费额度优先扣 → 邀请奖励只并入增量（水位账本 arc_bapp_）→ 扣付费/奖励余额。
          // 修复：旧逻辑每 tick 把邀请奖励全额加回余额（balanceSeconds+effBonus-br），可无限刷时长。
          const bonusTarget=Math.max(b.bonusSeconds,parseInt((await dbGet('arc_bonus_'+ref))||0,10)||0);
          const bonusApplied=parseInt((await dbGet('arc_bapp_'+ref))||0,10)||0;
          const out=billing.applyTick({freeLeft:await dbGet('arc_free_'+ref),bal:balanceSeconds,bonusTarget,bonusApplied},elapsed);
          balanceSeconds=out.bal;
          await dbSet('arc_bapp_'+ref,out.bonusApplied);
          await dbSet('arc_free_'+ref,out.freeLeft);
          await dbSet('arc_bal_'+ref,balanceSeconds);
        }
      }
      const sb3=(await dbGet('arc_bonus_'+ref))||0;
      const freeRemaining=parseInt((await dbGet('arc_free_'+ref))||0,10)||0;
      // 服务端待付单（AutoOps 订单挽回写入 arc_pend_<ref>；只读，绝不触碰计费锚点）
      let pending=null;
      try{
        const pv=await dbGet('arc_pend_'+ref);
        if(pv&&parseInt(pv.expires_at||'0',10)>Date.now()) pending={plan:pv.plan,amount:pv.amount,pct:pv.pct||0,out_trade_no:pv.out_trade_no};
      }catch(e){}
      send(200,{ok:true,store:storeKind(),ref:ref,friends:b.friends,bonusSeconds:Math.max(b.bonusSeconds,parseInt(sb3,10)||0),balanceSeconds:balanceSeconds,freeSeconds:freeRemaining,pending:pending});return;
    }
    if(route==='/api/verify'){
      const r=await probePagePay(base);
      send(200,{ok:true,result:r,verdict:r.verdict||('ERROR '+(r.error||''))});
      return;
    }
    if(route==='/api/aliq'){
      const out=String(data.out_trade_no||'BDS_ALIQ_PROBE_'+(Date.now()%1000000));
      const mode=String(data.mode||(get('ALIPAY_AES_KEY')?'aes':'plain'));
      const q=await alipayQuery(out,mode);
      const body={ok:true,probe:'alipay.trade.query',out_trade_no:out,mode:mode,aes_configured:!!get('ALIPAY_AES_KEY'),result:q};
      if(String(data.debug)==='1')body.sig_fp=privFingerprint();
      send(200,body);return;
    }
    if(route==='/api/paid'){
      send(200,{ok:true,received:data,base:base,store:storeKind()});return;
    }
    if(route==='/api/config'){send(200,{ok:true,app_id:get('ALIPAY_APP_ID'),account:get('ALIPAY_ACCOUNT'),base:base,store:storeKind(),plans:PLANS,wallets:WALLETS,ready:!!(get('ALIPAY_APP_ID')&&getKey('ALIPAY_MERCHANT_PRIVATE_KEY')&&getKey('ALIPAY_ALIPAY_PUBLIC_KEY'))});return;}
    if(route==='/api/health'){send(200,{ok:true,env:{app:!!get('ALIPAY_APP_ID'),priv:!!getKey('ALIPAY_MERCHANT_PRIVATE_KEY'),pub:!!getKey('ALIPAY_ALIPAY_PUBLIC_KEY'),supabase:!!sb(),kv:!!kv()},store:storeKind()});return;}
    // Morning-Youth 独立路由
    // 注意：morning-youth.js 导出 {onRequest,plans} 非标准 Vercel handler，
    // 必须经本分发器转发；rewrite 会把子路径放 __path（如 morning-youth/config）。
    if(route.startsWith('/api/morning-youth')||u.pathname.indexOf('/api/morning-youth')===0){
      try{
        const mod = require('../lib/morning-youth.js');
        // 恢复原始子路径：优先 rewrite 的 __path，其次原始 pathname，最后 r 参数
        const subRaw = String(u.searchParams.get('__path')||'').replace(/^\/+/,'').replace(/^api\//,'');
        let myPath = route;
        if(subRaw && subRaw.indexOf('morning-youth')===0) myPath = '/api/'+subRaw;
        else if(u.pathname.indexOf('/api/morning-youth')===0) myPath = u.pathname;
        data.path = myPath;
        return await mod.onRequest(req,res,data);
      }catch(e){
        send(500,{ok:false,error:'morning-youth handler error: '+e.message});
      }
      return;
    }
    // 订阅墙 独立路由
    if(route.startsWith('/api/subwall')){
      try{
        const mod = require('../lib/subwall.js');
        // 保持原始 path 给 subwall；同时透传 window.__SUBWALL_REF__ 身份（若配置了）
        data.path = route;
        if(!data.ref){
          const pid = String((req.headers['x-ref']||req.headers['x-user-ref']||'')||'').slice(0,64);
          if(pid)data.ref=pid;
        }
        return await mod.onRequest(req,res,data);
      }catch(e){
        send(500,{ok:false,error:'subwall handler error: '+e.message});
      }
      return;
    }
    // 分佣账本 独立路由
    if(route.startsWith('/api/commission')){
      try{
        const mod = require('../lib/commission.js');
        data.path = route;
        if(!data.ref){
          const pid = String((req.headers['x-ref']||req.headers['x-user-ref']||'')||'').slice(0,64);
          if(pid)data.ref=pid;
        }
        return await mod.onRequest(req,res,data);
      }catch(e){
        send(500,{ok:false,error:'commission handler error: '+e.message});
      }
      return;
    }
    send(404,{ok:false,error:'not found',route:route});
  }catch(e){send(500,{ok:false,error:e.message,stack:(e.stack||'').split('\n').slice(0,3)});}
};
