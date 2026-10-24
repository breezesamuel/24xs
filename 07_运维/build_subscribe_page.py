# -*- coding: utf-8 -*-
"""从 subscription.py 生成 subscribe.html。

页面文案不手写价格 —— 改价只改 subscription.py，这里重新生成一遍，
页面和后台结算口径永远一致。手写的话迟早会出现"页面 60、后台 150"。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

eng = next(Path(r"F:\2026\24xs").glob("01_*"))
sys.path.insert(0, str(eng))
sys.stdout.reconfigure(encoding="utf-8")

import subscription as S  # noqa: E402

SITE = Path(r"F:\2026\24xs\10_官网")
OUT = SITE / "subscribe.html"

P = S.public_pricing()
cn, en = P["plans"]["cn"], P["plans"]["en"]

CONSULT_LINE = (
    "企业级 GEO 诊断与整改交付（人工，含策略、页面改造、复测）"
    "属于咨询项目，走公司对公并开具发票，不在本订阅范围内。"
)


def plan_cards(lang: str, d: dict) -> str:
    out = []
    order = ("month", "quarter", "year")
    for i, period in enumerate(order):
        it = next(x for x in d["items"] if x["period"] == period)
        price = f"{d['symbol']}{it['price']}"
        if lang == "cn":
            price = f"{d['symbol']}{it['price']:g}"
            sub = f"{it['label']} · {it['uses']} 次快检"
            cta = "选择" + it["label"]
        else:
            price = f"{d['symbol']}{it['price']:g}"
            sub = f"{it['label']} · {it['uses']} scans"
            cta = "Choose " + it["label"]
        best = ' <span class="tag">最划算</span>' if period == "year" else ""
        out.append(f"""      <div class="plan{' best' if period == 'year' else ''}">
        <div class="pl">{it['label']}{best}</div>
        <div class="pp">{price}<small>/{'年' if lang == 'cn' else 'yr' if period == 'year' else ('季' if lang == 'cn' else 'qtr') if period == 'quarter' else ('月' if lang == 'cn' else 'mo')}</small></div>
        <div class="pu">{sub}</div>
        <button class="pick" data-plan="{period}" data-lang="{lang}">{cta}</button>
      </div>""")
    return "\n".join(out)


def tier_list(lang: str) -> str:
    out = []
    for t in S.REFERRAL_TIERS:
        if lang == "cn":
            title, reward = t["title_zh"], t["reward_zh"]
        else:
            title, reward = t["title_en"], t["reward_en"]
        out.append(f"""      <li><b>{title}</b><span>{reward}</span></li>""")
    return "\n".join(out)


PAY = P["pay_alipay"]

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>订阅套餐 · AI 搜索可见度快检</title>
<meta name="description" content="自动化 AI 搜索可见度快检订阅：注册赠送 {P['free_uses']} 次免费使用，按月/季/年付费，支付宝转账开通。">
<link rel="canonical" href="https://geo-audit-24xs.vercel.app/subscribe.html">
<style>
  :root {{ color-scheme: light; --ink:#14161a; --mut:#5c6470; --line:#e6e8ec;
          --brand:#e11d48; --bg:#fff; --soft:#fafbfc; }}
  * {{ box-sizing:border-box }}
  body {{ font:15px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
          color:var(--ink); background:var(--bg); margin:0 }}
  .wrap {{ max-width:960px; margin:0 auto; padding:32px 20px 72px }}
  header {{ border-bottom:3px solid var(--brand); padding-bottom:18px; margin-bottom:28px }}
  h1 {{ font-size:27px; margin:0 0 8px; letter-spacing:-.3px }}
  .sub {{ color:var(--mut); font-size:14.5px }}
  h2 {{ font-size:19px; margin:38px 0 12px; padding-left:11px; border-left:4px solid var(--brand) }}
  h3 {{ font-size:15.5px; margin:22px 0 8px }}
  .free {{ background:#fff5f7; border:1px solid #fecdd6; border-radius:10px;
           padding:14px 18px; margin:18px 0; font-size:14.5px }}
  .free b {{ color:var(--brand) }}
  .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:16px 0 }}
  @media (max-width:720px) {{ .grid {{ grid-template-columns:1fr }} }}
  .plan {{ border:1px solid var(--line); border-radius:12px; padding:20px 18px; background:var(--soft) }}
  .plan.best {{ border-color:var(--brand); background:#fff }}
  .pl {{ font-size:14px; color:var(--mut) }}
  .pp {{ font-size:31px; font-weight:700; margin:6px 0 2px; letter-spacing:-1px }}
  .pp small {{ font-size:14px; font-weight:400; color:var(--mut); letter-spacing:0 }}
  .pu {{ font-size:13.5px; color:var(--mut); margin-bottom:14px }}
  .tag {{ font-size:11px; background:var(--brand); color:#fff; border-radius:20px;
          padding:2px 8px; vertical-align:middle; letter-spacing:0 }}
  button.pick {{ width:100%; padding:10px; border:1px solid var(--brand); background:#fff;
                 color:var(--brand); border-radius:8px; font-size:14px; cursor:pointer }}
  button.pick:hover {{ background:var(--brand); color:#fff }}
  table {{ border-collapse:collapse; width:100%; font-size:14px; margin:12px 0 }}
  td,th {{ border:1px solid var(--line); padding:9px 11px; text-align:left }}
  th {{ background:var(--soft) }}
  ul.tiers {{ list-style:none; padding:0; margin:12px 0 }}
  ul.tiers li {{ border-left:3px solid var(--brand); padding:8px 0 8px 14px; margin:9px 0 }}
  ul.tiers li b {{ display:block; font-size:14.5px }}
  ul.tiers li span {{ color:var(--mut); font-size:13.5px }}
  form {{ border:1px solid var(--line); border-radius:12px; padding:20px; margin:16px 0; background:var(--soft) }}
  label {{ display:block; font-size:13.5px; color:var(--mut); margin:12px 0 4px }}
  input,select {{ width:100%; padding:9px 11px; border:1px solid var(--line);
                  border-radius:8px; font-size:14px; font-family:inherit; background:#fff }}
  button.go {{ margin-top:16px; padding:11px 20px; background:var(--brand); color:#fff;
               border:0; border-radius:8px; font-size:15px; cursor:pointer }}
  .paybox {{ background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:16px 18px; margin:14px 0 }}
  .paybox b {{ font-size:17px; font-family:ui-monospace,Menlo,Consolas,monospace }}
  details {{ border:1px solid var(--line); border-radius:10px; padding:12px 16px; margin:10px 0; background:var(--soft) }}
  summary {{ cursor:pointer; font-weight:600; font-size:14.5px }}
  details p,details li {{ font-size:13.5px; color:var(--mut) }}
  .foot {{ margin-top:44px; padding-top:18px; border-top:1px solid var(--line);
           font-size:13px; color:var(--mut) }}
  .note {{ font-size:13px; color:var(--mut) }}
  #msg {{ margin-top:12px; font-size:14px; min-height:20px }}
  .ok {{ color:#15803d }} .er {{ color:#b91c1c }}
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>AI 搜索可见度快检 · 订阅</h1>
  <div class="sub">自动化检测官网结构化数据与问答块，生成可打印报告。<b>纯机器快检，不含人工咨询交付。</b></div>
</header>

<div class="free">
  注册即赠 <b>{P['free_uses']} 次</b>免费快检，用完后可选择套餐继续。
</div>

<h2>套餐 · 中文</h2>
<div class="grid">
{plan_cards("cn", cn)}
</div>

<h2>Plans · English</h2>
<div class="grid">
{plan_cards("en", en)}
</div>

<p class="note">
  同一人同时订阅多个套餐时，按额度最大的一个计算，不叠加。<br>
  额度按订阅时长一次性发放，用完可续费；不自动扣款。
</p>

<h2>推荐奖励</h2>
<ul class="tiers">
{tier_list("cn")}
</ul>
<p class="note">
  奖励按<b>被邀请人实际付费的档位</b>判定，且每位被邀请人只能为其邀请人贡献一次奖励。
  奖励在推荐人账户内直接发放额度，无需另行兑换。
</p>
<p class="note">Referral rewards / 英文说明同中文条款，按被邀请人实付档位判定，每人仅计一次。</p>

<h2>申请开通</h2>
<p class="note">
  支持两种方式：<b>支付宝在线支付</b>（跳转支付宝付款，付完自动核验开通，推荐）
  或 <b>支付宝转账 + 人工确认</b>。两者都不需要支付账号密码，也不需要绑定银行卡。
</p>

<form id="f">
  <label for="email">邮箱（用于接收开通通知与报告）</label>
  <input id="email" name="email" type="email" required placeholder="you@example.com">

  <label for="lang">界面语言</label>
  <select id="lang" name="lang">
    <option value="cn">中文</option>
    <option value="en">English</option>
  </select>

  <label for="plan">选择套餐</label>
  <select id="plan" name="plan">
    <option value="month">中文 ¥60 / 月　　English $9.9 / month</option>
    <option value="quarter">中文 ¥150 / 季　　English $25 / quarter</option>
    <option value="year">中文 ¥500 / 年　　English $99 / year</option>
  </select>

  <label for="ref">推荐码（选填，你的好友推荐码）</label>
  <input id="ref" name="ref" type="text" placeholder="选填">

  <label for="site">要检测的官网（选填）</label>
  <input id="site" name="site" type="text" placeholder="https://">

  <label for="pm">付款方式</label>
  <select id="pm" name="pm">
    <option value="alipay">支付宝在线支付（推荐，付完自动开通）</option>
    <option value="manual">支付宝转账 + 人工确认</option>
  </select>
  <p class="note">
    在线支付以<b>人民币</b>结算（¥60 / ¥150 / ¥500）。
    若需按美元结算英文套餐价，请选"转账 + 人工确认"并注明，我们按当日汇率人工核对。
  </p>

  <button class="go" type="submit">提交申请</button>
  <div id="msg"></div>
</form>

<h2>收款信息</h2>
<div class="paybox">
  <div>支付宝账号（转账到此处）</div>
  <b>{PAY}</b>
  <div class="note" style="margin-top:6px">
    收款人：{S.ENTITY_PERSON}（个人账户，仅用于本订阅的小额收款）<br>
    转账备注请填写你的申请编号，便于核对。
  </div>
</div>

<div class="paybox" style="background:#f8fafc;border-color:var(--line)">
  <div>咨询项目另行对公</div>
  <div class="note" style="margin-top:6px">{CONSULT_LINE}</div>
</div>

<h2>条款</h2>

<details open>
  <summary>服务条款</summary>
  <p>本订阅提供的是<b>自动化机器检测</b>：抓取你提交的公开官网首页，检测结构化数据、问答区块等机器可读信号，输出报告。</p>
  <ul>
    <li>检测结论仅代表被抓取页面在检测时点的机器可读状态，<b>不等于该品牌在 DeepSeek、豆包等 AI 平台的实际排名或被引用情况</b>。</li>
    <li>报告为只读抓取，不登录、不修改对方网站。</li>
    <li>本服务不含人工咨询、策略制定或代运营；需要这些请走咨询项目。</li>
    <li>额度自发放当日起计算，不延期、不转让。</li>
  </ul>
</details>

<details>
  <summary>退款政策</summary>
  <ul>
    <li>尚未开始使用且在付款后 <b>7 个自然日</b>内，可申请全额退款。</li>
    <li>已使用过额度的，退款按剩余未使用额度比例退还。</li>
    <li>推荐奖励发放的额度不支持折现或退款。</li>
    <li>退款走原路，支付宝到账通常 1–3 个工作日。</li>
  </ul>
</details>

<details>
  <summary>隐私政策</summary>
  <ul>
    <li>我们只抓取你主动提交的公开网址，不采集后台、不提交表单、不做端口扫描。</li>
    <li>保存的信息仅限：邮箱、所选套餐、申请编号、检测网址、额度余量。</li>
    <li>不会把你的邮箱或检测数据出售或共享给第三方。</li>
    <li>随时可要求导出或删除你的数据，写信到 <b>460123249@qq.com</b>。</li>
  </ul>
</details>

<div class="foot">
  <a href="/">← 返回首页</a>　|　联系：<a href="mailto:460123249@qq.com">460123249@qq.com</a><br><br>
  检测平台参考：DeepSeek、豆包、通义千问、Kimi、文心一言、元宝。<br>
  主体：{S.ENTITY_COMPANY}。本页价格为人民币与美元双币种标价，汇率按下单当日结算。
</div>

</div>
<script>
document.querySelectorAll(".pick").forEach(function(b){{
  b.addEventListener("click", function(){{
    var p = document.getElementById("plan");
    p.value = b.dataset.plan;
    document.getElementById("lang").value = b.dataset.lang;
    document.getElementById("f").scrollIntoView({{behavior:"smooth"}});
  }});
}});

document.getElementById("f").addEventListener("submit", async function(e){{
  e.preventDefault();
  var msg = document.getElementById("msg");
  msg.className = ""; msg.textContent = "提交中…";
  var data = Object.fromEntries(new FormData(e.target).entries());
  try {{
    if (data.pm === "alipay") {{
      msg.textContent = "正在跳转支付宝…";
      var r2 = await fetch("/api/alipay_pay", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify(data)
      }});
      var j2 = await r2.json();
      if (!r2.ok) throw new Error(j2.error || "支付通道不可用");
      // 跳转到支付宝收银台，付款由支付宝页面完成，本页不接触卡号
      location.href = j2.pay_url;
      return;
    }}
    var r = await fetch("/api/order", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(data)
    }});
    var j = await r.json();
    if (!r.ok) throw new Error(j.error || "提交失败");
    msg.className = "ok";
    msg.innerHTML = "已受理，申请编号 <b>" + j.order_id + "</b>。" +
      "请按下方支付宝账号转账并备注该编号，核对到账后开通。";
    e.target.reset();
  }} catch (err) {{
    msg.className = "er";
    msg.textContent = "提交失败：" + err.message;
  }}
}});

// 付款完成后回来时给一句说明（真正是否到账以服务端核验支付宝结果为准）
if (/(?:^|[?&])paid=1(?:&|$)/.test(location.search)) {{
  var m = document.getElementById("msg");
  m.className = "ok";
  m.textContent = "已收到付款，正在核验并开通，通常 1 分钟内完成。" +
    "开通邮件会发到你填写的邮箱。";
}}
</script>
</body>
</html>
"""

OUT.write_text(HTML, encoding="utf-8")
print("=" * 74)
print(f"已生成 {OUT}  ({len(HTML):,} 字符)")
print("=" * 74)
print(f"  免费额度   {P['free_uses']} 次")
for lg in ("cn", "en"):
    d = P["plans"][lg]
    line = "  {:<4} ".format(lg) + "  ".join(
        f"{i['label']}={d['symbol']}{i['price']:g}/{i['uses']}次"
        for i in d["items"])
    print(line)
print(f"  收款       支付宝 {PAY}（人工确认开通）")
print(f"  规则来源   01_引擎/subscription.py —— 改价只需改这里再重跑本脚本")
print("=" * 74)
