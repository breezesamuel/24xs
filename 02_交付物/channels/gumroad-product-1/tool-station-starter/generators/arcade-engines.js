// bingdashan AI arcade - engine library
// each engine: {id,cat,t,p,pain,units,lvs,skins,mk(u,l,s)->js}
// js defines function go(){...}; helpers via window.A ; state on window.AG
const T=require('./arcade-topics.js');
const THEMES=[
 {k:'kids',zh:'儿童版',en:'Kids',ar:'أطفال'},
 {k:'student',zh:'学生版',en:'Student',ar:'طلاب'},
 {k:'office',zh:'办公版',en:'Office',ar:'مكتب'},
 {k:'dev',zh:'程序员版',en:'Developer',ar:'مبرمج'},
 {k:'senior',zh:'长辈版',en:'Senior',ar:'كبار'},
 {k:'travel',zh:'旅行版',en:'Travel',ar:'سفر'},
 {k:'food',zh:'美食版',en:'Foodie',ar:'طعام'},
 {k:'fit',zh:'健身版',en:'Fitness',ar:'لياقة'},
 {k:'money',zh:'理财版',en:'Finance',ar:'مال'},
 {k:'fun',zh:'休闲版',en:'Casual',ar:'ترفيه'}
];
const LV=[{zh:'入门',en:'Easy',ar:'سهل'},{zh:'进阶',en:'Medium',ar:'متوسط'},{zh:'高手',en:'Hard',ar:'صعب'},{zh:'大师',en:'Expert',ar:'خبير'}];
function slice(arr,n){const out=[];for(let i=0;i<arr.length;i+=n)out.push(arr.slice(i,i+n));return out;}
const PACKS=(arr,size)=>{const p=slice(arr,size);const names=['A','B','C','D','E','F','G','H','I','J','K','L','M','N'];return p.map((rows,i)=>({rows,zh:names[i],en:names[i],ar:names[i]}));};

const E=[];
const add=(e)=>E.push(e);

// ---------- 算术 ----------
add({id:'math',cat:'算术',t:{zh:'口算练习',en:'Mental Math',ar:'حساب ذهني'},
 p:{zh:'需要练口算的人',en:'Anyone practicing math',ar:'من يتدرب على الحساب'},
 pain:{zh:'口算慢、易出错',en:'Slow and error-prone math',ar:'حساب بطيء وخاطئ'},
 units:[{zh:'加法',en:'Addition',ar:'جمع'},{zh:'减法',en:'Subtraction',ar:'طرح'},{zh:'乘法',en:'Multiplication',ar:'ضرب'},{zh:'除法',en:'Division',ar:'قسمة'}],
 lvs:3,skins:4,
 mk:(u,l,s)=>`function go(){var op=['+','-','×','÷'][${u}];var lv=${l+1};var sc=0,rd=0,cur=null;
function nq(){var a,b,r;if(op==='+'){a=A.rnd(2,9+lv*9);b=A.rnd(2,9+lv*9);r=a+b;}else if(op==='-'){a=A.rnd(5,9+lv*9);b=A.rnd(1,a);r=a-b;}else if(op==='×'){a=A.rnd(2,4+lv*4);b=A.rnd(2,4+lv*4);r=a*b;}else{b=A.rnd(2,4+lv*4);r=A.rnd(2,4+lv*4);a=b*r;}cur={s:a+' '+op+' '+b,q:r};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+' / '+rd+'</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.s+' = ?</div>'+A.opts(cur.q,3+lv));}
draw();}`});

add({id:'fastmath',cat:'算术',t:{zh:'限时心算',en:'Timed Math Sprint',ar:'حساب سريع'},
 p:{zh:'想提升计算速度的人',en:'Speed trainers',ar:'مدربو السرعة'},
 pain:{zh:'算得慢、注意力散',en:'Slow and distracted',ar:'بطء وتشتت'},
 units:[{zh:'加',en:'Add',ar:'جمع'},{zh:'减',en:'Sub',ar:'طرح'},{zh:'乘',en:'Mul',ar:'ضرب'},{zh:'混合',en:'Mixed',ar:'مختلط'}],
 lvs:3,skins:4,
 mk:(u,l,s)=>`function go(){var mode=${u};var lv=${l+1};var sc=0,left=30+lv*10,cur=null,timer=null;
function nq(){var a,b,r,op;var m=mode===3?A.rnd(0,2):mode;op=['+','-','×'][m];
if(m===0){a=A.rnd(2,20+lv*20);b=A.rnd(2,20+lv*20);r=a+b;}
else if(m===1){a=A.rnd(10,30+lv*20);b=A.rnd(1,a);r=a-b;}
else{a=A.rnd(2,6+lv*5);b=A.rnd(2,6+lv*5);r=a*b;}cur={s:a+' '+op+' '+b,q:r};}
window.AG={ans:function(v){if(v===cur.q)sc++;nq();draw();}};
function draw(){A.say('<div style="display:flex;justify-content:space-between;font-size:.9rem"><b>得分 '+sc+'</b><b>剩余 '+left+'s</b></div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.s+' = ?</div>'+A.opts(cur.q,4+lv));}
nq();draw();timer=setInterval(function(){left--;if(left<=0){clearInterval(timer);A.say('<div style="font-size:1.4rem">时间到! 得分 '+sc+'</div><button onclick="AG.again()">再来一局</button>');return;}var e=A.el('o').querySelector('b:last-child');if(e)e.textContent='剩余 '+left+'s';},1000);
window.AG.again=function(){sc=0;left=30+lv*10;nq();draw();};}`});

add({id:'pct',cat:'算术',t:{zh:'百分比计算',en:'Percentages',ar:'نسبة مئوية'},
 p:{zh:'购物比价、算折扣的人',en:'Shoppers and savers',ar:'المتسوقون'},
 pain:{zh:'打折算不清',en:'Discount math confusion',ar:'ارتباك الخصومات'},
 units:[{zh:'折扣价',en:'Sale price',ar:'سعر الخصم'},{zh:'涨幅',en:'Increase',ar:'زيادة'},{zh:'占比',en:'Share',ar:'نسبة'},{zh:'小费',en:'Tip',ar:'بقشيش'}],
 lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var sc=0,rd=0,cur=null;
function nq(){if(t===0){var p=A.rnd(2,9)*10,d=[10,15,20,25,30,40,50][A.rnd(0,6)];cur={s:'原价 ¥'+p+' 打 '+d+'% 折,现价?',q:Math.round(p*(100-d)/100)};}
else if(t===1){var base=A.rnd(2,9)*10,up=[5,10,15,20,25,50][A.rnd(0,5)];cur={s:base+' 涨 '+up+'% 后?',q:Math.round(base*(100+up)/100)};}
else if(t===2){var tot=A.rnd(2,9)*10,pt=A.rnd(1,4)*10;cur={s:tot+' 的 '+pt+'% 是多少?',q:Math.round(tot*pt/100)};}
else{var bill=A.rnd(5,40)*10,tp=[10,15,18,20][A.rnd(0,3)];cur={s:'账单 ¥'+bill+' 给 '+tp+'% 小费,总付?',q:Math.round(bill*(100+tp)/100)};}}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+' / '+rd+'</div><div style="font-size:1.3rem;margin:14px 0">'+cur.s+'</div>'+A.opts(cur.q,Math.max(2,Math.round(cur.q*0.15)+1+lv)));}
draw();}`});

// ---------- 语言 ----------
const WPK=PACKS(T.WORDS,20);
add({id:'word2en',cat:'语言',t:{zh:'看图识字·中英',en:'Chinese to English',ar:'صيني إلى إنجليزي'},
 p:{zh:'背单词的学生',en:'Vocabulary learners',ar:'متعلمو المفردات'},
 pain:{zh:'单词记不住',en:'Words keep slipping',ar:'نسيان الكلمات'},
 units:WPK.map(x=>({zh:'第'+x.zh+'组',en:'Set '+x.en,ar:'مجموعة '+x.ar})),lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var Q=${JSON.stringify(WPK[u].rows)};var lv=${l+1};var i=0,sc=0,cur=null;
function nq(){var row=Q[i%Q.length];var wrong=A.shuffle(Q.filter(function(r){return r[1]!==row[1];})).slice(0,3).map(function(r){return r[1];});cur={a:row[0],q:row[1],o:A.shuffle([row[1]].concat(wrong))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});
add({id:'en2word',cat:'语言',t:{zh:'看词猜义·英译中',en:'English to Chinese',ar:'إنجليزي إلى صيني'},
 p:{zh:'英语阅读者',en:'English readers',ar:'قراء الإنجليزية'},
 pain:{zh:'认得字母不懂意思',en:'Recognize but not understand',ar:'تعرف الشكل لا المعنى'},
 units:WPK.map(x=>({zh:'第'+x.zh+'组',en:'Set '+x.en,ar:'مجموعة '+x.ar})),lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var Q=${JSON.stringify(WPK[u].rows)};var i=0,sc=0,cur=null;
function nq(){var row=Q[i%Q.length];var wrong=A.shuffle(Q.filter(function(r){return r[0]!==row[0];})).slice(0,3).map(function(r){return r[0];});cur={a:row[1],q:row[0],o:A.shuffle([row[0]].concat(wrong))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});

const IPK=PACKS(T.IDIOMS,16);
add({id:'idiom',cat:'语言',t:{zh:'成语填空',en:'Idiom Fill-in',ar:'أكمل المثل'},
 p:{zh:'想提升中文表达的人',en:'Chinese learners',ar:'متعلمو الصينية'},
 pain:{zh:'成语只会一半',en:'Only half the idiom',ar:'نصف المثل فقط'},
 units:IPK.map(x=>({zh:'第'+x.zh+'组',en:'Set '+x.en,ar:'مجموعة '+x.ar})),lvs:2,skins:1,
 mk:(u,l,s)=>`function go(){var Q=${JSON.stringify(IPK[u].rows)};var i=0,sc=0,cur=null;
function nq(){var w=Q[i%Q.length];var p=A.rnd(0,w.length-1);var ans=w[p];var masked=w.slice(0,p)+'〇'+w.slice(p+1);
var pool='天地人心山川日月水火风云金木玉石花草鸟鱼马牛羊龙虎';var wrong=[];while(wrong.length<3){var c=pool[A.rnd(0,pool.length-1)];if(c!==ans&&wrong.indexOf(c)<0)wrong.push(c);}cur={m:masked,q:ans,o:A.shuffle([ans].concat(wrong))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:2rem;letter-spacing:8px;margin:14px 0;font-weight:700">'+cur.m+'</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});
add({id:'proverb',cat:'语言',t:{zh:'谚语接龙',en:'Proverb Match',ar:'مطابقة الحكم'},
 p:{zh:'喜欢俗语的人',en:'Idiom fans',ar:'محبو الحكم'},
 pain:{zh:'只会上半句',en:'Only know half',ar:'تعرف النصف'},
 units:[{zh:'A组',en:'Set A',ar:'مجموعة أ'},{zh:'B组',en:'Set B',ar:'مجموعة ب'},{zh:'C组',en:'Set C',ar:'مجموعة ج'}],lvs:1,skins:1,
 mk:(u,l,s)=>{const rows=T.PROVERBS.slice(u*10,u*10+10);return `function go(){var Q=${JSON.stringify(rows.map(r=>[r[0],r[1]]))};var i=0,sc=0,cur=null;
function nq(){var row=Q[i%Q.length];var wrong=A.shuffle(Q.filter(function(r){return r[1]!==row[1];})).slice(0,3).map(function(r){return r[1];});cur={a:row[0],q:row[1],o:A.shuffle([row[1]].concat(wrong))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:1.5rem;margin:14px 0;font-weight:700">'+cur.a+' , ____</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`;}});

const CPK=PACKS(T.CAPITALS,16);
add({id:'capita',cat:'知识',t:{zh:'国家与首都',en:'Country & Capital',ar:'دولة وعاصمة'},
 p:{zh:'地理爱好者、备考学生',en:'Geography fans',ar:'محبو الجغرافيا'},
 pain:{zh:'首都是哪个记混',en:'Mixing up capitals',ar:'خلط العواصم'},
 units:CPK.map(x=>({zh:'第'+x.zh+'组',en:'Set '+x.en,ar:'مجموعة '+x.ar})),lvs:2,skins:1,
 mk:(u,l,s)=>`function go(){var Q=${JSON.stringify(CPK[u].rows.map(r=>[r[0],r[1]]))};var i=0,sc=0,cur=null;
function nq(){var row=Q[i%Q.length];var wrong=A.shuffle(Q.filter(function(r){return r[1]!==row[1];})).slice(0,3).map(function(r){return r[1];});cur={a:row[0],q:row[1],o:A.shuffle([row[1]].concat(wrong))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.a+' 的首都?</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});

const ELPK=PACKS(T.ELEMENTS,15);
add({id:'elem',cat:'知识',t:{zh:'元素符号',en:'Element Symbols',ar:'رموز العناصر'},
 p:{zh:'化学学生',en:'Chemistry students',ar:'طلاب الكيمياء'},
 pain:{zh:'符号和中文对不上',en:'Symbols vs names',ar:'الرموز والأسماء'},
 units:ELPK.map(x=>({zh:'第'+x.zh+'组',en:'Set '+x.en,ar:'مجموعة '+x.ar})),lvs:2,skins:1,
 mk:(u,l,s)=>`function go(){var Q=${JSON.stringify(ELPK[u].rows.map(r=>[r[0],r[1]]))};var i=0,sc=0,cur=null;
function nq(){var row=Q[i%Q.length];var wrong=A.shuffle(Q.filter(function(r){return r[1]!==row[1];})).slice(0,3).map(function(r){return r[1];});cur={a:row[0],q:row[1],o:A.shuffle([row[1]].concat(wrong))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.a+' = ?</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});

const RPK=PACKS(T.RIDDLES,10);
add({id:'riddle',cat:'休闲',t:{zh:'脑筋急转弯',en:'Brain Teasers',ar:'ألغاز ذهنية'},
 p:{zh:'喜欢猜谜的人',en:'Riddle lovers',ar:'محبو الألغاز'},
 pain:{zh:'脑子转不动',en:'Brain freeze',ar:'تجمّد الفكر'},
 units:RPK.map(x=>({zh:'第'+x.zh+'组',en:'Set '+x.en,ar:'مجموعة '+x.ar})),lvs:1,skins:1,
 mk:(u,l,s)=>`function go(){var Q=${JSON.stringify(RPK[u].rows.map(r=>[r[0],r[1]]))};var i=0,cur=null,seen=false;
function nq(){cur=Q[i%Q.length];seen=false;}
window.AG={go:function(){if(seen)i++;seen=true;draw();}};
function draw(){if(!seen){A.say('<div style="font-size:.9rem;color:#555">第 '+(i+1)+' 题</div><div style="font-size:1.4rem;margin:14px 0">'+cur[0]+'</div><button onclick="AG.go()">看答案</button>');}
else{A.say('<div style="font-size:1.2rem;margin:14px 0">'+cur[0]+'</div><div style="font-size:1.6rem;font-weight:700">答案:'+cur[1]+'</div><button onclick="AG.go()">下一题</button>');}}
nq();draw();}`});

const TPK=PACKS(T.TRIVIA,10);
add({id:'trivia',cat:'知识',t:{zh:'常识问答',en:'Trivia Quiz',ar:'معلومات عامة'},
 p:{zh:'爱答题的人',en:'Quiz fans',ar:'محبو المسابقات'},
 pain:{zh:'知识碎片化',en:'Scattered knowledge',ar:'معرفة مبعثرة'},
 units:TPK.map(x=>({zh:'第'+x.zh+'组',en:'Set '+x.en,ar:'مجموعة '+x.ar})),lvs:2,skins:1,
 mk:(u,l,s)=>`function go(){var Q=${JSON.stringify(TPK[u].rows.map(r=>[r[0],r[1],r[2]]))};var i=0,sc=0,cur=null;
function nq(){var row=Q[i%Q.length];cur={a:row[0],q:row[1],o:A.shuffle([row[1]].concat(row[2].slice(0,3)))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:1.3rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});

add({id:'quote',cat:'知识',t:{zh:'名句作者',en:'Who Said It',ar:'من قالها'},
 p:{zh:'文学爱好者',en:'Literature fans',ar:'محبو الأدب'},
 pain:{zh:'记得句子忘了作者',en:'Quote without author',ar:'النص بلا قائل'},
 units:[{zh:'A组',en:'Set A',ar:'أ'},{zh:'B组',en:'Set B',ar:'ب'},{zh:'C组',en:'Set C',ar:'ج'}],lvs:1,skins:1,
 mk:(u,l,s)=>{const rows=T.QUOTES.slice(u*10,u*10+10);return `function go(){var Q=${JSON.stringify(rows)};var i=0,sc=0,cur=null;
function nq(){var row=Q[i%Q.length];var wrong=A.shuffle(Q.filter(function(r){return r[1]!==row[1];})).slice(0,3).map(function(r){return r[1];});cur={a:row[0],q:row[1],o:A.shuffle([row[1]].concat(wrong))};}
window.AG={ans:function(v){if(v===cur.q)sc++;i++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">答对 '+sc+' / 第 '+(i+1)+' 题</div><div style="font-size:1.2rem;margin:14px 0;font-weight:700">「'+cur.a+'」 出自?</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`;}});

// ---------- 反应 ----------
add({id:'react',cat:'反应',t:{zh:'反应速度测试',en:'Reaction Test',ar:'اختبار سرعة الاستجابة'},
 p:{zh:'想测反应力的人',en:'Anyone testing reflexes',ar:'اختبار ردود الفعل'},
 pain:{zh:'反应慢半拍',en:'Half a beat slow',ar:'بطء في الرد'},
 units:[{zh:'纯色',en:'Solid',ar:'لون'},{zh:'变词',en:'Word',ar:'كلمة'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var best=0,tries=0,t0=0,armed=false,timer=null;
function draw(){A.say('<div style="font-size:.9rem;color:#555">最佳 '+best+'ms · 已测 '+tries+' 次</div><div id="pad" style="margin:16px 0;height:180px;border-radius:14px;background:#e5e7eb;display:flex;align-items:center;justify-content:center;font-size:1.2rem;cursor:pointer">点击开始</div>');}
window.AG={tap:function(){var p=A.el('pad');
if(!armed){p.textContent='等待变绿…';p.style.background='#e5e7eb';armed=true;t0=Date.now()+A.rnd(800,2500-lv*200);
timer=setTimeout(function(){p.style.background='#22c55e';p.textContent='点!';armed=false;t0=Date.now();},t0-Date.now());return;}
var dt=Date.now()-t0;tries++;if(!best||dt<best)best=dt;p.style.background='#e5e7eb';p.textContent=dt+'ms · 继续';}};
A.say=function(h){A.el('o').innerHTML=h;var p=A.el('pad');if(p)p.onclick=function(){AG.tap();};};
draw();}`});

add({id:'gng',cat:'反应',t:{zh:'红绿灯',en:'Go / No-Go',ar:'أخضر أم أحمر'},
 p:{zh:'想练专注力的人',en:'Focus trainers',ar:'مدربو التركيز'},
 pain:{zh:'容易手滑、冲动',en:'Impulsive mistakes',ar:'أخطاء الاندفاع'},
 units:[{zh:'颜色',en:'Color',ar:'لون'},{zh:'文字',en:'Text',ar:'نص'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var sc=0,miss=0,i=0,cur=null,lock=false;
function nq(){cur=Math.random()<0.6?'go':'stop';i++;}
window.AG={tap:function(){if(lock)return;lock=true;var ok=(cur==='go');if(ok)sc++;else miss++;setTimeout(function(){lock=false;nq();draw();},350);}};
function draw(){if(!cur)nq();A.say('<div style="display:flex;justify-content:space-between;font-size:.9rem"><b>正确 '+sc+'</b><b>失误 '+miss+'</b></div><div style="margin:18px 0;padding:36px;border-radius:14px;text-align:center;font-size:1.8rem;font-weight:700;background:'+(cur==='go'?'#dcfce7;color:#166534':'#fee2e2;color:#991b1b')+'">'+(cur==='go'?'GO 点我':'STOP 别点')+'</div><button onclick="AG.tap()">点</button><div style="font-size:.85rem;color:#666;margin-top:8px">看到 GO 才点,STOP 点了算失误</div>');}
draw();}`});

add({id:'taptarget',cat:'反应',t:{zh:'快速点靶',en:'Tap Targets',ar:'انقر الأهداف'},
 p:{zh:'练手速的人',en:'Hand-speed trainers',ar:'مدربو السرعة'},
 pain:{zh:'鼠标点不准',en:'Inaccurate clicking',ar:'نقر غير دقيق'},
 units:[{zh:'圆形',en:'Circle',ar:'دائرة'},{zh:'方形',en:'Square',ar:'مربع'},{zh:'混合',en:'Mixed',ar:'مختلط'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var sc=0,miss=0,target=null,t0=Date.now();
function nq(){target={x:A.rnd(5,90),y:A.rnd(5,80)};}
window.AG={hit:function(e){if(e)e.stopPropagation();sc++;tryGrow();nq();draw();},miss:function(){miss++;draw();}};
function tryGrow(){}
function draw(){if(!target)nq();A.say('<div style="display:flex;justify-content:space-between;font-size:.9rem"><b>命中 '+sc+'</b><b>失误 '+miss+'</b></div><div onclick="AG.miss()" style="position:relative;height:260px;margin:12px 0;background:#f3f4f6;border-radius:12px;overflow:hidden"><div onclick="AG.hit(event)" style="position:absolute;left:'+target.x+'%;top:'+target.y+'%;width:'+(56-lv*8)+'px;height:'+(56-lv*8)+'px;border-radius:'+((${u}===1)?'8px':'50%')+';background:#111;cursor:pointer"></div></div>');}
draw();}`});

add({id:'speed_sort',cat:'反应',t:{zh:'快慢分类',en:'Fast Sort',ar:'فرز سريع'},
 p:{zh:'需要快速判断的人',en:'Fast decision makers',ar:'أصحاب القرار السريع'},
 pain:{zh:'判断犹豫',en:'Hesitation',ar:'تردد'},
 units:[{zh:'大小',en:'Big/Small',ar:'كبير/صغير'},{zh:'奇偶',en:'Odd/Even',ar:'فردي/زوجي'},{zh:'正负',en:'Sign',ar:'إشارة'},{zh:'颜色',en:'Color',ar:'لون'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var sc=0,rd=0,cur=null;
function nq(){var n=A.rnd(1,99+lv*50);if(t===0){cur={v:n,q:n>50?'大':'小',help:'大于50选大,否则选小'};}
else if(t===1){cur={v:n,q:n%2?'奇':'偶',help:'奇数还是偶数'};}
else if(t===2){cur={v:A.rnd(-99,99),q:'',help:'正数还是负数'};cur.q=cur.v>=0?'正':'负';}
else{var c=[['红','#ef4444'],['绿','#22c55e'],['蓝','#3b82f6'],['黄','#eab308']];var pick=c[A.rnd(0,3)];cur={v:'',q:pick[0],help:'这是什么颜色',color:pick[1],opts:c.map(function(x){return x[0];})};}}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();var opts=(t===3)?cur.opts:(t===0?['大','小']:t===1?['奇','偶']:['正','负']);
A.say('<div style="font-size:.9rem;color:#555">'+cur.help+' · 得分 '+sc+'/'+rd+'</div><div style="font-size:3rem;font-weight:700;margin:14px 0'+(cur.color?';color:'+cur.color:'')+'">'+(cur.v===''?'■':cur.v)+'</div>'+opts.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});

// ---------- 记忆 ----------
add({id:'memseq',cat:'记忆',t:{zh:'记忆序列',en:'Sequence Memory',ar:'ذاكرة التسلسل'},
 p:{zh:'想练短期记忆的人',en:'Working-memory trainers',ar:'تدريب الذاكرة'},
 pain:{zh:'记不住刚才的事',en:'Forgetting just now',ar:'نسيان اللحظة'},
 units:[{zh:'数字',en:'Digits',ar:'أرقام'},{zh:'颜色',en:'Colors',ar:'ألوان'}],lvs:4,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var seq=[],input=[],showing=false,best=0,t0=0,len=0;
var COL=['#ef4444','#3b82f6','#22c55e','#eab308','#a855f7','#ec4899','#14b8a6','#f97316'];
function nq(){len=2+lv;seq=[];for(var i=0;i<len;i++)seq.push(${u}===0?A.rnd(1,9):A.rnd(0,COL.length-1));input=[];show();}
function show(){showing=true;var i=0;var str=seq.map(function(x){return ${u}===0?x:'<span style="display:inline-block;width:26px;height:26px;border-radius:6px;background:'+COL[x]+';margin:2px"></span>';}).join(' ');
A.say('<div style="font-size:.9rem;color:#555">记住顺序,最长为 '+best+'</div><div style="font-size:2rem;margin:16px 0" id="seqbox">'+str+'</div><div id="pad"></div>');
var box=A.el('seqbox');box.style.transition='opacity .3s';
setTimeout(function(){box.style.opacity='0';setTimeout(function(){showing=false;draw();},400);},Math.max(800,len*420-lv*40));}
function draw(){A.say('<div style="font-size:.9rem;color:#555">按顺序点击 · 最长 '+best+'</div><div style="margin:12px 0">'+input.join(' ')+'</div>'+(${u}===0?'<button onclick="AG.d(1)">1</button><button onclick="AG.d(2)">2</button><button onclick="AG.d(3)">3</button><button onclick="AG.d(4)">4</button><button onclick="AG.d(5)">5</button><button onclick="AG.d(6)">6</button><button onclick="AG.d(7)">7</button><button onclick="AG.d(8)">8</button><button onclick="AG.d(9)">9</button>':COL.map(function(c,i){return '<button style="background:'+c+'" onclick="AG.d('+i+')">&nbsp;</button>';}).join('')));}
window.AG={d:function(v){input.push(v);var i=input.length;if(input[i-1]!==seq[i-1]){if(seq.length-1>best)best=seq.length-1;A.say('<div style="font-size:1.3rem">错了!长度 '+seq.length+' · 最佳 '+best+'</div><button onclick="AG.next()">再来</button>');return;}if(i===seq.length){if(seq.length>best)best=seq.length;nq();return;}draw();},next:function(){lv=Math.max(1,lv);nq();}};
nq();}`});

add({id:'memcard',cat:'记忆',t:{zh:'记忆翻牌',en:'Memory Match',ar:'مطابقة البطاقات'},
 p:{zh:'喜欢配对游戏的人',en:'Matching-game fans',ar:'محبو المطابقة'},
 pain:{zh:'记性差',en:'Poor memory',ar:'ذاكرة ضعيفة'},
 units:[{zh:'表情',en:'Emoji',ar:'رموز'},{zh:'字母',en:'Letters',ar:'حروف'},{zh:'数字',en:'Numbers',ar:'أرقام'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var pairs=4+lv*2;var pool=['🍎','🍌','🍇','🚀','🐱','🐶','🎈','⭐','🌙','🍀','🐟','🎵','🚗','🌻','🍕','🐼','⚽','🎲','🔑','💎'];
var syms=A.shuffle(pool).slice(0,pairs);var deck=A.shuffle(syms.concat(syms).map(function(x,i){return {x:x,i:i};}));
if(${u}===1)syms=A.shuffle('ABCDEFGHJKLMNPQRSTUVWXYZ'.split('')).slice(0,pairs),deck=A.shuffle(syms.concat(syms).map(function(x,i){return {x:x,i:i};}));
if(${u}===2){syms=[];while(syms.length<pairs){var n=A.rnd(10,99);if(syms.indexOf(n)<0)syms.push(n);}deck=A.shuffle(syms.concat(syms).map(function(x,i){return {x:'&#8203;'+x,i:i};}));}
var open=[],done=[],moves=0,lock=false;
window.AG={flip:function(i){if(lock||done.indexOf(i)>=0||open.indexOf(i)>=0)return;open.push(i);draw();
if(open.length===2){moves++;lock=true;var a=open[0],b=open[1];setTimeout(function(){if(deck[a].x===deck[b].x){done.push(a);done.push(b);}open=[];lock=false;draw();},600);}}};
function draw(){var html='<div style="font-size:.9rem;color:#555">翻牌 '+moves+' 次 · 完成 '+done.length/2+'/'+pairs+'</div><div style="display:grid;grid-template-columns:repeat('+Math.min(pairs,6)+',1fr);gap:8px;margin:14px 0">';
deck.forEach(function(c,i){var shown=open.indexOf(i)>=0||done.indexOf(i)>=0;html+='<div onclick="AG.flip('+i+')" style="height:56px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;cursor:pointer;background:'+(shown?'#fff;border:1px solid #d1d5db':'#111;color:#fff')+';user-select:none">'+(shown?c.x:'?')+'</div>';});
html+='</div>';if(done.length===deck.length)html+='<div style="font-size:1.3rem;font-weight:700">全部配对!用了 '+moves+' 次</div>';
A.say(html);}
draw();}`});

add({id:'nback',cat:'记忆',t:{zh:'N-back 记忆',en:'N-Back Memory',ar:'ذاكرة N-back'},
 p:{zh:'想提升专注与记忆',en:'Memory & focus',ar:'ذاكرة وتركيز'},
 pain:{zh:'专注力不足',en:'Poor focus',ar:'ضعف التركيز'},
 units:[{zh:'1-back',en:'1-back',ar:'1-back'},{zh:'2-back',en:'2-back',ar:'2-back'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var N=${u+1};var lv=${l+1};var seq=[],i=0,sc=0,rd=0,shown='——';
var COL=['#ef4444','#3b82f6','#22c55e','#eab308','#a855f7'];
function step(){var n=A.rnd(1,26);if(i>=N&&Math.random()<0.35)n=seq[i-N];seq.push(n);i++;shown=n;draw();}
window.AG={yes:function(){var ok=(i-1>=N)&&seq[i-1]===seq[i-1-N];if(ok)sc++;rd++;step();},no:function(){var ok=!(i-1>=N&&seq[i-1]===seq[i-1-N]);if(ok)sc++;rd++;step();}};
function draw(){A.say('<div style="font-size:.9rem;color:#555">'+N+'-back · 答对 '+sc+'/'+rd+'</div><div style="font-size:3rem;font-weight:700;margin:14px 0">'+shown+'</div><button onclick="AG.yes()">与 '+N+' 步前相同</button><button onclick="AG.no()">不同</button><div style="font-size:.85rem;color:#666;margin-top:8px">当前字母是否与 '+N+' 步前相同?</div>');}
step();}`});

add({id:'digitspan',cat:'记忆',t:{zh:'数字广度',en:'Digit Span',ar:'مدى الأرقام'},
 p:{zh:'测记忆容量的人',en:'Memory capacity',ar:'قدرة الذاكرة'},
 pain:{zh:'一长串数字就懵',en:'Lost in long numbers',ar:'ضياع في الأرقام'},
 units:[{zh:'正序',en:'Forward',ar:'أمامي'},{zh:'倒序',en:'Reverse',ar:'عكسي'}],lvs:4,skins:2,
 mk:(u,l,s)=>`function go(){var rev=${u===1?1:0};var len=3+${l};var best=0;
function round(){var n=len;var num='';for(var i=0;i<n;i++)num+=A.rnd(0,9);window.AG.saved=num;
A.say('<div style="font-size:.9rem;color:#555">最长记住 '+best+' 位</div><div style="font-size:2.4rem;letter-spacing:6px;margin:16px 0">'+num+'</div><div id="lg"></div>');
setTimeout(function(){A.say('<div style="font-size:.9rem;color:#555">'+(rev?'倒序':'正序')+'输入刚才的数字</div><input id="ans" inputmode="numeric" style="font-size:1.6rem;letter-spacing:4px"><br><button onclick="AG.chk()">提交</button>');},1200+n*250);}
window.AG={chk:function(){var v=(A.el('ans').value||'').replace(/\D/g,'');var want=rev?AG.saved.split('').reverse().join(''):AG.saved;
if(v===want){best=Math.max(best,want.length);len++;A.say('<div style="font-size:1.3rem;color:#166534">正确!升级到 '+len+' 位</div><button onclick="AG.next()">继续</button>');}
else{A.say('<div style="font-size:1.3rem;color:#991b1b">错了,答案是 '+want+' · 最佳 '+best+' 位</div><button onclick="AG.next()">重来</button>');len=3+${l};}},next:function(){round();}};
round();}`});

// ---------- 益智 ----------
add({id:'oddball',cat:'益智',t:{zh:'找出不同',en:'Odd One Out',ar:'اكتشف المختلف'},
 p:{zh:'想练眼力的人',en:'Sharp-eye training',ar:'تدريب النظر'},
 pain:{zh:'细节看不出来',en:'Missing details',ar:'تفويت التفاصيل'},
 units:[{zh:'表情',en:'Emoji',ar:'رموز'},{zh:'数字',en:'Numbers',ar:'أرقام'},{zh:'字母',en:'Letters',ar:'حروف'},{zh:'形状',en:'Shapes',ar:'أشكال'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var n=3+lv*2;var sc=0,rd=0;
function draw(){var rows=[],cols=[],base;
if(${u}===0){var p=['🍎','🐱','🚀','⭐','🎈','🐶','🍀','🌙'];base=A.pick(p);var o=A.pick(p.filter(function(x){return x!==base;}));}
else if(${u}===1){base='6';var o='9';}
else if(${u}===2){base='O';var o='Q';}
else{base='●';var o='⬤';}
var pos=A.rnd(0,n*n-1);var html='<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div><div style="display:grid;grid-template-columns:repeat('+n+',1fr);gap:6px;margin:14px 0">';
for(var i=0;i<n*n;i++){html+='<div onclick="AG.pick('+(i===pos)+')" style="text-align:center;font-size:1.6rem;cursor:pointer;padding:6px;border-radius:8px;background:#f9fafb">'+(i===pos?o:base)+'</div>';}
html+='</div>';A.say(html);}
window.AG={pick:function(ok){if(ok){sc++;}rd++;if(rd>=10){A.say('<div style="font-size:1.4rem">10 题答对 '+sc+' 题</div><button onclick="AG.again()">再来</button>');return;}draw();},again:function(){sc=0;rd=0;draw();}};
draw();}`});

add({id:'pattern',cat:'益智',t:{zh:'数列找规律',en:'Number Pattern',ar:'نمط الأرقام'},
 p:{zh:'备考与逻辑爱好者',en:'Pattern solvers',ar:'محبو الأنماط'},
 pain:{zh:'规律看不出来',en:'Missing the pattern',ar:'تفويت النمط'},
 units:[{zh:'等差',en:'Arithmetic',ar:'حسابي'},{zh:'等比',en:'Geometric',ar:'هندسي'},{zh:'斐波那契',en:'Fibonacci',ar:'فيبوناتشي'},{zh:'平方数',en:'Squares',ar:'مربعات'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var sc=0,rd=0,cur=null;
function nq(){var sg=[],i;if(t===0){var a=A.rnd(1,9),d=A.rnd(2,3+lv*3);for(i=0;i<5;i++)sg.push(a+i*d);}
else if(t===1){var b=A.rnd(1,4),r=A.rnd(2,2+((lv>2)?1:0)+1);for(i=0;i<5;i++)sg.push(b*Math.pow(r,i));}
else if(t===2){sg=[1,1];for(i=2;i<5;i++)sg.push(sg[i-1]+sg[i-2]);}
else{var st=A.rnd(1,5);for(i=0;i<5;i++)sg.push(Math.pow(st+i,2));}
cur={s:sg.join(', ')+', ?',q:sg[4]};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.s+'</div>'+A.opts(cur.q,Math.max(2,Math.round(Math.abs(cur.q)*0.2)+1)));}
draw();}`});

add({id:'guess',cat:'益智',t:{zh:'猜数字',en:'Guess the Number',ar:'خمّن الرقم'},
 p:{zh:'等人时打发时间',en:'Killing time',ar:'قتل الوقت'},
 pain:{zh:'无聊没事做',en:'Boredom',ar:'ملل'},
 units:[{zh:'1-100',en:'1-100',ar:'1-100'},{zh:'1-1000',en:'1-1000',ar:'1-1000'},{zh:'1-10000',en:'1-10000',ar:'1-10000'}],lvs:2,skins:3,
 mk:(u,l,s)=>`function go(){var max=[100,1000,10000][${u}];var goal=A.rnd(1,max);var tries=0;
window.AG={go:function(){var v=parseInt(A.el('g').value,10);if(!v)return;tries++;var h='';if(v===goal)h='<div style="font-size:1.5rem;color:#166534">猜中!就是 '+goal+',共用 '+tries+' 次</div><button onclick="AG.again()">再来</button>';
else h='<div style="font-size:1.3rem">'+(v<goal?'太小了 ⬆':'太大了 ⬇')+' · 已猜 '+tries+' 次</div><input id="g" type="number" style="font-size:1.3rem"><br><button onclick="AG.go()">再猜</button>';
A.say('<div style="font-size:.9rem;color:#555">范围 1 - '+max+'</div>'+h);},again:function(){goal=A.rnd(1,max);tries=0;init();}};
function init(){A.say('<div style="font-size:.9rem;color:#555">范围 1 - '+max+'</div><input id="g" type="number" style="font-size:1.3rem"><br><button onclick="AG.go()">猜</button>');}
init();}`});

add({id:'p24',cat:'益智',t:{zh:'24 点',en:'24 Game',ar:'لعبة 24'},
 p:{zh:'喜欢数学游戏的人',en:'Math-game players',ar:'لاعبو الرياضيات'},
 pain:{zh:'四则运算不灵活',en:'Rigid arithmetic',ar:'جمود حسابي'},
 units:[{zh:'简单',en:'Easy',ar:'سهل'},{zh:'困难',en:'Hard',ar:'صعب'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var cur=null;
function nq(){var ok=false,c;while(!ok){var a=A.rnd(1,9+lv*3),b=A.rnd(1,9+lv*3),cc=A.rnd(1,9+lv*3),d=A.rnd(1,9+lv*3);
c=[a,b,cc,d];ok=solvable(c);}cur=c;}
function solvable(c){var n=c.length;if(n===1)return Math.abs(c[0]-24)<0.0001;for(var i=0;i<n;i++)for(var j=0;j<n;j++){if(i===j)continue;var rest=[];for(var k=0;k<n;k++)if(k!==i&&k!==j)rest.push(c[k]);var a=c[i],b=c[j];var cand=[a+b,a-b,a*b];if(Math.abs(b)>1e-9)cand.push(a/b);for(var q=0;q<cand.length;q++){if(solvable(rest.concat([cand[q]])))return true;}}return false;}
window.AG={chk:function(){var v=A.el('e').value;var ok=false;try{var f=new Function('return ('+v+')');var r=f();ok=Math.abs(r-24)<0.001;}catch(err){ok=false;}
A.say('<div style="font-size:.9rem;color:#555">用 + - × ÷ 和括号,把 4 个数字算成 24</div><div style="font-size:2rem;letter-spacing:10px;margin:14px 0;font-weight:700">'+cur.join(' ')+'</div><input id="e" placeholder="如 (3+3)*(2+2)" value="'+(v||'').replace(/"/g,'')+'"><br>'+(ok?'<div style="font-size:1.4rem;color:#166534">正确!</div>':'<div style="font-size:1.1rem;color:#991b1b">还不是 24,再想想</div>')+'<button onclick="AG.chk()">检查</button><button onclick="AG.next()">换一题</button>');},next:function(){nq();draw();}};
function draw(){A.say('<div style="font-size:.9rem;color:#555">用 + - × ÷ 算 24</div><div style="font-size:2rem;letter-spacing:10px;margin:14px 0;font-weight:700">'+cur.join(' ')+'</div><input id="e" placeholder="如 (3+3)*(2+2)"><br><button onclick="AG.chk()">检查</button><button onclick="AG.next()">换一题</button>');}
nq();draw();}`});

add({id:'hanoi',cat:'益智',t:{zh:'汉诺塔',en:'Tower of Hanoi',ar:'أبراج هانوي'},
 p:{zh:'喜欢解谜的人',en:'Puzzle solvers',ar:'حلّالو الألغاز'},
 pain:{zh:'逻辑规划弱',en:'Weak planning',ar:'تخطيط ضعيف'},
 units:[{zh:'经典',en:'Classic',ar:'كلاسيكي'},{zh:'计时',en:'Timed',ar:'مؤقت'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var n=${l+3};var pegs=[[],[],[]];for(var i=n;i>=1;i--)pegs[0].push(i);var sel=null,moves=0,t0=Date.now();
window.AG={tap:function(p){if(sel===null){if(pegs[p].length){sel=p;draw();}return;}
if(sel===p){sel=null;draw();return;}
var d=pegs[sel][pegs[sel].length-1];var top=pegs[p][pegs[p].length-1];
if(top&&top<d){A.say('<div style="color:#991b1b">不能把大块放到小块上</div><button onclick="AG.re()">返回</button>');setTimeout(draw,900);return;}
pegs[p].push(pegs[sel].pop());moves++;sel=null;draw();},re:function(){sel=null;draw();}};
function draw(){var done=pegs[2].length===n;var html='<div style="font-size:.9rem;color:#555">把 '+n+' 层从 A 移到 C · 步数 '+moves+'</div><div style="display:flex;gap:10px;margin:14px 0">';
['A','B','C'].forEach(function(nm,p){html+='<div onclick="AG.tap('+p+')" style="flex:1;min-height:150px;border-bottom:6px solid #111;display:flex;flex-direction:column-reverse;align-items:center;gap:4px;cursor:pointer;padding-bottom:6px">';
pegs[p].forEach(function(d,i){var last=i===pegs[p].length-1;html+='<div style="width:'+(20+d*18)+'px;height:16px;border-radius:4px;background:'+(sel===p&&last?'#f59e0b':'#111')+'"></div>';});
html+='<div style="font-size:.8rem;color:#555;margin-top:6px">'+nm+'</div></div>';});
html+='</div>';if(done)html+='<div style="font-size:1.3rem;color:#166534;font-weight:700">完成!共 '+moves+' 步'+(moves===Math.pow(2,n)-1?' (最优!)':'')+'</div>';
A.say(html);}
draw();}`});

add({id:'ttt',cat:'益智',t:{zh:'井字棋',en:'Tic-Tac-Toe',ar:'إكس-أو'},
 p:{zh:'想找对手下棋',en:'No opponent around',ar:'لا منافس'},
 pain:{zh:'找不到人陪玩',en:'Nobody to play with',ar:'لا أحد يلعب'},
 units:[{zh:'你(人)先手',en:'You first',ar:'أنت أولاً'},{zh:'电脑先手',en:'AI first',ar:'الحاسوب أولاً'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var hard=${l>0?1:0};var b=['','','','','','','','',''];var my='X',ai='O';var turn=0;
function win(s){var L=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];for(var i=0;i<L.length;i++){var a=L[i];if(s[a[0]]&&s[a[0]]===s[a[1]]&&s[a[1]]===s[a[2]])return s[a[0]];}return s.indexOf('')<0?'D':'';}
function best(){if(!hard){var e=[];b.forEach(function(v,i){if(!v)e.push(i);});return A.pick(e);}
var r=minimax(b,ai).i;return r;}
function minimax(s,p){var w=win(s);if(w==='O')return {s:10};if(w==='X')return {s:-10};if(w==='D')return {s:0};
var moves=[];for(var i=0;i<9;i++)if(!s[i])moves.push(i);var bs=p===ai?-99:99,bestI=null;
moves.forEach(function(i){var c=s.slice();c[i]=p;var v=minimax(c,p===ai?'X':'O').s;if(p===ai){if(v>bs){bs=v;bestI=i;}}else{if(v<bs){bs=v;bestI=i;}}});return {s:bs,i:bestI};}
function draw(){var w=win(b);var html='<div style="font-size:.9rem;color:#555">你 = X,电脑 = O</div><div style="display:grid;grid-template-columns:repeat(3,72px);gap:6px;justify-content:center;margin:16px 0">';
b.forEach(function(v,i){html+='<div onclick="AG.p('+i+')" style="width:72px;height:72px;display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:700;background:#f3f4f6;border-radius:10px;cursor:pointer">'+v+'</div>';});
html+='</div>';if(w==='X')html+='<div style="font-size:1.3rem;color:#166534">你赢了!</div><button onclick="AG.re()">再来</button>';
else if(w==='O')html+='<div style="font-size:1.3rem;color:#991b1b">电脑赢了</div><button onclick="AG.re()">再来</button>';
else if(w==='D')html+='<div style="font-size:1.3rem">平局</div><button onclick="AG.re()">再来</button>';
A.say(html);}
window.AG={p:function(i){if(b[i]||win(b))return;b[i]=my;if(win(b)){draw();return;}var m=best();if(m!=null&&b[m]==='')b[m]=ai;draw();},re:function(){b=['','','','','','','','',''];if(${u}===1){b[4]=ai;}draw();}};
if(${u}===1){b[4]=ai;}
draw();}`});

add({id:'sudoku',cat:'益智',t:{zh:'数独',en:'Sudoku',ar:'سودوكو'},
 p:{zh:'喜欢逻辑游戏的人',en:'Logic gamers',ar:'محبو المنطق'},
 pain:{zh:'脑子需要热身',en:'Brain warm-up',ar:'تسخين الدماغ'},
 units:[{zh:'4x4',en:'4x4',ar:'4x4'},{zh:'6x6',en:'6x6',ar:'6x6'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var N=${u===0?4:6};var Bk=${u===0?2:3};var Br=${u===0?2:2};var base,mask,cur=null;
function gen(){var n=N;function ok(g,r,c,v){for(var i=0;i<n;i++){if(g[r][i]===v||g[i][c]===v)return false;}var br=Math.floor(r/Br)*Br,bc=Math.floor(c/Bk)*Bk;for(var i=0;i<Br;i++)for(var j=0;j<Bk;j++)if(g[br+i][bc+j]===v)return false;return true;}
function fill(g,p){if(p>=n*n)return true;var r=Math.floor(p/n),c=p%n;var vals=A.shuffle(Array.from({length:n},function(_,i){return i+1;}));for(var i=0;i<vals.length;i++){if(ok(g,r,c,vals[i])){g[r][c]=vals[i];if(fill(g,p+1))return true;g[r][c]=0;}}return false;}
var g=Array.from({length:n},function(){return Array(n).fill(0);});fill(g,0);return g;}
if(!cur){cur=gen();mask=Array.from({length:N},function(){return Array(N).fill(false);});var holes=[3,4,5][${l}]||3;var cells=A.shuffle(Array.from({length:N*N},function(_,i){return i;}));for(var i=0;i<holes;i++)mask[Math.floor(cells[i]/N)][cells[i]%N]=true;}
window.AG={set:function(r,c,v){if(mask[r][c])return;cur[r][c]=parseInt(v,10)||0;draw();}};
function draw(){var bad=function(r,c){var v=cur[r][c];if(!v)return false;for(var i=0;i<N;i++){if(i!==c&&cur[r][i]===v)return true;if(i!==r&&cur[i][c]===v)return true;}var br=Math.floor(r/Br)*Br,bc=Math.floor(c/Bk)*Bk;for(var i=0;i<Br;i++)for(var j=0;j<Bk;j++)if((br+i!==r||bc+j!==c)&&cur[br+i][bc+j]===v)return true;return false;};
var html='<div style="font-size:.9rem;color:#555">填 1-'+N+',行列与宫内不重复</div><div style="display:grid;grid-template-columns:repeat('+N+',44px);gap:4px;justify-content:center;margin:14px 0">';
for(var r=0;r<N;r++)for(var c=0;c<N;c++){var v=cur[r][c];var err=v&&bad(r,c);html+='<input inputmode="numeric" value="'+(v||'')+'" oninput="AG.set('+r+','+c+',this.value)" style="width:44px;height:44px;text-align:center;font-size:1.2rem;'+(mask[r][c]?'background:#f3f4f6;font-weight:700':'')+(err?';color:#dc2626':'')+'">';}
html+='</div>';var full=cur.every(function(row){return row.every(function(x){return x;});});var anyBad=false;for(var r2=0;r2<N;r2++)for(var c2=0;c2<N;c2++)if(bad(r2,c2))anyBad=true;
if(full&&!anyBad)html+='<div style="font-size:1.3rem;color:#166534;font-weight:700">完成了!</div>';
A.say(html);}
draw();}`});

add({id:'numpad',cat:'益智',t:{zh:'数字华容道',en:'Sliding Puzzle',ar:'لوح منزلق'},
 p:{zh:'喜欢动手解谜的人',en:'Sliding puzzles',ar:'ألغاز منزلقة'},
 pain:{zh:'手指闲不住',en:'Restless fingers',ar:'أصابع لا تهدأ'},
 units:[{zh:'3x3',en:'3x3',ar:'3x3'},{zh:'4x4',en:'4x4',ar:'4x4'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var N=${u===0?3:4};var arr=[];for(var i=1;i<N*N;i++)arr.push(i);arr.push(0);arr=A.shuffle(arr);if(${l}===0){arr=[];for(var j=1;j<N*N;j++)arr.push(j);arr.push(0);}var moves=0;
window.AG={tap:function(p){var z=arr.indexOf(0);var zr=Math.floor(z/N),zc=z%N,r=Math.floor(p/N),c=p%N;
if(Math.abs(zr-r)+Math.abs(zc-c)!==1)return;arr[z]=arr[p];arr[p]=0;moves++;draw();}};
function draw(){var html='<div style="font-size:.9rem;color:#555">步数 '+moves+' · 把 1 到 '+(N*N-1)+' 排好</div><div style="display:grid;grid-template-columns:repeat('+N+',64px);gap:6px;justify-content:center;margin:14px 0">';
arr.forEach(function(v,i){html+='<div onclick="AG.tap('+i+')" style="width:64px;height:64px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;font-weight:700;border-radius:10px;cursor:pointer;background:'+(v?'#111;color:#fff':'#f3f4f6')+'">'+(v||'')+'</div>';});
html+='</div>';var win=arr.every(function(v,i){return i===arr.length-1?v===0:v===i+1;});
if(win)html+='<div style="font-size:1.3rem;color:#166534;font-weight:700">完成!用了 '+moves+' 步</div>';
A.say(html);}
draw();}`});

// ---------- 逻辑 ----------
add({id:'logic_order',cat:'逻辑',t:{zh:'排队推理',en:'Logic Ordering',ar:'ترتيب منطقي'},
 p:{zh:'想练逻辑思维的人',en:'Logic training',ar:'تدريب المنطق'},
 pain:{zh:'逻辑推理吃力',en:'Weak reasoning',ar:'ضعف الاستدلال'},
 units:[{zh:'身高',en:'Height',ar:'طول'},{zh:'年龄',en:'Age',ar:'عمر'},{zh:'速度',en:'Speed',ar:'سرعة'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var names=['小明','小红','小刚','小丽','小强'].slice(0,3+Math.min(lv,2));var arr=names.slice();var truth=arr.slice();
var facts=[];for(var i=0;i<truth.length-1;i++){facts.push(truth[i]+' 比 '+truth[i+1]+' '+(['高','大','快'][${u}]));}
window.AG={chk:function(){var v=A.el('ord').value.replace(/\s/g,'').split(/[>,，、]/).filter(Boolean);if(v.join('')===truth.join('')){A.say('<div style="font-size:1.4rem;color:#166534">正确!</div><button onclick="AG.re()">再来</button>');}else{A.say('<div style="font-size:1.1rem;color:#991b1b">不对,再想想</div><div style="font-size:.9rem">提示:'+facts.join(' · ')+'</div><input id="ord" placeholder="从高到低用 &gt; 连接"><br><button onclick="AG.chk()">提交</button><button onclick="AG.re()">换一题</button>');}},re:function(){location.reload();}};
A.say('<div style="font-size:.9rem;color:#555">按'+['身高','年龄','速度'][${u}]+'从'+['高到低','大到小','快到慢'][${u}]+'排序</div><div style="margin:14px 0;font-size:1.05rem">'+facts.join('<br>')+'</div><div style="font-size:.9rem;color:#666">参与者:'+names.join('、')+'</div><input id="ord" placeholder="如 小明&gt;小红&gt;小刚"><br><button onclick="AG.chk()">提交</button>');}`});

add({id:'anagram',cat:'逻辑',t:{zh:'字母重排',en:'Anagram',ar:'إعادة ترتيب'},
 p:{zh:'喜欢文字游戏的人',en:'Word-game fans',ar:'محبو الكلمات'},
 pain:{zh:'拼写不熟练',en:'Spelling trouble',ar:'مشاكل التهجئة'},
 units:[{zh:'水果',en:'Fruit',ar:'فاكهة'},{zh:'动物',en:'Animals',ar:'حيوانات'},{zh:'颜色',en:'Colors',ar:'ألوان'},{zh:'常见词',en:'Common',ar:'شائع'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var sets=[['apple','banana','orange','grape','lemon','mango','peach','pear'],['tiger','horse','rabbit','monkey','sheep','mouse','wolf','snake'],['red','blue','green','yellow','black','white','pink','gray'],['table','chair','window','school','doctor','police','driver','water']];
var words=sets[${u}];var i=0,sc=0,cur=null;
function nq(){var w=words[i%words.length];cur={w:w,s:A.shuffle(w.split('')).join('')};if(cur.s===w)cur.s=A.shuffle(w.split('')).join('');}
window.AG={chk:function(){var v=(A.el('a').value||'').trim().toLowerCase();if(v===cur.w){sc++;i++;draw();}else{A.say('<div style="font-size:1.1rem;color:#991b1b">不对,再试试</div><div style="font-size:2rem;letter-spacing:6px;margin:12px 0">'+cur.s+'</div><input id="a"><br><button onclick="AG.chk()">提交</button><div style="font-size:.85rem;color:#666">答对 '+sc+'</div>');}}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">把字母重排成单词 · 答对 '+sc+'</div><div style="font-size:2rem;letter-spacing:6px;margin:14px 0;font-weight:700">'+cur.s+'</div><input id="a" placeholder="输入单词"><br><button onclick="AG.chk()">提交</button>');}
draw();}`});

add({id:'prime',cat:'逻辑',t:{zh:'质数判断',en:'Prime Check',ar:'فحص الأولية'},
 p:{zh:'数学学习者',en:'Math learners',ar:'متعلمو الرياضيات'},
 pain:{zh:'质数合数分不清',en:'Primes vs composites',ar:'الفرق بين الأعداد'},
 units:[{zh:'判断',en:'Judge',ar:'حكم'},{zh:'找质数',en:'Find',ar:'ابحث'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var max=[50,200,1000][${l}];var sc=0,rd=0,cur=null;
function isp(n){if(n<2)return false;for(var i=2;i*i<=n;i++)if(n%i===0)return false;return true;}
function nq(){var n=A.rnd(2,max);cur={n:n,q:isp(n)?'质数':'合数'};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div><div style="font-size:3rem;font-weight:700;margin:14px 0">'+cur.n+'</div><button onclick="AG.ans(&quot;质数&quot;)">质数</button><button onclick="AG.ans(&quot;合数&quot;)">合数</button>');}
draw();}`});

add({id:'base',cat:'逻辑',t:{zh:'进制转换',en:'Base Converter',ar:'تحويل الأنظمة'},
 p:{zh:'程序员与计算机学生',en:'Developers & CS students',ar:'المبرمجون'},
 pain:{zh:'二进制看不懂',en:'Binary confusion',ar:'ارتباك ثنائي'},
 units:[{zh:'二→十',en:'Bin→Dec',ar:'ثنائي→عشري'},{zh:'八→十',en:'Oct→Dec',ar:'ثماني→عشري'},{zh:'十六→十',en:'Hex→Dec',ar:'ست عشري→عشري'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var lim=[16,64,255][${l}];var sc=0,rd=0,cur=null;
function nq(){var n=A.rnd(2,lim);if(t===0)cur={a:n.toString(2),q:String(n)};else if(t===1)cur={a:n.toString(8),q:String(n)};else cur={a:n.toString(16).toUpperCase(),q:String(n)};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+' · '+['二进制→十进制','十进制→二进制','十六进制→十进制'][t]+'</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+A.opts(parseInt(cur.q,10),Math.max(2,Math.round(parseInt(cur.q,10)*0.3)+1)));}
draw();}`});

add({id:'roman',cat:'逻辑',t:{zh:'罗马数字',en:'Roman Numerals',ar:'الأرقام الرومانية'},
 p:{zh:'历史文化爱好者',en:'History fans',ar:'محبو التاريخ'},
 pain:{zh:'罗马数字看不明白',en:'Roman numerals',ar:'الأرقام الرومانية'},
 units:[{zh:'认读',en:'Read',ar:'قراءة'},{zh:'书写',en:'Write',ar:'كتابة'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var max=[20,100,500][${l}];var sc=0,rd=0,cur=null;
function rn(n){var m=[[1000,'M'],[900,'CM'],[500,'D'],[400,'CD'],[100,'C'],[90,'XC'],[50,'L'],[40,'XL'],[10,'X'],[9,'IX'],[5,'V'],[4,'IV'],[1,'I']];var s='';for(var i=0;i<m.length;i++){while(n>=m[i][0]){s+=m[i][1];n-=m[i][0];}}return s;}
function nq(){var n=A.rnd(1,max);if(t===0){cur={a:rn(n),q:String(n)};}
else{var wrong=[];while(wrong.length<3){var m=A.rnd(1,max);var r=rn(m);if(r!==rn(n)&&wrong.indexOf(r)<0)wrong.push(r);}cur={a:String(n),q:rn(n),o:A.shuffle([rn(n)].concat(wrong))};}}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div><div style="font-size:2.4rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+(t===0?A.opts(parseInt(cur.q,10),Math.max(3,Math.round(parseInt(cur.q,10)*0.2))):cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join('')));}
draw();}`});

add({id:'gcdlcm',cat:'逻辑',t:{zh:'最大公约数',en:'GCD & LCM',ar:'القاسم والمضاعف'},
 p:{zh:'数学学习者',en:'Math learners',ar:'متعلمو الرياضيات'},
 pain:{zh:'分数线化简头疼',en:'Fraction reduction',ar:'تبسيط الكسور'},
 units:[{zh:'GCD',en:'GCD',ar:'ق.م.أ'},{zh:'LCM',en:'LCM',ar:'م.م.أ'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var max=[20,60,200][${l}];var sc=0,rd=0,cur=null;
function gcd(a,b){while(b){var t2=b;b=a%b;a=t2;}return a;}
function nq(){var a=A.rnd(2,max),b=A.rnd(2,max);var g=gcd(a,b);var q=(t===0)?g:(a*b/g);cur={a:a+', '+b,q:q};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+' · '+['最大公约数','最小公倍数'][t]+'</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+A.opts(cur.q,Math.max(2,Math.round(cur.q*0.3)+1)));}
draw();}`});

add({id:'weekday',cat:'逻辑',t:{zh:'星期推算',en:'Day of Week',ar:'يوم الأسبوع'},
 p:{zh:'要安排日程的人',en:'Schedulers',ar:'منظمو المواعيد'},
 pain:{zh:'日期算不准',en:'Date math',ar:'حساب التواريخ'},
 units:[{zh:'未来',en:'Future',ar:'مستقبل'},{zh:'过去',en:'Past',ar:'ماضٍ'},{zh:'跨月',en:'Across months',ar:'عبر الأشهر'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var W=['周日','周一','周二','周三','周四','周五','周六'];var sc=0,rd=0,cur=null;
function nq(){var d=new Date();var today=d.getDay();var off=((${u}===1)?-1:1)*A.rnd(1,7+lv*20);var t=new Date(d.getTime()+off*86400000);cur={a:'今天是'+W[today]+', '+off+' 天后是星期?',q:W[t.getDay()]};if(${u}===1)cur.a='今天是'+W[today]+', '+(-off)+' 天前是星期?';}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div><div style="font-size:1.4rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+A.shuffle(W).map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''));}
draw();}`});

add({id:'unitconv',cat:'逻辑',t:{zh:'单位换算',en:'Unit Converter',ar:'تحويل الوحدات'},
 p:{zh:'学生与生活达人',en:'Students & DIY',ar:'طلاب وعمليون'},
 pain:{zh:'单位换算老出错',en:'Unit conversion errors',ar:'أخطاء التحويل'},
 units:[{zh:'长度',en:'Length',ar:'طول'},{zh:'重量',en:'Weight',ar:'وزن'},{zh:'时间',en:'Time',ar:'زمن'},{zh:'数据',en:'Data',ar:'بيانات'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var sc=0,rd=0,cur=null;
var L=[[['1 米 = ? 厘米',100],['1 公里 = ? 米',1000],['1 米 = ? 毫米',1000],['1 英尺 = ? 英寸',12]],
[['1 公斤 = ? 克',1000],['1 吨 = ? 公斤',1000],['1 斤 = ? 克',500],['1 磅 ≈ ? 克',454]],
[['1 小时 = ? 秒',3600],['1 天 = ? 小时',24],['1 分钟 = ? 秒',60],['1 周 = ? 天',7]],
[['1 KB = ? 字节',1024],['1 MB = ? KB',1024],['1 GB = ? MB',1024],['1 TB = ? GB',1024]]];
function nq(){var row=A.pick(L[t]);var mult=[1,10,100][lv-1];var mm=row[1]*((lv===1)?1:1);var n=A.rnd(1,9)*(lv>2?100:1);cur={a:row[0].replace('1 ',n+' '),q:n*row[1]};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div><div style="font-size:1.4rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+A.opts(cur.q,Math.max(2,Math.round(cur.q*0.25)+1)));}
draw();}`});

add({id:'tally',cat:'逻辑',t:{zh:'账单 AA',en:'Bill Split',ar:'تقسيم الفاتورة'},
 p:{zh:'聚餐要算账的人',en:'Group diners',ar:'المتسوقون'},
 pain:{zh:'分摊算不清',en:'Split confusion',ar:'ارتباك التقسيم'},
 units:[{zh:'均分',en:'Equal',ar:'متساوٍ'},{zh:'含小费',en:'With tip',ar:'مع بقشيش'},{zh:'按比例',en:'Weighted',ar:'مُوزّع'}],lvs:2,skins:3,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var sc=0,rd=0,cur=null;
function nq(){var n=A.rnd(2,4+lv*2),bill=A.rnd(8,40)*10;
if(t===0){cur={a:'账单 ¥'+bill+','+n+' 人均分,每人?',q:Math.round(bill/n)};}
else if(t===1){var tip=[10,15,20][A.rnd(0,2)];cur={a:'账单 ¥'+bill+' + '+tip+'% 小费,'+n+' 人均分,每人?',q:Math.round(bill*(100+tip)/100/n)};}
else{var a=A.rnd(2,4),b=A.rnd(2,4);cur={a:'账单 ¥'+bill+',甲吃 '+a+' 份、乙吃 '+b+' 份,账面比例,甲付?',q:Math.round(bill*a/(a+b))};}}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div><div style="font-size:1.3rem;margin:14px 0;font-weight:700">'+cur.a+'</div>'+A.opts(cur.q,Math.max(2,Math.round(cur.q*0.15)+1)));}
draw();}`});

// ---------- 休闲/专注 ----------
add({id:'typing',cat:'休闲',t:{zh:'打字速度',en:'Typing Speed',ar:'سرعة الكتابة'},
 p:{zh:'需要打字快的人',en:'Typists',ar:'الكاتبون'},
 pain:{zh:'打字慢',en:'Slow typing',ar:'كتابة بطيئة'},
 units:[{zh:'中文短句',en:'Chinese',ar:'صيني'},{zh:'英文单词',en:'English',ar:'إنجليزي'},{zh:'数字',en:'Digits',ar:'أرقام'},{zh:'符号',en:'Symbols',ar:'رموز'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var POOL=[['的'+'工作学习生活时间朋友家人','坚持每天进步一点点','认真做事踏实做人','机会总是留给有准备的人'],['the quick brown fox jumps over a lazy dog','practice makes perfect every single day','learning never exhausts the mind'],['7 3 9 1 4 0 8 2 6 5','11 22 33 44 55 66 77','908 17 4 62 350 8'],['@ # $ % ^ & * ( ) _ +','! ? , . ; : \\' " - = /']][${u}];
var text=A.pick(POOL).repeat(lv);var t0=null,elapsed=0,timer=null;
function render(typed){var shown='';for(var i=0;i<text.length;i++){var c=text[i];var cls=(i<typed.length)?(typed[i]===c?'ok':'bad'):'';var col=cls==='ok'?'#166534':cls==='bad'?'#dc2626':'#111';var bg=cls==='ok'?'#dcfce7':cls==='bad'?'#fee2e2':'transparent';shown+='<span style="color:'+col+';background:'+bg+'">'+c+'</span>';}
A.say('<div style="font-size:.9rem;color:#555">用时 '+elapsed+'s · 进度 '+typed.length+'/'+text.length+'</div><div style="margin:14px 0;font-size:1.05rem;line-height:2;font-family:monospace">'+shown+'</div><input id="ti" autocomplete="off" spellcheck="false" placeholder="照着打字,不用按回车">');var inp=A.el('ti');inp.oninput=function(){if(!t0){t0=Date.now();timer=setInterval(function(){elapsed=Math.round((Date.now()-t0)/1000);var s=A.el('o').querySelector('div');if(s)s.textContent='用时 '+elapsed+'s · 进度 '+inp.value.length+'/'+text.length;},1000);}if(inp.value===text){clearInterval(timer);var secs=Math.max(1,(Date.now()-t0)/1000);A.say('<div style="font-size:1.4rem;color:#166534;font-weight:700">完成!'+secs.toFixed(1)+'s · 速度 '+(text.length/secs).toFixed(1)+' 字/秒</div><button onclick="AG.re()">再来</button>');return;}render(inp.value);};inp.focus();}
window.AG={re:function(){location.reload();}};
render('');}`});

add({id:'simon',cat:'记忆',t:{zh:'记忆亮灯',en:'Simon Says',ar:'سايمون يقول'},
 p:{zh:'喜欢经典小游戏的人',en:'Classic-game fans',ar:'محبو الكلاسيكيات'},
 pain:{zh:'注意力不集中',en:'Short attention',ar:'تشتت الانتباه'},
 units:[{zh:'4 色',en:'4 colors',ar:'4 ألوان'},{zh:'6 色',en:'6 colors',ar:'6 ألوان'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var n=${u===0?4:6};var COL=['#ef4444','#22c55e','#3b82f6','#eab308','#a855f7','#ec4899'].slice(0,n);var seq=[],input=[],best=0,lit=-1,showing=false;
function next(){seq.push(A.rnd(0,n-1));play();}
function play(){showing=true;var i=0;var t=setInterval(function(){lit=seq[i];draw();setTimeout(function(){lit=-1;draw();},320);i++;if(i>=seq.length){clearInterval(t);setTimeout(function(){showing=false;input=[];draw();},420);}},520);}
window.AG={tap:function(c){if(showing)return;lit=c;input.push(c);draw();setTimeout(function(){lit=-1;draw();},200);
var i=input.length-1;if(input[i]!==seq[i]){if(seq.length-1>best)best=seq.length-1;A.say('<div style="font-size:1.3rem">错了 · 长度 '+seq.length+' · 最佳 '+best+'</div><button onclick="AG.re()">再来</button>');return;}
if(input.length===seq.length){if(seq.length>best)best=seq.length;setTimeout(next,600);}}};
window.AG.re=function(){seq=[];best=best;next();};
function draw(){var html='<div style="font-size:.9rem;color:#555">长度 '+seq.length+' · 最佳 '+best+' · '+(showing?'看好了':'轮到你了')+'</div><div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:14px 0">';
COL.forEach(function(c,i){var on=(lit===i);html+='<div onclick="AG.tap('+i+')" style="height:80px;border-radius:12px;cursor:pointer;background:'+c+';opacity:'+(on?1:0.35)+';transition:opacity .15s"></div>';});
html+='</div>';A.say(html);}
next();}`});

add({id:'snake',cat:'休闲',t:{zh:'贪吃蛇',en:'Snake',ar:'الثعبان'},
 p:{zh:'打发时间的人',en:'Time killers',ar:'قاتلو الوقت'},
 pain:{zh:'无聊想玩点老的',en:'Craving retro fun',ar:'اشتياق للكلاسيكيات'},
 units:[{zh:'经典',en:'Classic',ar:'كلاسيكي'},{zh:'高速',en:'Fast',ar:'سريع'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var N=15;var speed=${u===1?90:150};var snake=[{x:7,y:7}],dir={x:1,y:0},food={x:3,y:3},t=null,dead=false,sc=0;
function rndFood(){do{food={x:A.rnd(0,N-1),y:A.rnd(0,N-1)};}while(snake.some(function(p){return p.x===food.x&&p.y===food.y;}));}
window.AG={turn:function(x,y){if(dir.x===-x&&dir.y===-y)return;dir={x:x,y:y};}};
document.onkeydown=function(e){if(e.key==='ArrowUp')AG.turn(0,-1);if(e.key==='ArrowDown')AG.turn(0,1);if(e.key==='ArrowLeft')AG.turn(-1,0);if(e.key==='ArrowRight')AG.turn(1,0);};
function step(){var h={x:snake[0].x+dir.x,y:snake[0].y+dir.y};
if(h.x<0||h.y<0||h.x>=N||h.y>=N||snake.some(function(p){return p.x===h.x&&p.y===h.y;})){clearInterval(t);dead=true;draw();return;}
snake.unshift(h);if(h.x===food.x&&h.y===food.y){sc++;rndFood();}else{snake.pop();}draw();}
function draw(){var cells='';for(var y=0;y<N;y++)for(var x=0;x<N;x++){var isS=snake.some(function(p){return p.x===x&&p.y===y;});var isF=(food.x===x&&food.y===y);cells+='<div style="background:'+(isF?'#ef4444':isS?'#111':'#f3f4f6')+'"></div>';}
A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+' · 方向键控制</div><div style="display:grid;grid-template-columns:repeat('+N+',18px);gap:2px;margin:12px 0;justify-content:center">'+cells+'</div>'+(dead?'<div style="font-size:1.3rem;color:#991b1b">游戏结束,得分 '+sc+'</div><button onclick="location.reload()">再来</button>':'<div class="row"><button onclick="AG.turn(0,-1)">↑</button><button onclick="AG.turn(-1,0)">←</button><button onclick="AG.turn(0,1)">↓</button><button onclick="AG.turn(1,0)">→</button></div>'));}
rndFood();draw();t=setInterval(step,speed);}`});

add({id:'g2048',cat:'休闲',t:{zh:'2048 合成',en:'2048 Merge',ar:'دمج 2048'},
 p:{zh:'数字游戏爱好者',en:'Number-game fans',ar:'محبو الأرقام'},
 pain:{zh:'想玩点需要思考的',en:'Want a thinking game',ar:'لعبة تفكير'},
 units:[{zh:'4x4',en:'4x4',ar:'4x4'},{zh:'5x5',en:'5x5',ar:'5x5'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var N=${u===0?4:5};var g=Array.from({length:N},function(){return Array(N).fill(0);});var sc=0;var COL={2:'#eee',4:'#ddd',8:'#fdba74',16:'#fb923c',32:'#f97316',64:'#ef4444',128:'#eab308',256:'#22c55e',512:'#3b82f6',1024:'#a855f7',2048:'#111'};
function add(){var e=[];g.forEach(function(r,y){r.forEach(function(v,x){if(!v)e.push([x,y]);});});if(!e.length)return;var p=A.pick(e);g[p[1]][p[0]]=Math.random()<0.9?2:4;}
function move(dx,dy){var moved=false;function line(cells){var vals=cells.map(function(p){return g[p[1]][p[0]];}).filter(Boolean);for(var i=0;i<vals.length-1;i++){if(vals[i]===vals[i+1]){vals[i]*=2;sc+=vals[i];vals[i+1]=0;}}
vals=vals.filter(Boolean);while(vals.length<N)vals.push(0);cells.forEach(function(p,i){if(g[p[1]][p[0]]!==vals[i])moved=true;g[p[1]][p[0]]=vals[i];});}
for(var i=0;i<N;i++){var cells=[];for(var j=0;j<N;j++)cells.push(dx?[dx>0?N-1-j:j,i]:[i,dy>0?N-1-j:j]);line(cells);}
if(moved)add();draw();}
window.AG={mv:function(dx,dy){move(dx,dy);}};
document.onkeydown=function(e){if(e.key==='ArrowUp')AG.mv(0,-1);if(e.key==='ArrowDown')AG.mv(0,1);if(e.key==='ArrowLeft')AG.mv(-1,0);if(e.key==='ArrowRight')AG.mv(1,0);};
function draw(){var html='<div style="font-size:.9rem;color:#555">得分 '+sc+' · 方向键或按钮移动</div><div style="display:grid;grid-template-columns:repeat('+N+',64px);gap:8px;margin:14px 0;justify-content:center">';
g.forEach(function(r){r.forEach(function(v){html+='<div style="width:64px;height:64px;display:flex;align-items:center;justify-content:center;border-radius:10px;font-weight:700;font-size:'+(v>999?'1rem':'1.3rem')+';background:'+(v?(COL[v]||'#111'):'#f9fafb')+';color:'+(v===2||v===4?'#111':'#fff')+'">'+(v||'')+'</div>';});});
html+='</div><div class="row"><button onclick="AG.mv(0,-1)">↑</button><button onclick="AG.mv(-1,0)">←</button><button onclick="AG.mv(0,1)">↓</button><button onclick="AG.mv(1,0)">→</button></div>';
A.say(html);}
add();add();draw();}`});

add({id:'stroop',cat:'反应',t:{zh:'色词干扰',en:'Stroop Test',ar:'اختبار ستروب'},
 p:{zh:'想测专注力的人',en:'Focus testing',ar:'اختبار التركيز'},
 pain:{zh:'容易分心',en:'Easily distracted',ar:'سهل التشتت'},
 units:[{zh:'选字义',en:'Word',ar:'الكلمة'},{zh:'选颜色',en:'Color',ar:'اللون'},{zh:'交替',en:'Alternate',ar:'تبديل'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var mode=${u};var lv=${l+1};var C=[['红','#ef4444'],['绿','#22c55e'],['蓝','#3b82f6'],['黄','#eab308']];var sc=0,rd=0,cur=null,alt=0;
function nq(){var w=A.pick(C),c=A.pick(C);cur={word:w[0],color:c};var m=mode;if(mode===2){m=alt%2;alt++;}cur.mode=m;cur.ask=(m===0)?'选字义(读到的词)':'选颜色(看到的颜色)';cur.q=(m===0)?cur.word:cur.color[0];}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">'+cur.ask+' · 得分 '+sc+'/'+rd+'</div><div style="font-size:3rem;font-weight:700;margin:14px 0;color:'+cur.color[1]+'">'+cur.word+'</div>'+A.shuffle(C).map(function(o){return '<button onclick="AG.ans(&quot;'+o[0]+'&quot;)">'+o[0]+'</button>';}).join(''));}
draw();}`});

add({id:'whack',cat:'反应',t:{zh:'打地鼠',en:'Whack-a-Mole',ar:'اضرب الخلد'},
 p:{zh:'想放松又练反应',en:'Relax + reflexes',ar:'استرخاء ورد فعل'},
 pain:{zh:'压力大想发泄',en:'Stress relief',ar:'تنفيس التوتر'},
 units:[{zh:'地鼠',en:'Mole',ar:'خلد'},{zh:'数字',en:'Numbers',ar:'أرقام'},{zh:'字母',en:'Letters',ar:'حروف'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var N=9;var hole=-1,sc=0,miss=0,left=30+lv*10,t=null,tm=null;
var SYM=['🐹','🐰','🐻','🦊','🐼','🐸','🐷','🐵','🐯'];var target=(Math.random()<0.5)?'X':'O';
function pop(){if(hole>=0)miss++;hole=A.rnd(0,N-1);draw();}
function draw(){var html='<div style="display:flex;justify-content:space-between;font-size:.9rem"><b>得分 '+sc+'</b><b>漏 '+miss+'</b><b>剩余 '+left+'s</b></div><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0">';
for(var i=0;i<N;i++){var show=(i===hole);var face=(${u}===0)?'🐹':(${u}===1)?String(A.rnd(100,999)):'❓';
html+='<div onclick="AG.hit('+i+')" style="height:70px;display:flex;align-items:center;justify-content:center;font-size:1.6rem;border-radius:12px;background:'+(show?'#fde68a':'#f3f4f6')+';cursor:pointer">'+(show?face:'')+'</div>';}
html+='</div>';A.say(html);}
window.AG={hit:function(i){if(i===hole){sc++;hole=-1;draw();}else{miss++;draw();}}};
pop();t=setInterval(pop,Math.max(650,1400-lv*250));tm=setInterval(function(){left--;if(left<=0){clearInterval(t);clearInterval(tm);A.say('<div style="font-size:1.4rem">时间到!得分 '+sc+' · 漏 '+miss+'</div><button onclick="location.reload()">再来</button>');return;}var b=A.el('o').querySelectorAll('b');if(b[2])b[2].textContent='剩余 '+left+'s';},1000);}`});

add({id:'sortnum',cat:'益智',t:{zh:'数字排序',en:'Number Sort',ar:'ترتيب الأرقام'},
 p:{zh:'想练数字感的人',en:'Number sense',ar:'حس الأرقام'},
 pain:{zh:'大小比较慢',en:'Slow comparisons',ar:'بطء المقارنة'},
 units:[{zh:'从小到大',en:'Ascending',ar:'تصاعدي'},{zh:'从大到小',en:'Descending',ar:'تنازلي'},{zh:'绝对值',en:'Absolute',ar:'مطلق'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var n=4+lv;var sc=0,rd=0,cur=null;
function nq(){var a=[];while(a.length<n){var v=A.rnd(-99,99);if(a.indexOf(v)<0)a.push(v);}cur={a:a,q:a.slice().sort(function(x,y){return (t===0)?x-y:(t===1)?y-x:(Math.abs(x)-Math.abs(y))||(x-y);}).join(',')};}
window.AG={chk:function(){var v=(A.el('s').value||'').split(/[,\s，]+/).filter(Boolean).map(Number).join(',');if(v===cur.q){sc++;}rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+' · '+['从小到大','从大到小','按绝对值从小到大'][t]+'</div><div style="font-size:1.6rem;margin:14px 0;font-weight:700">'+cur.a.join(', ')+'</div><input id="s" placeholder="用逗号分隔"><br><button onclick="AG.chk()">提交</button>'+(rd>0?'<div style="font-size:.85rem;color:#666">上一题答案:'+cur.q+'</div>':''));}
draw();}`});

add({id:'morse',cat:'知识',t:{zh:'摩斯密码',en:'Morse Code',ar:'شفرة مورس'},
 p:{zh:'通信与密码爱好者',en:'Crypto & comms fans',ar:'محبو الشفرات'},
 pain:{zh:'看不懂点和划',en:'Dots and dashes',ar:'النقاط والشرطات'},
 units:[{zh:'译码',en:'Decode',ar:'فك'},{zh:'编码',en:'Encode',ar:'ترميز'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var t=${u};var MAP={A:'.-',B:'-...',C:'-.-.',D:'-..',E:'.',F:'..-.',G:'--.',H:'....',I:'..',J:'.---',K:'-.-',L:'.-..',M:'--',N:'-.',O:'---',P:'.--.',Q:'--.-',R:'.-.',S:'...',T:'-',U:'..-',V:'...-',W:'.--',X:'-..-',Y:'-.--',Z:'--..'};
var keys=Object.keys(MAP);var sc=0,rd=0,cur=null;
function nq(){var k=A.pick(keys);cur=(t===0)?{a:MAP[k],q:k,o:A.shuffle(A.shuffle(keys).slice(0,3).filter(function(x){return x!==k;}).concat([k]))}:{a:k,q:MAP[k]};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();var body=(t===0)?'<div style="font-size:2rem;letter-spacing:6px;margin:14px 0;font-weight:700">'+cur.a+'</div>'+cur.o.map(function(o){return '<button onclick="AG.ans(&quot;'+o+'&quot;)">'+o+'</button>';}).join(''):'<div style="font-size:2.4rem;margin:14px 0;font-weight:700">'+cur.a+'</div><div style="font-size:.9rem;color:#666">这是 '+cur.q+' 的摩斯码</div><button onclick="AG.ans(&quot;'+cur.q+'&quot;)">记住了</button>';
A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+'</div>'+body);}
draw();}`});

add({id:'emath',cat:'算术',t:{zh:'图形算术',en:'Emoji Math',ar:'حساب بالرموز'},
 p:{zh:'儿童与亲子互动',en:'Kids & parents',ar:'أطفال وأهالٍ'},
 pain:{zh:'孩子不爱算数',en:'Kids avoid math',ar:'الأطفال يكرهون الحساب'},
 units:[{zh:'水果',en:'Fruit',ar:'فاكهة'},{zh:'动物',en:'Animals',ar:'حيوانات'},{zh:'交通工具',en:'Vehicles',ar:'مركبات'},{zh:'天气',en:'Weather',ar:'طقس'}],lvs:3,skins:4,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var SETS=[['🍎','🍌','🍇','🍊'],['🐱','🐶','🐰','🐻'],['🚗','🚕','🚌','🚲'],['☀️','🌙','⭐','☁️']];var sym=SETS[${u}];var sc=0,rd=0,cur=null;
function nq(){var a=A.rnd(1,4+lv*3),b=A.rnd(1,4+lv*2);var op=A.pick(['+','-','×']);if(op==='-'&&b>a){var t=a;a=b;b=t;}var r=op==='+'?a+b:op==='-'?a-b:a*b;cur={a:Array(a).fill(sym[0]).join(''),b:Array(b).fill(sym[1]).join(''),op:op,q:r};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+' · 数一数图形</div><div style="font-size:1.6rem;margin:14px 0;line-height:1.8">'+cur.a+' '+cur.op+' '+cur.b+' = ?</div>'+A.opts(cur.q,Math.max(2,Math.round(cur.q*0.3)+1)));}
draw();}`});

add({id:'reflex',cat:'反应',t:{zh:'文字接龙',en:'Word Chain',ar:'سلسلة كلمات'},
 p:{zh:'喜欢语言游戏的人',en:'Word-game fans',ar:'محبو الكلمات'},
 pain:{zh:'词汇量不够',en:'Limited vocabulary',ar:'مفردات محدودة'},
 units:[{zh:'英语',en:'English',ar:'إنجليزي'},{zh:'拼音',en:'Pinyin',ar:'بينيين'}],lvs:2,skins:3,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var words=${u===0?"['apple','elephant','tiger','rabbit','table','egg','goat','tree','eagle','ant']":'["苹果","果冻","冬天","天空","空气","气球","球鞋","鞋子","子女","女人"]'};var i=0,sc=0,cur=null;
function nq(){cur=words[i%words.length];}
window.AG={go:function(){var v=(A.el('w').value||'').trim();if(!v)return;var last=cur[cur.length-1].toLowerCase();var first=v[0].toLowerCase();var ok=(v.length>1&&first===last);if(ok){sc++;i++;}draw(ok);}};
function draw(ok){nq();A.say('<div style="font-size:.9rem;color:#555">接龙成功 '+sc+' 次'+(ok===false?' · <span style="color:#991b1b">要以「'+cur[cur.length-1]+'」开头</span>':'')+'</div><div style="font-size:2rem;margin:14px 0;font-weight:700">'+cur+'</div><input id="w" placeholder="以「'+cur[cur.length-1]+'」开头"><br><button onclick="AG.go()">接龙</button>');}
draw();}`});

add({id:'countwords',cat:'休闲',t:{zh:'字数统计',en:'Word Count',ar:'عد الكلمات'},
 p:{zh:'写作、论文、自媒体',en:'Writers',ar:'الكتّاب'},
 pain:{zh:'不知道够不够字数',en:'Word count unknown',ar:'عدد الكلمات'},
 units:[{zh:'中文字数',en:'Chinese',ar:'صيني'},{zh:'英文单词',en:'English',ar:'إنجليزي'}],lvs:1,skins:3,
 mk:(u,l,s)=>`function go(){window.AG={run:function(){var t=A.el('txt').value||'';var o={};if(${u}===0){o.zh=(t.match(/[\\u4e00-\\u9fa5]/g)||[]).length;o.total=t.replace(/\\s/g,'').length;o.lines=t.split(/\\n/).length;o.punct=(t.match(/[，。！？；：、,.!?;:]/g)||[]).length;}
else{var w=t.trim()?t.trim().split(/\\s+/):[];o.words=w.length;o.chars=t.length;o.sentences=t.split(/[.!?。！？]+/).filter(function(x){return x.trim();}).length;o.uniq=new Set(w.map(function(x){return x.toLowerCase();})).size;}
A.say('<div style="font-size:1.05rem;line-height:2">'+Object.keys(o).map(function(k){return k+' : <b>'+o[k]+'</b>';}).join('<br>')+'</div>');}};
A.say('<div style="font-size:.9rem;color:#555">粘贴文字后点统计</div><textarea id="txt" rows="6"></textarea><button onclick="AG.run()">统计</button>');}`});

add({id:'pwd',cat:'知识',t:{zh:'密码强度',en:'Password Strength',ar:'قوة كلمة المرور'},
 p:{zh:'关心账号安全的人',en:'Security-minded',ar:'المهتمون بالأمان'},
 pain:{zh:'密码太弱不安全',en:'Weak passwords',ar:'كلمات مرور ضعيفة'},
 units:[{zh:'强度评估',en:'Score',ar:'تقييم'},{zh:'生成密码',en:'Generate',ar:'توليد'}],lvs:1,skins:2,
 mk:(u,l,s)=>`function go(){window.AG={run:function(){var p=A.el('p').value||'';var score=0;var notes=[];
if(p.length>=8)score+=1;if(p.length>=12)score+=1;if(p.length>=16)score+=1;
if(/[a-z]/.test(p))score+=1;if(/[A-Z]/.test(p))score+=1;if(/[0-9]/.test(p))score+=1;if(/[^A-Za-z0-9]/.test(p))score+=1;
if(/^[a-z]+$/.test(p)||/^[0-9]+$/.test(p))score=Math.min(score,2);
if(/(.)\\1{2,}/.test(p))notes.push('有连续重复字符');
if(/123|abc|qwerty|password|admin/i.test(p))notes.push('含常见弱口令片段');
var lvl=score>=6?'很强':score>=4?'中等':score>=2?'偏弱':'很弱';
var entropy=Math.round(p.length*Math.log2((/[a-z]/.test(p)?26:0)+(/[A-Z]/.test(p)?26:0)+(/[0-9]/.test(p)?10:0)+(/[^A-Za-z0-9]/.test(p)?32:0)||1));
A.say('<div style="font-size:1.4rem">强度:'+lvl+' ('+score+'/7)</div><div style="font-size:.95rem;color:#555">估算熵 ≈ '+entropy+' bit'+(entropy<40?' · 建议更长或更多字符种类':'')+'</div>'+(notes.length?'<div style="color:#991b1b">'+notes.join('、')+'</div>':'')+(entropy>=60?'<div style="color:#166534">这个密码强度不错</div>':'<div style="margin-top:8px"><button onclick="AG.gen()">帮我生成一个强密码</button></div>'));},gen:function(){var chars='abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#%^&*-_+=';var out='';for(var i=0;i<20;i++)out+=chars[Math.floor(Math.random()*chars.length)];A.el('p').value=out;AG.run();}};
A.say('<div style="font-size:.9rem;color:#555">输入密码评估强度(只在本地计算,不上传)</div><input id="p" type="text" placeholder="输入要评估的密码"><br><button onclick="AG.run()">评估</button>');}`});

add({id:'balance',cat:'逻辑',t:{zh:'天平找次品',en:'Find the Odd Ball',ar:'ابحث عن الكرة المختلفة'},
 p:{zh:'喜欢经典逻辑题的人',en:'Classic puzzle fans',ar:'محبو الألغاز'},
 pain:{zh:'逻辑题不会做',en:'Stuck on logic puzzles',ar:'تعقّد الألغاز'},
 units:[{zh:'8 球',en:'8 balls',ar:'8 كرات'},{zh:'12 球',en:'12 balls',ar:'12 كرة'}],lvs:2,skins:2,
 mk:(u,l,s)=>`function go(){var n=${u===0?8:12};var odd=A.rnd(0,n-1),heavy=Math.random()<0.5;var tried=0;
window.AG={guess:function(i){tried++;if(i===odd){A.say('<div style="font-size:1.4rem;color:#166534">找到了!编号 '+(i+1)+' 的球'+(heavy?'偏重':'偏轻')+',用了 '+tried+' 次</div><button onclick="location.reload()">再来</button>');}else{A.say('<div style="font-size:1.1rem;color:#991b1b">不是这个,再想想</div><div style="font-size:.9rem;color:#666">提示:可用天平比较两组球</div><button onclick="AG.more()">继续猜</button>');}},more:function(){draw();}};
function draw(){var html='<div style="font-size:.9rem;color:#555">'+n+' 个球外观一样,其中 1 个'+(heavy?'偏重':'偏轻')+',点出它。已猜 '+tried+' 次</div><div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:14px 0">';
for(var i=0;i<n;i++){html+='<div onclick="AG.guess('+i+')" style="height:52px;display:flex;align-items:center;justify-content:center;background:#f3f4f6;border-radius:50%;cursor:pointer;font-weight:700">'+(i+1)+'</div>';}
html+='</div>';A.say(html);}
draw();}`});

add({id:'sortcolor',cat:'记忆',t:{zh:'颜色序列',en:'Color Sequence',ar:'تسلسل الألوان'},
 p:{zh:'想练视觉记忆',en:'Visual memory',ar:'الذاكرة البصرية'},
 pain:{zh:'看过就忘',en:'See and forget',ar:'أرى وأنسى'},
 units:[{zh:'短',en:'Short',ar:'قصير'},{zh:'长',en:'Long',ar:'طويل'}],lvs:3,skins:2,
 mk:(u,l,s)=>`function go(){var lv=${l+1};var len=(${u===0?2:4})+lv;var C=['#ef4444','#22c55e','#3b82f6','#eab308','#a855f7','#ec4899'];var seq=[],ans=[],phase='mem',sc=0,rd=0;
function nq(){seq=[];for(var i=0;i<len;i++)seq.push(A.rnd(0,C.length-1));ans=[];phase='mem';draw();
var box=A.el('sb');setTimeout(function(){phase='input';draw();},700+len*400);}
window.AG={tap:function(c){if(phase!=='input')return;ans.push(c);if(ans[ans.length-1]!==seq[ans.length-1]){rd++;A.say('<div style="font-size:1.2rem;color:#991b1b">错了</div><button onclick="AG.next()">继续</button>');phase='done';return;}if(ans.length===seq.length){sc++;rd++;A.say('<div style="font-size:1.2rem;color:#166534">正确!</div><button onclick="AG.next()">下一题</button>');phase='done';return;}draw();},next:function(){nq();}};
function draw(){var html='<div style="font-size:.9rem;color:#555">答对 '+sc+'/'+rd+' · '+(phase==='mem'?'记住顺序':'按顺序点')+'</div>';
if(phase==='mem'){html+='<div id="sb" style="display:flex;gap:8px;justify-content:center;margin:16px 0">'+seq.map(function(c){return '<div style="width:40px;height:40px;border-radius:8px;background:'+C[c]+'"></div>';}).join('')+'</div>';}
else if(phase==='input'){html+='<div style="display:flex;gap:8px;justify-content:center;margin:12px 0">'+ans.map(function(c){return '<div style="width:26px;height:26px;border-radius:6px;background:'+C[c]+'"></div>';}).join('')+'</div><div>'+C.map(function(c,i){return '<button style="background:'+c+'" onclick="AG.tap('+i+')">&nbsp;&nbsp;</button>';}).join('')+'</div>';}
A.say(html);}
nq();}`});

add({id:'gridmem',cat:'记忆',t:{zh:'亮格记忆',en:'Grid Memory',ar:'ذاكرة الشبكة'},
 p:{zh:'想练空间记忆的人',en:'Spatial memory',ar:'الذاكرة المكانية'},
 pain:{zh:'位置记不住',en:'Forgetting positions',ar:'نسيان المواضع'},
 units:[{zh:'3x3',en:'3x3',ar:'3x3'},{zh:'4x4',en:'4x4',ar:'4x4'},{zh:'5x5',en:'5x5',ar:'5x5'}],lvs:3,skins:5,
 mk:(u,l,s)=>`function go(){var N=${u+3};var lv=${l+1};var k=2+lv;var target=[],picked=[],phase='mem',sc=0,rd=0;
function nq(){target=[];while(target.length<k){var i=A.rnd(0,N*N-1);if(target.indexOf(i)<0)target.push(i);}picked=[];phase='mem';draw();
setTimeout(function(){phase='input';draw();},900+k*220);}
window.AG={tap:function(i){if(phase!=='input'||picked.indexOf(i)>=0)return;picked.push(i);
if(target.indexOf(i)<0){rd++;phase='done';A.say('<div style="font-size:1.2rem;color:#991b1b">点错了</div><button onclick="AG.next()">继续</button>');return;}
if(picked.length===target.length){sc++;rd++;phase='done';A.say('<div style="font-size:1.2rem;color:#166534">全对!</div><button onclick="AG.next()">下一题</button>');return;}draw();},next:function(){nq();}};
function draw(){var html='<div style="font-size:.9rem;color:#555">全对 '+sc+'/'+rd+' · '+(phase==='mem'?'记住亮格':'点出亮过的格子')+'</div><div style="display:grid;grid-template-columns:repeat('+N+',1fr);gap:6px;margin:14px 0;max-width:340px">';
for(var i=0;i<N*N;i++){var on=(phase==='mem'&&target.indexOf(i)>=0)||(phase==='input'&&picked.indexOf(i)>=0);html+='<div onclick="AG.tap('+i+')" style="height:46px;border-radius:8px;cursor:pointer;background:'+(on?'#111':'#f3f4f6')+'"></div>';}
html+='</div>';A.say(html);}
nq();}`});

add({id:'estimation',cat:'益智',t:{zh:'看图数数',en:'Count the Dots',ar:'عد النقاط'},
 p:{zh:'练数感与专注',en:'Number sense',ar:'حس الأرقام'},
 pain:{zh:'数字感差',en:'Weak number sense',ar:'ضعف الحس العددي'},
 units:[{zh:'少',en:'Few',ar:'قليل'},{zh:'中',en:'Medium',ar:'متوسط'},{zh:'多',en:'Many',ar:'كثير'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var base=[6,16,30][t];var spread=[4,10,20][t];var sc=0,rd=0,cur=null;
var SYM=['●','▲','■','★','◆'];
function nq(){var n=base+A.rnd(0,spread)+lv*2;var sym=A.pick(SYM);var html='';for(var i=0;i<n;i++)html+='<span style="font-size:1.1rem;color:'+A.pick(['#ef4444','#3b82f6','#22c55e','#eab308','#a855f7'])+'">'+sym+'</span> ';cur={n:n,html:html};}
window.AG={ans:function(v){if(v===cur.n)sc++;rd++;draw();}};
function draw(){nq();var opts=[cur.n];while(opts.length<4){var v=cur.n+A.rnd(1,Math.max(3,Math.round(cur.n*0.25)))*(Math.random()<.5?-1:1);if(v>0&&opts.indexOf(v)<0)opts.push(v);}
opts=A.shuffle(opts);A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+' · 一共有几个图形?</div><div style="margin:14px 0;line-height:1.9">'+cur.html+'</div>'+opts.map(function(o){return '<button onclick="AG.ans('+o+')">'+o+'</button>';}).join(''));}
draw();}`});

add({id:'compare',cat:'反应',t:{zh:'极速比大小',en:'Quick Compare',ar:'مقارنة سريعة'},
 p:{zh:'想加快判断速度',en:'Speed judgment',ar:'سرعة الحكم'},
 pain:{zh:'比大小要想半天',en:'Slow comparing',ar:'بطء المقارنة'},
 units:[{zh:'整数',en:'Integers',ar:'أعداد صحيحة'},{zh:'小数',en:'Decimals',ar:'عشرية'},{zh:'分数',en:'Fractions',ar:'كسور'}],lvs:3,skins:3,
 mk:(u,l,s)=>`function go(){var t=${u};var lv=${l+1};var sc=0,rd=0,cur=null;
function nq(){var a,b;if(t===0){a=A.rnd(1,99+lv*200);b=A.rnd(1,99+lv*200);}
else if(t===1){a=+(A.rnd(1,99)/10).toFixed(1);b=+(A.rnd(1,99)/100).toFixed(2);}
else{var d1=A.rnd(2,9),d2=A.rnd(2,9);a=A.rnd(1,d1-1)+'/'+d1;b=A.rnd(1,d2-1)+'/'+d2;var va=eval(a),vb=eval(b);cur={a:a,b:b,q:va>vb?'左':'右'};return;}
cur={a:String(a),b:String(b),q:a>b?'左':'右'};}
window.AG={ans:function(v){if(v===cur.q)sc++;rd++;draw();}};
function draw(){nq();A.say('<div style="font-size:.9rem;color:#555">得分 '+sc+'/'+rd+' · 哪个更大?</div><div style="display:flex;gap:12px;margin:16px 0"><div style="flex:1;text-align:center;font-size:2.2rem;font-weight:700;background:#f3f4f6;border-radius:12px;padding:20px">'+cur.a+'</div><div style="flex:1;text-align:center;font-size:2.2rem;font-weight:700;background:#f3f4f6;border-radius:12px;padding:20px">'+cur.b+'</div></div><button onclick="AG.ans(&quot;左&quot;)">左边大</button><button onclick="AG.ans(&quot;右&quot;)">右边大</button>');}
draw();}`});

module.exports={ENGINES:E,THEMES,LV};
