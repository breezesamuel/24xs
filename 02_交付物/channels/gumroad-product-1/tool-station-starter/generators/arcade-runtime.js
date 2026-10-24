// bingdashan AI arcade runtime: per-minute billing + referral bonus
(function(){
var d=document;
var FREE_SEC=600;      // 10 minutes free per game
var RATE=0.2;          // CNY per minute
var PACKS=[['t30',30,6],['t60',60,12],['t300',300,60],['t1000',1000,200]];
var L={left:{zh:'剩余时间',en:'Time left',ar:'الوقت المتبقي'},
 free:{zh:'免费',en:'free',ar:'مجاني'},
 over:{zh:'免费时长已用完',en:'Free minutes used up',ar:'انتهت الدقائق المجانية'},
 buy:{zh:'充值时长',en:'Buy minutes',ar:'شراء دقائق'},
 rate:{zh:'每分钟 0.2 元',en:'0.2 CNY / minute',ar:'0.2 يوان/دقيقة'},
 invite:{zh:'邀请 1 人双方各送 10 分钟',en:'Invite a friend — both get +10 min',ar:'ادع صديقا لتحصلا على 10 دقائق'},
 invite2:{zh:'你的邀请链接',en:'Your invite link',ar:'رابط دعوتك'},
 invited:{zh:'已邀请',en:'Invited',ar:'مدعوون'},
 got:{zh:'已到账 10 分钟',en:'+10 minutes added',ar:'تمت اضافة 10 دقائق'},
 minutes:{zh:'分钟',en:'min',ar:'دقيقة'},
 close:{zh:'关闭',en:'Close',ar:'إغلاق'},
 login:{zh:'去支付',en:'Pay now',ar:'ادفع'},
 demo:{zh:'(支付通道接入后自动到账)',en:'(credited automatically once payment is live)',ar:'(تضاف تلقائيا)'}};
var lang='zh';
function cur(){try{var l=localStorage.getItem('bds_lang');if(l)return l;}catch(e){}var n=(navigator.language||'zh').toLowerCase();return n.indexOf('zh')===0?'zh':(n.indexOf('ar')===0?'ar':'en');}
function t(k){return (L[k]&&(L[k][lang]||L[k].zh))||k;}
var LS=function(k,v){try{if(v===undefined)return localStorage.getItem('bds_'+k);localStorage.setItem('bds_'+k,v);}catch(e){return null;}};
function slug(){return window.BDS_SLUG||'game';}
function me(){var r=LS('ref');if(!r){r='U'+Math.random().toString(36).slice(2,10).toUpperCase();LS('ref',r);}return r;}
function num(k){return parseInt(LS(k)||'0',10)||0;}
function setnum(k,v){LS(k,String(Math.max(0,Math.round(v))));}
function freeUsed(){return num('af_'+slug());}
function bal(){return num('bal');}
function remaining(){return Math.max(0,FREE_SEC-freeUsed())+bal();}
function fmt(sec){sec=Math.max(0,Math.round(sec));var m=Math.floor(sec/60),s=sec%60;return m+':'+(s<10?'0':'')+s;}

window.A={
 rnd:function(a,b){return Math.floor(Math.random()*(b-a+1))+a;},
 pick:function(a){return a[Math.floor(Math.random()*a.length)];},
 shuffle:function(a){a=a.slice();for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t2=a[i];a[i]=a[j];a[j]=t2;}return a;},
 el:function(id){return d.getElementById(id);},
 say:function(h){var o=d.getElementById('o');if(o)o.innerHTML=h;},
 opts:function(q,sp){var set=[q],guard=0;while(set.length<4&&guard<300){guard++;var v=q+A.rnd(1,Math.max(1,sp))*(Math.random()<.5?-1:1);if(set.indexOf(v)<0&&v>=0)set.push(v);}var k=1;while(set.length<4){var w=q+k;if(set.indexOf(w)<0)set.push(w);k++;}set=A.shuffle(set);return set.map(function(v){return '<button data-v="'+v+'" onclick="AG.ans('+v+')">'+v+'</button>';}).join('');},
 on:function(sel,fn){var o=d.getElementById('o');if(o)o.addEventListener('click',function(e){var t2=e.target.closest(sel);if(t2)fn(t2);});}
};
var ticking=false,timer=null,paywalled=false;
function hud(){var c=d.getElementById('clock');if(!c)return;var rem=remaining();
 var freeLeft=Math.max(0,FREE_SEC-freeUsed());
 c.textContent=fmt(rem)+(freeLeft>0?' ('+t('free')+')':'');
 c.style.color=rem<=60?'#dc2626':(rem<=180?'#b45309':'#166534');}
function gate(){var g=d.getElementById('gate');var on=remaining()<=0;if(g)g.style.display=on?'block':'none';paywalled=on;}
function tick(){if(d.hidden)return;var rem=remaining();if(rem<=0){gate();if(timer){clearInterval(timer);timer=null;ticking=false;}return;}
 var fu=freeUsed();if(fu<FREE_SEC){setnum('af_'+slug(),fu+1);}else{setnum('bal',bal()-1);}
 hud();}
function start(){if(ticking)return;ticking=true;if(timer)clearInterval(timer);timer=setInterval(tick,1000);hud();
 setTimeout(function(){beacon();},1500);}
function stop(){ticking=false;if(timer){clearInterval(timer);timer=null;}}
function beacon(){try{var u='/api/arcade?a=tick&slug='+encodeURIComponent(slug())+'&ref='+encodeURIComponent(me())+'&used='+freeUsed()+'&bal='+bal();fetch(u,{method:'GET'}).then(function(r){return r.json();}).then(function(j){
 if(j&&j.ok){if(typeof j.bonusSeconds==='number'&&j.bonusSeconds>0){var k='bonus_'+me();if(num(k)<j.bonusSeconds){var add=j.bonusSeconds-num(k);setnum('bal',bal()+add);setnum(k,j.bonusSeconds);hud();}}
 if(typeof j.balanceSeconds==='number'&&j.balanceSeconds>bal()){setnum('bal',j.balanceSeconds);hud();}}
}).catch(function(){});}catch(e){}}

function modal(html){var m=d.getElementById('modal');if(!m)return;var b=d.getElementById('modal-body');if(!b){b=d.createElement('div');b.id='modal-body';m.appendChild(b);}b.innerHTML=html;m.style.display='block';}
function hideModal(){var m=d.getElementById('modal');if(m)m.style.display='none';}
function payHTML(){var h='<div class="mw"><div class="mh">'+t('over')+'</div><div class="mnote">'+t('rate')+' · '+t('invite')+'</div><div class="plans">';
 PACKS.forEach(function(p){h+='<div class="pc" onclick="AR.buy(&quot;'+p[0]+'&quot;)"><div>'+p[1]+' '+t('minutes')+'</div><div class="price">¥'+p[2]+'</div></div>';});
 h+='</div><div class="rrow">'+t('invite2')+':<br><input id="aref" readonly value="'+location.origin+'/arcade/'+slug()+'/?ref='+me()+'"></div>';
 h+='<div class="mnote">'+t('demo')+'</div><button class="mlink" onclick="AR.hide()">'+t('close')+'</button></div>';return h;}
function showModal(){gate();if(!paywalled)return;modal(payHTML());}

window.AR={start:start,stop:stop,hud:hud,open:showModal,hide:hideModal,
 remaining:remaining,free:freeUsed,bal:bal,me:me,slug:slug,
 buy:function(plan){try{var fd=PACKS.filter(function(p){return p[0]===plan;})[0];LS('pending_'+slug(),JSON.stringify({plan:plan,out:'ARC_'+me()+'_'+plan+'_'+Date.now(),min:fd?fd[1]:0,ts:Date.now()}));}catch(e){}
   location.href='/api/pay?plan='+encodeURIComponent(plan)+'&slug='+encodeURIComponent(slug())+'&ref='+encodeURIComponent(me())+'&arcade=1';},
 credit:function(sec){setnum('bal',bal()+Math.round(sec));hud();try{if(paywalled){hideModal();start();}}catch(e){}},
 use:function(){start();}};

// referral: ?ref=XXX -> both sides +10 minutes
function referral(){var u=new URLSearchParams((location.search||'').slice(1));var inv=u.get('ref');if(!inv)return;var my=me();if(inv===my)return;
 var key='joined_'+inv;if(LS(key)==='1')return;LS(key,'1');LS('invited_by',inv);
 setnum('bal',bal()+FREE_SEC);hud();
 try{var f=num('friends_'+inv)+1;setnum('friends_'+inv,f);}catch(e){}
 try{fetch('/api/arcade?a=invite&ref='+encodeURIComponent(inv)+'&by='+encodeURIComponent(my)+'&slug='+encodeURIComponent(slug()),{method:'GET'}).then(function(r){return r.json();}).then(function(){});}catch(e){}
 var el=d.getElementById('ainvited');if(el)el.textContent=t('got');}

function ready(){
 lang=cur();referral();hud();gate();
 document.addEventListener('visibilitychange',function(){if(d.hidden){stop();}else if(!paywalled&&freeUsed()>0){start();}});
 window.addEventListener('beforeunload',function(){try{beacon();}catch(e){}});
 setTimeout(function(){try{beacon();}catch(e){}},600);
}
if(d.readyState==='loading'){d.addEventListener('DOMContentLoaded',ready);}else{ready();}
})();
