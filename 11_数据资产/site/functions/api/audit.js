// 免费 GEO 体检 · Cloudflare Pages Function
// 与 01_引擎/geo_health.py 同口径，但在 Cloudflare 边缘运行 ——
// 这是关键：pages.dev 在大陆不被 DNS 污染（workers.dev 被封），
// 所以这条路让「免费体检」按钮在上海也能用，且完全不需要 SSH。

const UA = "Mozilla/5.0 (compatible; GEOAudit/1.0; +free-visibility-check)";
const BROWSER_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36";

const AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Bytespider", "Baiduspider", "Google-Extended"];

const INDUSTRY_RULES = [
  ["口腔","口腔医疗"],["齿科","口腔医疗"],["牙科","口腔医疗"],["诊所","口腔医疗"],["医院","医疗健康"],
  ["装饰","装修装饰"],["装修","装修装饰"],["建材","装修装饰"],
  ["设计","设计创意"],["广告","营销传媒"],
  ["教育","教育培训"],["培训","教育培训"],["学校","教育培训"],["编程","教育培训"],["少儿","教育培训"],["早教","教育培训"],
  ["律师","法律服务"],["法律","法律服务"],["事务所","法律服务"],
  ["财税","财税服务"],["会计","财税服务"],["税务","财税服务"],
  ["科技","软件科技"],["软件","软件科技"],["信息","软件科技"],
  ["贸易","跨境贸易"],["外贸","跨境贸易"],["跨境","跨境贸易"],
  ["物流","物流供应链"],["供应链","物流供应链"],["货运","物流供应链"],
  ["制造","工业制造"],["机械","工业制造"],["精密","工业制造"],["光电","工业制造"],["电子","工业制造"],["化工","工业制造"],
  ["婚礼","本地生活"],["婚庆","本地生活"],["摄影","本地生活"],["瑜伽","本地生活"],["健身","本地生活"],["宠物","本地生活"],
  ["汽修","汽车服务"],["汽车","汽车服务"],
  ["文旅","文旅服务"],["旅游","文旅服务"],
  ["餐饮","餐饮服务"],["食品","餐饮服务"],
  ["实业","综合实业"],["集团","综合实业"],
];

function guessIndustry(name) {
  for (const [kw, ind] of INDUSTRY_RULES) if (name.includes(kw)) return ind;
  return "其他";
}

function pageTitle(html) {
  const m = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  return m ? m[1].replace(/\s+/g, " ").trim().slice(0, 80) : "";
}

function nodes(o) {
  if (Array.isArray(o)) return o.filter((x) => x && typeof x === "object");
  if (o && typeof o === "object") {
    if (Array.isArray(o["@graph"])) return o["@graph"].filter((x) => x && typeof x === "object");
    return [o];
  }
  return [];
}

async function fetchOnce(url, ua) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 15000);
  try {
    const r = await fetch(url, {
      headers: {
        "User-Agent": ua,
        Accept: "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
      },
      redirect: "follow",
      signal: ctrl.signal,
    });
    const buf = await r.arrayBuffer();
    return { status: r.status, body: buf };
  } catch (e) {
    return { status: 0, body: new ArrayBuffer(0), cert: /certificate|SSL|TLS/i.test(String(e)) };
  } finally {
    clearTimeout(t);
  }
}

async function get(url) {
  let last = { status: 0, body: new ArrayBuffer(0) };
  for (const ua of [UA, BROWSER_UA]) {
    const r = await fetchOnce(url, ua);
    if (r.status === 200 && r.body.byteLength > 0) return r;
    last = r;
    if (r.cert) return { status: -1, body: new ArrayBuffer(0) };
  }
  return last;
}

function decode(buf) {
  try {
    return new TextDecoder("utf-8").decode(buf);
  } catch {
    return "";
  }
}

async function probe(siteBase, base, fname) {
  let r = await get(siteBase + "/" + fname);
  if (r.status === 200 && r.body.byteLength > 0) return r;
  if (siteBase !== base) {
    const r2 = await get(base + "/" + fname);
    if (r2.status === 200 && r2.body.byteLength > 0) return r2;
  }
  return r;
}

function grade(score) {
  return score >= 80 ? "优" : score >= 55 ? "中" : "差";
}

export async function onRequestGet(context) {
  const { request } = context;
  const target = new URL(request.url).searchParams.get("url") || "";
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "public, max-age=300",
  };
  if (!target) return new Response(JSON.stringify({ error: "缺少 url 参数" }), { status: 400, headers });

  let url = target.trim();
  if (!/^https?:\/\//i.test(url)) url = "http://" + url;
  let u;
  try {
    u = new URL(url);
  } catch {
    return new Response(JSON.stringify({ error: "网址格式不正确" }), { status: 400, headers });
  }
  const host = u.host;
  const base = `${u.protocol}//${u.host}`;
  const sitePath = u.pathname.endsWith("/") ? u.pathname : u.pathname.replace(/\/[^/]*$/, "/");
  const siteBase = sitePath.replace(/^\/|\/$/g, "") ? `${base}/${sitePath.replace(/^\/|\/$/g, "")}/` : base;

  // robots.txt
  const rob = await probe(siteBase, base, "robots.txt");
  const robotsText = rob.status === 200 ? decode(rob.body) : "";
  const blocked = [];
  if (robotsText) {
    for (const bot of AI_BOTS) {
      const re = new RegExp(`^user-agent:\\s*${bot}\\s*$([\\s\\S]*?)(?=^\\s*user-agent:|$)`, "im");
      const m = robotsText.match(re);
      if (m) {
        const dis = [...m[1].matchAll(/^\s*disallow:\s*(\S*)/gim)].map((x) => x[1].trim());
        if (dis.some((d) => d === "/" || d === "")) blocked.push(bot);
      }
    }
  }
  const robots = { exists: rob.status === 200, blocked, total: AI_BOTS.length };

  // llms.txt
  const lm = await probe(siteBase, base, "llms.txt");
  const llms = { exists: lm.status === 200 && lm.body.byteLength > 30 };

  // 首页
  const page = await get(url);
  const html = page.body.byteLength ? decode(page.body) : "";
  const http = page.status;
  const name = pageTitle(html) || host;
  const industry = guessIndustry(name);

  // 反爬/风控页识别。阿里云 WAF 会返回 200 + JS 挑战页；B 站这类返 412 +
  // 「出错啦」；很多站对机器人返 403。这些都不是官网内容，拿去打分就是诬告。
  // 正经做法：标「需人工复核」，既不冤枉客户，也不假装我们抓到了。
  const antiBot =
    /(aliyun_waf_\w+|captcha-delivery\.com|_captcha|请开启.{0,6}JavaScript|just a moment|checking your browser|cf-browser-verification|安全验证|滑动验证|出错啦|Access Denied|Forbidden|人机验证|请稍候)/i
      .test(html.slice(0, 6000));
  const blockedStatus = [401, 403, 405, 406, 412, 429, 451, 503].includes(http);
  const challenge = antiBot || blockedStatus;
  // 520/521/522 加一个几十字节的回源失败占位页不是官网。
  const looksOriginError = http >= 500 && page.body.byteLength < 1024;
  const reachable = {
    ok: http > 0 && page.body.byteLength >= 256 && !looksOriginError,
    bytes: page.body.byteLength,
    waf: challenge,
  };

  const result = {
    url, host, name, industry, http,
    checks: { robots, llms, reachable },
  };

  if (!reachable.ok) {
    result.score = 0;
    result.unreachable = true;
    if (http === -1) {
      result.grade = "证书故障";
      result.blockers = ["官网 HTTPS 证书链校验不通过。主流 AI 爬虫在握手阶段就会放弃，等于直接不收录 —— 这是真问题，建议优先修复证书链。"];
    } else {
      result.grade = "无法访问";
      result.blockers = [`探测端未取得任何响应（HTTP ${http}），AI 大概率也抓不到；建议先在境内网络复测可达性，确认不是我们这边网络的问题`];
    }
    return new Response(JSON.stringify(result), { status: 200, headers });
  }

  if (challenge) {
    result.score = 0;
    result.grade = "需人工复核";
    result.waf_blocked = true;
    result.blockers = ["站点启用了反爬验证（WAF/验证码），自动探测拿不到真实页面。这不代表该站有问题，需人工用浏览器打开确认后再判分。"];
    return new Response(JSON.stringify(result), { status: 200, headers });
  }

  // JSON-LD
  const types = [];
  const re = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let mm;
  while ((mm = re.exec(html))) {
    try {
      const obj = JSON.parse(mm[1].trim());
      for (const o of nodes(obj)) {
        const t = o["@type"];
        if (t) types.push(...(Array.isArray(t) ? t : [t]));
      }
    } catch { /* 忽略坏 JSON */ }
  }
  const schema = {
    exists: types.length > 0,
    types: [...new Set(types.map(String))].sort(),
    has_org: types.some((t) => /Organization|LocalBusiness|MedicalBusiness/.test(String(t))),
    has_faq: types.some((t) => /FAQ/.test(String(t))),
  };

  const sm = await probe(siteBase, base, "sitemap.xml");
  const sitemap = { exists: sm.status === 200 };

  const faq = { exists: /(FAQ|常见问题|问答|Q&A)/i.test(html) };
  const tm = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const dm = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([\s\S]*?)["']/i);
  const meta = {
    title: tm ? tm[1].trim().slice(0, 120) : "",
    has_title: !!(tm && tm[1].trim()),
    has_description: !!dm,
  };

  result.checks.schema = schema;
  result.checks.sitemap = sitemap;
  result.checks.faq = faq;
  result.checks.meta = meta;

  let score = 0;
  const why = [];
  if (robots.blocked.length) why.push("robots.txt 明确拦截了 AI 爬虫：" + robots.blocked.join("、"));
  else if (robots.exists) score += 30;
  else { score += 18; why.push("没有 robots.txt，未明确放行 AI 爬虫"); }

  if (schema.exists && schema.has_org) score += 25;
  else if (schema.exists) { score += 12; why.push("有结构化数据但没有实体（Organization/LocalBusiness）"); }
  else why.push("没有 JSON-LD 结构化数据，AI 难以识别你是谁");

  if (schema.has_faq) score += 15; else why.push("没有 FAQ/问答区块，AI 无从抽取问答对");
  if (llms.exists) score += 10; else why.push("没有 llms.txt（给大模型的站点说明书）");
  if (meta.has_description) score += 10; else why.push("缺少 meta description");
  if (sitemap.exists) score += 10; else why.push("没有 sitemap.xml");

  result.score = Math.min(score, 100);
  result.grade = grade(result.score);
  result.blockers = why;
  return new Response(JSON.stringify(result), { status: 200, headers });
}
