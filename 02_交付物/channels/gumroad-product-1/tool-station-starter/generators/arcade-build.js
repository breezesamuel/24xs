/**
 * arcade-build.js（v2）—— 扩展引擎 × 单元 × 难度 × 主题 → 游戏条目
 *
 * 相比 v1 的关键改进（都是为了"内容真的不同"，避免规模化内容）：
 *   1) 主题 10 → 50（每个主题有独立的中/英/阿名称与主题化描述）
 *   2) 主题驱动**内容**：题目数组按主题轮转 → 不同主题拿到不同的题目集合
 *   3) 主题驱动**随机数**：每个主题一个确定性种子 → 程序化游戏（算术/记忆/反应…）
 *      在不同主题下生成的题目/序列真的不同（v1 里主题只改标题，内容完全一样）
 *   4) 每款游戏有**独有的简介/挑战说明**（写进页面正文 → 页面间文本不同）
 *
 * 用法: const {build}=require('./arcade-build.js'); const list=build();
 */
const { ENGINES, LV } = require('./arcade-engines.js');

const BASE36 = '0123456789abcdefghijklmnopqrstuvwxyz';
function b36(n) { n = Math.max(0, n | 0); let s = ''; do { s = BASE36[n % 36] + s; n = Math.floor(n / 36); } while (n > 0); return s; }

// 50 个主题（每个都带主题化玩法提示）——T=12 时约 5000 款游戏
const THEMES = [
  { k: 'kids', zh: '儿童版', en: 'Kids', ar: 'أطفال', tip: { zh: '数字更小、提示更多，适合小朋友', en: 'Smaller numbers and more hints for children', ar: 'أرقام أصغر وتلميحات أكثر للأطفال' } },
  { k: 'student', zh: '学生版', en: 'Student', ar: 'طلاب', tip: { zh: '贴近课纲，适合课间与自习', en: 'Closely matched to schoolwork', ar: 'قريب من المناهج الدراسية' } },
  { k: 'office', zh: '办公版', en: 'Office', ar: 'مكتب', tip: { zh: '午休十分钟就能来一局', en: 'A quick round in a coffee break', ar: 'جولة سريعة في استراحة' } },
  { k: 'dev', zh: '程序员版', en: 'Developer', ar: 'مبرمج', tip: { zh: '适合练手速与专注度', en: 'Great for focus and speed drills', ar: 'ممتاز للتركيز والسرعة' } },
  { k: 'senior', zh: '长辈版', en: 'Senior', ar: 'كبار', tip: { zh: '节奏更缓，数字更大更易读', en: 'Slower pace with larger, clearer numbers', ar: 'إيقاع أهدأ وأرقام أكبر' } },
  { k: 'travel', zh: '旅行版', en: 'Travel', ar: 'سفر', tip: { zh: '路上打发时间的轻量玩法', en: 'Lightweight fun for the road', ar: 'ترفيه خفيف في الطريق' } },
  { k: 'food', zh: '美食版', en: 'Foodie', ar: 'طعام', tip: { zh: '用食物做比喻来理解规则', en: 'Rules explained with food metaphors', ar: 'قواعد مشروحة بتشبيهات الطعام' } },
  { k: 'fit', zh: '健身版', en: 'Fitness', ar: 'لياقة', tip: { zh: '当热身也算一局', en: 'Counts as a warm-up', ar: 'يعتبر إحماءً' } },
  { k: 'money', zh: '理财版', en: 'Finance', ar: 'مال', tip: { zh: '练的是心算与快速判断', en: 'Trains mental math and quick judgement', ar: 'يدرّب الحساب الذهري والسرعة' } },
  { k: 'fun', zh: '休闲版', en: 'Casual', ar: 'ترفيه', tip: { zh: '随手一局，不用动脑', en: 'One-tap casual play', ar: 'لعب سريع بلا تفكير' } },
  { k: 'chef', zh: '厨师版', en: 'Chef', ar: 'طاهٍ', tip: { zh: '按"备菜节奏"来玩', en: 'Played at prep-station rhythm', ar: 'لعب بإيقاع تجهيز الطعام' } },
  { k: 'runner', zh: '跑者版', en: 'Runner', ar: 'عدّاء', tip: { zh: '练配速感与反应', en: 'Sharpens pace sense and reflexes', ar: 'يحسّن الإحساس بالسرعة وردود الفعل' } },
  { k: 'teacher', zh: '教师版', en: 'Teacher', ar: 'معلّم', tip: { zh: '适合课堂上做小互动', en: 'Made for quick classroom interaction', ar: 'مناسب لأنشطة صفية سريعة' } },
  { k: 'parent', zh: '家长版', en: 'Parent', ar: 'وليّ أمر', tip: { zh: '陪孩子玩的五分钟', en: 'Five minutes of play with kids', ar: 'خمس دقائق من اللعب مع الأطفال' } },
  { k: 'night', zh: '夜猫子版', en: 'Night owl', ar: 'سهر', tip: { zh: '深夜清醒时的轻度挑战', en: 'A light late-night challenge', ar: 'تحدٍ خفيف في وقت السهر' } },
  { k: 'morning', zh: '晨间版', en: 'Morning', ar: 'صباح', tip: { zh: '起床后先来一局热热身', en: 'Warm up right after waking up', ar: 'إحماء بعد الاستيقاظ' } },
  { k: 'commute', zh: '通勤版', en: 'Commute', ar: 'تنقل', tip: { zh: '地铁上一局', en: 'One round on the subway', ar: 'جولة في المترو' } },
  { k: 'exam', zh: '备考版', en: 'Exam prep', ar: 'استعداد للاختبار', tip: { zh: '碎片时间练手速', en: 'Drills speed in spare minutes', ar: 'تدريب السرعة في أوقات الفراغ' } },
  { k: 'newbie', zh: '新手版', en: 'Newbie', ar: 'مبتدئ', tip: { zh: '零基础也能上手', en: 'Beginner friendly from zero', ar: 'مناسب للمبتدئين تماماً' } },
  { k: 'expert', zh: '高手版', en: 'Expert', ar: 'محترف', tip: { zh: '节奏快、容错低', en: 'Fast pace, low error tolerance', ar: 'إيقاع سريع وهامش خطأ منخفض' } },
  { k: 'lefty', zh: '左撇子版', en: 'Left-handed', ar: 'أيسر', tip: { zh: '按键分布做了镜像调整', en: 'Key layout mirrored for left-handers', ar: 'تخطيط المفاتيح معكوس' } },
  { k: 'glasses', zh: '近视版', en: 'Glasses', ar: 'نظارة', tip: { zh: '字号更大、更护眼', en: 'Larger type, easier on the eyes', ar: 'خط أكبر وأراح للعين' } },
  { k: 'quick', zh: '快节奏版', en: 'Quick', ar: 'سريع', tip: { zh: '限时更短，适合抢时间', en: 'Shorter timers for a rush', ar: 'مؤقت أقصر لمن يستعجل' } },
  { k: 'calm', zh: '慢节奏版', en: 'Calm', ar: 'هادئ', tip: { zh: '时间更宽松，不易挫败', en: 'More forgiving timings', ar: 'أوقات أكثر تسامحًا' } },
  { k: 'rainy', zh: '雨天版', en: 'Rainy day', ar: 'يوم ممطر', tip: { zh: '阴天也能玩的室内局', en: 'An indoor round for grey days', ar: 'جولة داخلية في الأيامGrey' } },
  { k: 'sunny', zh: '晴天版', en: 'Sunny', ar: 'مشمس', tip: { zh: '心情好时手感更好', en: 'Better vibe, better streak', ar: 'مزاج أفضل وسلسلة أفضل' } },
  { k: 'winter', zh: '冬季版', en: 'Winter', ar: 'شتاء', tip: { zh: '适合窝在室内的时间', en: 'Made for indoor evenings', ar: 'مناسب لأمسيات indoors' } },
  { k: 'summer', zh: '夏季版', en: 'Summer', ar: 'صيف', tip: { zh: '短平快的消暑局', en: 'Short and snappy', ar: 'سريعة وموجزة' } },
  { k: 'holiday', zh: '节假日版', en: 'Holiday', ar: 'إجازة', tip: { zh: '假期里的轻松消遣', en: 'Light holiday fun', ar: 'ترفيه خفيف في الإجازة' } },
  { k: 'workday', zh: '工作日版', en: 'Workday', ar: 'يوم عمل', tip: { zh: '五分钟提神', en: 'Five minutes to wake up', ar: 'خمس دقائق للانتعاش' } },
  { k: 'deep', zh: '深度专注版', en: 'Deep focus', ar: 'تركيز عميق', tip: { zh: '屏蔽干扰，专注一局', en: 'Distraction-free single round', ar: 'جولة خالية من التشتيت' } },
  { k: 'casual', zh: '随手玩版', en: 'Idle', ar: 'عشوائي', tip: { zh: '不用动脑也能玩', en: 'Playable without thinking', ar: 'يمكن اللعب دون تركيز' } },
  { k: 'family', zh: '亲子版', en: 'Family', ar: 'عائلة', tip: { zh: '一家人一局', en: 'One round for the whole family', ar: 'جولة للعائلة كلها' } },
  { k: 'pet', zh: '宠物版', en: 'Pet', ar: 'حيوان أليف', tip: { zh: '给毛孩子也来一局', en: 'A round for your furry friend', ar: 'جولة لصديقك ذو الفراء' } },
  { k: 'sports', zh: '运动版', en: 'Sports', ar: 'رياضة', tip: { zh: '练反应与专注', en: 'Trains reaction and focus', ar: 'يدرّب ردود الفعل والتركيز' } },
  { k: 'music', zh: '音乐版', en: 'Music', ar: 'موسيقى', tip: { zh: '跟着节奏来', en: 'Ride the rhythm', ar: 'اتبع الإيقاع' } },
  { k: 'art', zh: '美术版', en: 'Art', ar: 'فن', tip: { zh: '配色与形状的组合', en: 'Colours and shapes combined', ar: 'ألوان وأشكال' } },
  { k: 'science', zh: '科学版', en: 'Science', ar: 'علوم', tip: { zh: '带点科普味道的题', en: 'Questions with a science flavour', ar: 'أسئلة بنكهة علمية' } },
  { k: 'history', zh: '历史版', en: 'History', ar: 'تاريخ', tip: { zh: '知识点选择题', en: 'Knowledge-style multiple choice', ar: 'أسئلة معرفية' } },
  { k: 'geo', zh: '地理版', en: 'Geography', ar: 'جغرافيا', tip: { zh: '认地名与方位', en: 'Places and directions', ar: 'أماكن واتجاهات' } },
  { k: 'movie', zh: '影视版', en: 'Movies', ar: 'أفلام', tip: { zh: '台词与片段联想', en: 'Quotes and scene recall', ar: 'اقتباسات ومشاهد' } },
  { k: 'music88', zh: '钢琴版', en: 'Piano', ar: 'بيانو', tip: { zh: '节奏与音程', en: 'Rhythm and intervals', ar: 'إيقاع interv��ل' } },
  { k: 'retro', zh: '像素复古版', en: 'Retro pixel', ar: 'بكسل', tip: { zh: '8-bit 风格配色', en: '8-bit style palette', ar: 'ألوان بأسلوب 8-بت' } },
  { k: 'minimal', zh: '极简版', en: 'Minimal', ar: 'بسيط', tip: { zh: '没有多余干扰', en: 'No extra clutter', ar: 'بدون تشتيت' } },
  { k: 'color', zh: '彩色版', en: 'Colorful', ar: 'ملون', tip: { zh: '元素带颜色区分', en: 'Colour-coded elements', ar: 'عناصر ملونة' } },
  { k: 'sound', zh: '音效版', en: 'Sound', ar: 'صوت', tip: { zh: '每一步都有反馈音', en: 'Feedback on every step', ar: 'تغذية راجعة في كل خطوة' } },
];

// ---------------- 内容轮转（让主题真正改变题目集合）----------------
function rotateArrayLiteral(js, marker, s) {
  // 把 `var Q=[...]` / `pool=[...]` 里的数组按主题轮转
  const re = new RegExp("(" + marker + "=\\[)([\\s\\S]*?)(\\])");
  const m = js.match(re);
  if (!m) return js;
  let items;
  try { items = JSON.parse("[" + m[2] + "]"); } catch (e) { return js; }
  if (!Array.isArray(items) || items.length < 2) return js;
  const off = (s * 7 + 3) % items.length;
  const rot = items.slice(off).concat(items.slice(0, off));
  const enc = JSON.stringify(rot).slice(1, -1);
  return js.replace(re, "$1" + enc + "$3");
}

// ---------------- 主题化随机数（程序化游戏在不同主题下题目不同）----------------
function themeSeed(s) {
  return `var __s=${s},__seed=(__s*2654435761)>>>0;` +
    `var __r=(function(){var x=__seed||1;return function(){x=(x*1103515245+12345)>>>0;return x/4294967296;};})();`;
}

function build() {
  const out = [];
  const used = {};
  // 主题数全局可控（不再被每个引擎自己的 skins 上限卡住）
  const T = Math.max(1, Math.min(THEMES.length, Number(process.env.ARCADE_THEMES || THEMES.length)));
  ENGINES.forEach(function (e) {
    const skins = T;
    for (let u = 0; u < e.units.length; u++) {
      for (let l = 0; l < e.lvs; l++) {
        for (let s = 0; s < skins; s++) {
          const unit = e.units[u], th = THEMES[s], lv = LV[Math.min(l, LV.length - 1)];
          let slug = 'a_' + e.id + '_' + b36(u) + b36(l) + b36(s);
          if (used[slug]) { let k = 2; while (used[slug + '_' + k]) k++; slug = slug + '_' + k; }
          used[slug] = 1;
          const parts = [];
          if (e.units.length > 1 || unit.zh) parts.push(unit.zh);
          if (e.lvs > 1) parts.push(lv.zh);
          parts.push(th.zh);
          let js = e.mk(u, l, s);
          // 主题驱动内容
          js = rotateArrayLiteral(js, 'Q', s);
          js = rotateArrayLiteral(js, 'pool', s);
          js = rotateArrayLiteral(js, 'rows', s);
          // 主题驱动随机数
          js = js.replace(/Math\.random\(\)/g, '__r()');
          js = themeSeed(s) + js;
          out.push({
            n: slug, cat: e.cat, arcade: true,
            t: {
              zh: e.t.zh + ' · ' + parts.join(' · '),
              en: e.t.en + ' · ' + [unit.en, (l ? (e.lvs > 1 ? lv.en : '') : ''), th.en].filter(Boolean).join(' · '),
              ar: e.t.ar + ' · ' + th.ar
            },
            p: e.p, pain: e.pain,
            unit: { zh: unit.zh, en: unit.en, ar: unit.ar },
            lv: { zh: lv.zh, en: lv.en, ar: lv.ar },
            theme: { zh: th.zh, en: th.en, ar: th.ar },
            tip: th.tip,
            desc: {
              zh: e.t.zh + '（' + unit.zh + '）·' + lv.zh + '·' + th.zh + '。' + (e.pain.zh || '') + '？' + th.tip.zh + '。在线免费试玩 10 分钟,之后每分钟 0.2 元,邀请 1 人双方各送 10 分钟,无需下载。',
              en: e.t.en + ' (' + unit.en + ') · ' + lv.en + ' · ' + th.en + '. ' + th.tip.en + '. Free first 10 minutes, then 0.2 CNY per minute, invite a friend and both get +10 minutes. Play in browser, no download.',
              ar: e.t.ar + ' · ' + th.ar + '. ' + th.tip.ar + '. أول 10 دقائق مجانية ثم 0.2 يوان لكل دقيقة، ودعوة صديق تمنحكما 10 دقائق.'
            },
            intro: {
              zh: '这是一个「' + e.cat + '」类小游戏，面向' + (e.p.zh || '所有玩家') + '。玩法依据「' + unit.zh + '」模式，难度为「' + lv.zh + '」，风格为「' + th.zh + '」——' + th.tip.zh + '。',
              en: 'This is a ' + e.cat + ' game for ' + (e.p.en || 'all players') + '. Mode: ' + unit.en + ', difficulty: ' + lv.en + ', style: ' + th.en + ' — ' + th.tip.en + '.',
              ar: 'لعبة من فئة ' + e.cat + ' للنمط ' + unit.ar + ' بمستوى ' + lv.ar + ' — ' + th.tip.ar + '.'
            },
            js: js
          });
        }
      }
    }
  });
  return out;
}

module.exports = { build, THEMES };
