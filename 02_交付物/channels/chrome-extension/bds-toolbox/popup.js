// BDS Toolbox popup — instant fuzzy search over 508 micro-calculators
const TOOLS = require_or_load('tools.json');
const BASE = 'https://tools.highkingflower.com/';
const I18N = {
  en: { sub: '508 micro-calculators. Free 10 uses per tool.', ph: 'Search a pain… e.g. resume, exam, rent', foot: 'Full site:', pricing: 'Pricing', none: 'No match — try fewer letters', count: n => n + ' tools' },
  zh: { sub: '508 个微工具，每个免费 10 次。', ph: '搜痛点…如：简历、考试、房租', foot: '完整站点：', pricing: '收费规则', none: '没找到——少打几个字试试', count: n => n + ' 个工具' },
  ar: { sub: '508 أداة صغيرة، 10 استخدامات مجانية لكل أداة.', ph: 'ابحث… مثل: سيرة، امتحان، إيجار', foot: 'الموقع الكامل:', pricing: 'الأسعار', none: 'لا نتائج — جرّب أحرفًا أقل', count: n => n + ' أداة' },
  fr: { sub: '508 micro-outils. 10 essais gratuits par outil.', ph: 'Cherchez… ex. CV, examen, loyer', foot: 'Site complet :', pricing: 'Tarifs', none: 'Aucun résultat — essayez moins de lettres', count: n => n + ' outils' },
  de: { sub: '508 Micro-Tools. 10 Gratis-Nutzungen pro Tool.', ph: 'Suchen… z.B. Lebenslauf, Prüfung, Miete', foot: 'Vollständige Seite:', pricing: 'Preise', none: 'Kein Treffer — weniger Buchstaben versuchen', count: n => n + ' Tools' }
};
function lang() {
  let l = localStorage.getItem('bds_lang');
  if (l && I18N[l]) return l;
  const n = (navigator.language || 'zh').toLowerCase();
  for (const k of ['zh', 'ar', 'fr', 'de']) if (n.indexOf(k) === 0) return k;
  return 'en';
}
function require_or_load(f) { /* tools.json injected as JSON via fetch below */ return window.__TOOLS || []; }

const list = document.getElementById('list');
const q = document.getElementById('q');
const count = document.getElementById('count');
const L = I18N[lang()];
document.querySelector('.sub').textContent = L.sub;
document.querySelector('footer [data-i=foot]').textContent = L.foot;
document.querySelector('footer [data-i=pricing]').textContent = L.pricing;
q.placeholder = L.ph;

function norm(s) { return (s || '').toLowerCase().replace(/\s+/g, ''); }
function render(items) {
  list.innerHTML = '';
  if (!items.length) { list.innerHTML = '<div class="empty">' + L.none + '</div>'; count.textContent = L.count(0); return; }
  const frag = document.createDocumentFragment();
  for (const it of items.slice(0, 30)) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = BASE + it.u;
    a.target = '_blank';
    const b = document.createElement('b'); b.textContent = it.t;
    const s = document.createElement('span'); s.textContent = it.d || '';
    a.appendChild(b); a.appendChild(s); li.appendChild(a); frag.appendChild(li);
  }
  list.appendChild(frag);
  count.textContent = L.count(items.length);
}
function search() {
  const v = norm(q.value);
  if (!v) { render(TOOLS.slice(0, 30)); return; }
  render(TOOLS.filter(t => norm(t.t).includes(v) || norm(t.d).includes(v) || norm(t.u).includes(v)));
}
q.addEventListener('input', search);
q.addEventListener('keydown', e => {
  if (e.key === 'Enter') { const first = list.querySelector('a'); if (first) { chrome.tabs ? chrome.tabs.create({ url: first.href }) : window.open(first.href); } }
});
// tools.json loaded as a module-level global via <script> injection in manifest-less MV3? simplest: fetch bundled file
fetch(chrome.runtime.getURL('tools.json')).then(r => r.json()).then(j => { window.__TOOLS = j; TOOLS.length = 0; TOOLS.push(...j); search(); });
search();
