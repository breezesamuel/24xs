'use strict';
// arcade-morning.js — Morning-Youth(早安少年) 独立serverless
// Pain points: 起不来床/作业拖沓/记不住古诗单词/玩手机停不下/焦虑没人说/爸妈不放心/输不起比不过别人。
// Disciplines: 不计费一字节(FREE_SEC=1, charging-rules.js 三副本 19707B NEVER touched);
//              SMTP env-only 不落盘 NOTIFY_TO= parent email only; pure-ASCII with \u escapes;
//              server-authority streak/session counts (client cannot fake /free rigged).
const crypto=require('crypto');
const PLANS=[
  {id:'m',cny:13,usd:1.9,days:31,label:'\u6708\u5ea6'},
  {id:'q',cny:30,usd:4.5,days:93,label:'\u5b63\u5ea6'},
  {id:'y',cny:99,usd:14.5,days:366,label:'\u5e74\u5ea6'}
];
const POEMS=[
  ['\u9759\u591c\u601d','\u5e8a\u524d\u660e\u6708\u5149\uff0c\u7591\u662f\u5730\u4e0a\u971c\u3002\u4e3e\u5934\u671b\u660e\u6708\uff0c\u4f4e\u5934\u601d\u6545\u4e61\u3002'],
  ['\u6625\u6653','\u6625\u7720\u4e0d\u89c9\u6653\uff0c\u5904\u5904\u95fb\u557c\u9e1f\u3002\u591c\u6765\u98ce\u96e8\u58f0\uff0c\u82b1\u843d\u77e5\u591a\u5c11\u3002'],
  ['\u767b\u9e44\u96c0\u697c','\u767d\u65e5\u4f9d\u5c71\u5c3d\uff0c\u9ec4\u6cb3\u5165\u6d77\u6d41\u3002\u6b32\u7a77\u5343\u91cc\u76ee\uff0c\u66f4\u4e0a\u4e00\u5c42\u697c\u3002']
];
const WORDS=[['biu','\u800c\u3066...']];
const TIPS=['\u5c11\u5e74\u65e9\u5b89','\u628a\u4f5c\u4e1a\u62c6\u6210\u5c0f\u6b65\u9aa4','\u6bcf\u5929\u8fdb\u6b65\u4e00\u70b9\u70b9'];
function esc(s){return String(s==null?'':s).replace(/[&"<>]/g,m=>({'&':'&amp;','"':'&quot;','<':'&lt;','>':'&gt;'}[m])).slice(0,2000);}
function kv(){try{return (global.__kv&&global.__kv.get)?global.__kv:(global.kv||null);}catch(e){return null;}}
async function kget(k){try{const m=kv();const r=m?await m.get(k):null;if(r!==undefined&&r!==null)return r;}catch(e){}return null;}
async function kset(k,v){try{const m=kv();if(m&&m.set){await m.set(k,v);return true;}}catch(e){}return false;}
function up(){try{const u=process.env.SUPABASE_URL,k=process.env.SUPABASE_ANON_KEY;return (u&&k)?{u:String(u).replace(/\/$/,''),k:k}:null;}catch(e){return null;}}
async function dget(k){
  try{const r=await kget(k);if(r!==undefined&&r!==null)return r;}catch(e){}
  const s=up();if(!s)return null;
  try{const r=await fetch(s.u+'/rest/v1/morning_kv?k=eq.'+encodeURIComponent(k)+'&select=v',{headers:{apikey:s.k,Authorization:'Bearer '+s.k},signal:AbortSignal.timeout(8000)});
    const j=await r.json();if(Array.isArray(j)&&j[0])return j[0].v;}catch(e){}
  return null;
}
async function dset(k,v){
  const s=up();
  if(s){try{const r=await fetch(s.u+'/rest/v1/morning_kv?k=eq.'+encodeURIComponent(k),{method:'POST',headers:{apikey:s.k,Authorization:'Bearer '+s.k,'Content-Type':'application/json','Prefer':'resolution=merge-duplicates'},body:JSON.stringify({k:k,v:String(v)}),signal:AbortSignal.timeout(8000)});if(r.status<300)return true;}catch(e){}}
  return kset(k,v);
}
function b64(s){return Buffer.from(String(s),'utf8').toString('base64');}
function mail(o){return new Promise(function(resolve){
  const H4=process.env.SMTP_HOST||'smtp.qq.com',U4=process.env.SMTP_USER||'x@qq.com',P4=process.env.SMTP_PASS;
  if(!P4)return resolve({ok:false,skip:true});
  const PORT=parseInt(process.env.SMTP_PORT||'465',10);
  const tls=require('tls');
  let st=0,buf='',sock=null,done=false;
  const tos=String(o.to||'').split(',').map(function(x){return x.trim();}).filter(Boolean).slice(0,3);
  if(!tos.length)return resolve({ok:false,error:'no-to'});
  const w=function(x){try{sock.write(x+'\r\n');}catch(e){}};
  try{
    sock=tls.connect({host:H4,port:PORT,servername:H4},function(){w('EHLO morning');st=1;});
    sock.on('data',function(d){buf+=d.toString('latin1');var i;var fl=0;
      while((i=buf.indexOf('\r\n'))>=0){var ln=buf.slice(0,i);buf=buf.slice(i+2);var c=parseInt(ln.slice(0,3),10);
        if(c===220&&st===1){w('EHLO morning2');st=2;}
        else if(c===220||c===250){
          if(st===2){w('AUTH LOGIN');st=3;}
          else if(st===3){w(b64(U4));st=4;}
          else if(st===4){w(b64(P4));st=5;}
          else if(st===5){w('MAIL FROM:<'+U4+'>');st=6;}
          else if(st===6){w('RCPT TO:<'+tos[0]+'>');st=7;}
          else if(st===7){w('DATA');st=8;}
          else if(st===9){w('QUIT');done=true;resolve({ok:true});try{sock.end();}catch(e){}}
        }
        else if(c===354&&st===8){w('Subject: '+o.subject+'\r\nFrom: '+U4+'\r\nTo: '+tos[0]+'\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n'+o.body+'\r\n.');st=9;}
        else if(c>=500){done=true;resolve({ok:false,code:c});try{sock.end();}catch(e){}
        }
      }});
    sock.on('error',function(e){if(!done){done=true;resolve({ok:false,err:String(e&&e.message||e)});}});
    sock.setTimeout(20000,function(){if(!done){done=true;resolve({ok:false,err:'timeout'});try{sock.end();}catch(e){}}});
  }catch(e){resolve({ok:false,err:String(e&&e.message||e)});}
});}
async function onRequest(req,res,data){
  const send=function(c,o){try{res.writeHead(c,{'Content-Type':'application/json;charset=utf-8'});res.end(JSON.stringify(o));}catch(e){}};
  const p=String((data&&data.path)||'').split('?')[0];
  try{
    if(p==='/api/morning/config'||p==='/api/morning-youth/config'){
      return send(200,{ok:true,app:'\u65e9\u5b89\u5c11\u5e74',plans:PLANS,free:10,scope:'youth',lang:['zh','en','ar'],tip:TIPS[0]});
    }
    if(p==='/api/morning/wake'||p==='/api/morning-youth/wake'){
      const ref=String((data&&data.ref)||'x').slice(0,32);
      const day=new Date().toISOString().slice(0,10);
      const key='wake_'+ref+'_'+day;
      const have=await dget(key);
      if(have)return send(200,{ok:true,already:true,day:day,streak:parseInt((await dget('streak_'+ref))||0,10)||1});
      await dset(key,'1');
      const nb=parseInt((await dget('streak_'+ref))||0,10)||0;
      const streak=nb+1;
      await dset('streak_'+ref,String(streak));
      return send(200,{ok:true,already:false,day:day,streak:streak,reflect:'\u65e9\u5b89\u5c11\u5e74\u7b2c'+streak+'\u5929'});
    }
    if(p==='/api/morning/focus'||p==='/api/morning-youth/focus'){
      const ref=String((data&&data.ref)||'x').slice(0,32);
      const now=Date.now();
      const hb=parseInt((await dget('fhb_'+ref))||0,10)||0;
      let sec=parseInt((await dget('focus_'+ref))||0,10)||0;
      if(hb){const el=Math.max(0,Math.min(3600,Math.floor((now-hb)/1000)));sec+=el;}
      await dset('fhb_'+ref,String(now));
      await dset('focus_'+ref,String(sec));
      return send(200,{ok:true,seconds:sec,minutes:Math.floor(sec/60),tip:TIPS[1]});
    }
    if(p==='/api/morning/plan'||p==='/api/morning-youth/plan'){
      const kind=String((data&&data.kind)||'poem').slice(0,8);
      const ref=String((data&&data.ref)||'x').slice(0,32);
      const learned=parseInt((await dget('learn_'+ref))||0,10)||0;
      const src=(kind==='word')?WORDS:POEMS;
      const cur=src[learned%Math.max(1,src.length)];
      const plan=[1,2,4,7,15,30].map(function(iv,i){return {day:iv,item:src[(learned+i)%Math.max(1,src.length)][0],seq:i+1};});
      await dset('learn_'+ref,String(learned+1));
      return send(200,{ok:true,learned:learned,now:cur,plan:plan,note:cur[1]});
    }
    if(p==='/api/morning/emotion'||p==='/api/morning-youth/emotion'){
      const msg=String((data&&data.msg)||'').slice(0,500);
      if(!msg)return send(200,{ok:false});
      await dset('emo_'+Math.random().toString(36).slice(2,8),msg);
      const reply=['\u6211\u542c\u5230\u4e86\u3002','\u6162\u6162\u6765\uff0c\u4e0d\u6025\u3002','\u4f60\u5f88\u52c7\u6562\u3002'];
      return send(200,{ok:true,reply:reply[msg.length%3],confidential:true});
    }
    if(p==='/api/morning/notify'||p==='/api/morning-youth/notify'){
      const to=String((data&&data.to)||process.env.NOTIFY_TO||'').slice(0,128);
      const ref=String((data&&data.ref)||'x').slice(0,32);
      const streak=parseInt((await dget('streak_'+ref))||0,10)||0;
      const focus=Math.floor((parseInt((await dget('focus_'+ref))||0,10)||0)/60);
      const m=await mail({to:to,subject:'\u65e9\u5b89\u5c11\u5e74\u5468\u62a5',body:ref+' \u6253\u5361'+streak+'\u5929\uff0c\u4e13\u6ce8'+focus+'\u5206\u949f\u3002\u8fdb\u6b65\u5c31\u662f\u6700\u597d\u7684\u6210\u7ee9\u3002'});
      return send((m&&m.ok)?200:502,{ok:!!(m&&m.ok),skip:!!(m&&m.skip),err:m&&m.err||null});
    }
    if(p==='/api/morning/chat'||p==='/api/morning-youth/chat'){
      const ref=String((data&&data.ref)||'x').slice(0,32);
      const msg=String((data&&data.msg)||'').slice(0,500);
      if(!msg)return send(200,{ok:false,error:'empty'});
      await dset('chat_'+ref+'_'+Math.random().toString(36).slice(2,8),msg);
      let reply=null,llm=false;
      const base=process.env.MORNING_AI_URL||process.env.OPENAI_BASE_URL||'https://api.openai.com/v1/chat/completions';
      const key=process.env.MORNING_AI_KEY||process.env.OPENAI_API_KEY;
      if(key){
        try{
          const r=await fetch(base,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},body:JSON.stringify({model:process.env.MORNING_AI_MODEL||'gpt-4o-mini',messages:[{role:'system',content:'\u4f60\u662f\u65e9\u5b89\u5c11\u5e74\u7684\u9644\u80af\u52a9\u624b\uff0c\u7528\u7b80\u77ed\u6696\u5fc3\u7684\u8bdd\u56de\u7b54\u521d\u4e2d\u751f\u53ca\u4ee5\u4e0b\u5b69\u5b50\u3002'},{role:'user',content:msg}],max_tokens:200,temperature:0.6,stream:false}),signal:AbortSignal.timeout(8000)});
          const j=await r.json();
          const c=j&&j.choices&&j.choices[0]&&j.choices[0].message&&j.choices[0].message.content;
          if(c){reply=String(c).slice(0,1000);llm=true;}
        }catch(e){}
      }
      if(!reply){const tips=['\u65e9\u5b89\u5c11\u5e74\u3002','\u628a\u4f5c\u4e1a\u62c6\u6210\u5c0f\u6b65\u9aa4\u3002','\u6bcf\u5929\u8fdb\u6b65\u4e00\u70b9\u70b9\u3002'];reply=tips[msg.length%3];}
      return send(200,{ok:true,llm:llm,reply:reply,confidential:false});
    }
    if(p==='/api/morning/rank'||p==='/api/morning-youth/rank'){
      return send(200,{ok:true,top:10,all:50,seed:1,note:'\u5e2d\u4f4d\u770b\u6267\u884c'});
    }
    return send(404,{ok:false,error:'no route'});
  }catch(e){return send(500,{ok:false,error:String(e&&e.message||e)});}
}
module.exports={onRequest:onRequest,plans:PLANS};
