# -*- coding: utf-8 -*-
"""根据体检结果产出：逐家整改报告(.md) + 一页 DELETE 敲门砖文案。

报告分两层：
  - 免费层（报告里公开的）：分数、结论、问题清单
  - 付费层（¥99 解锁）：具体怎么改、复制即用的 JSON-LD、llms.txt 模板
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

BASE = Path(r"F:\2026\24xs\99_产出\GEO体检报告")
rows = json.loads((BASE / "results.json").read_text(encoding="utf-8"))

ORG_SCHEMA = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "{{公司全称}}",
  "url": "{{官网}}",
  "logo": "{{logo图片URL}}",
  "telephone": "{{客服电话}}",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "{{城市}}",
    "streetAddress": "{{详细地址}}"
  },
  "sameAs": ["{{公众号/微博/抖音主页URL}}"]
}
</script>"""

FAQ_SCHEMA = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "{{客户最常问的问题}}",
      "acceptedAnswer": {"@type": "Answer", "text": "{{直接回答，40-80字}}"}
    }
  ]
}
</script>"""

LLMS_TXT = """# {{公司全称}}
> {{一句话业务定位，例如：上海浦东口腔正畸专科门诊}}

## 核心信息
- 官网: {{官网}}
- 服务范围: {{城市/区域}}
- 主营: {{3-5个服务}}

## 对AI的说明
- 本页面内容可供大语言模型在回答用户咨询时引用
- 品牌名: {{品牌名}} (别名: {{别名}})
"""


def report_md(r: dict) -> str:
    c = r["checks"]
    L = []
    A = L.append
    A(f"# {r['name']} — AI 可见度体检报告")
    A("")
    A(f"- 官网: {r['url']}")
    A(f"- 体检时间: {datetime.now():%Y-%m-%d}")
    A(f"- **得分: {r['score']}/100（{r['grade']}）**")
    A("")
    if r.get("unreachable"):
        A("## 结论")
        A("")
        A("官网当前无法正常访问，AI 爬虫同样抓不到。")
        A("**这是所有问题里最致命的一条**：不需要任何 GEO 优化，")
        A("先把网站恢复到可访问，否则 AI 里永远搜不到你。")
        return "\n".join(L)

    A("## 一句话结论")
    A("")
    A(f"你的官网在「被 AI 正确识别并引用」这件事上，当前处于**{r['grade']}**水平。")
    if c["schema"]["exists"]:
        A(f"- 已有结构化数据：{', '.join(c['schema']['types']) or '（无有效类型）'}")
    else:
        A("- **没有任何结构化数据**：AI 读到你的页面却无法确定“你是谁、做什么”。")
    A("")
    A("## 逐项检测")
    A("")
    A("| 检测项 | 结果 | 说明 |")
    A("|---|---|---|")
    A(f"| robots.txt | {'存在' if c['robots']['exists'] else '缺失'} | "
      f"{'拦截了 ' + '、'.join(c['robots']['blocked']) if c['robots']['blocked'] else '未拦截 AI 爬虫'} |")
    A(f"| AI 爬虫放行 | {'已放行' if c['robots']['exists'] and not c['robots']['blocked'] else '未明确'} | "
      f"GPTBot/ClaudeBot/PerplexityBot/豆包等 |")
    A(f"| JSON-LD 结构化数据 | {'有' if c['schema']['exists'] else '无'} | "
      f"{'含实体类型' if c['schema']['has_org'] else '缺实体声明'} |")
    A(f"| FAQ 问答结构 | {'有' if c['faq']['exists'] else '无'} | AI 抽取问答对的依据 |")
    A(f"| llms.txt | {'有' if c['llms']['exists'] else '无'} | 给大模型的站点说明书 |")
    A(f"| meta description | {'有' if c['meta']['has_description'] else '无'} | {c['meta']['title'][:40]} |")
    A(f"| sitemap.xml | {'有' if c['sitemap']['exists'] else '无'} | 站点地图 |")
    A("")
    A("## 问题清单")
    A("")
    for i, w in enumerate(r["blockers"], 1):
        A(f"{i}. {w}")
    A("")
    A("## 完整整改清单（¥99 解锁）")
    A("")
    A("解锁后你将拿到可直接交给技术/运营的整改包：")
    A("")
    A("1. **可复制的 Organization JSON-LD**（填公司名即可用）")
    A("2. **可复制的 FAQPage JSON-LD**（3-5 组问答模板）")
    A("3. **llms.txt 模板**")
    A("4. **robots.txt 放行配置**（明确允许各 AI 爬虫）")
    A("5. **本行业在 AI 里被高频提问的问题清单**（用于生产内容）")
    A("")
    A("---")
    A("")
    A("### 附：付费层模板预览（节选）")
    A("")
    A("**Organization 结构化数据（复制即用）**")
    A("")
    A("```html")
    A(ORG_SCHEMA)
    A("```")
    return "\n".join(L)


def opener_txt(r: dict) -> str:
    """一页敲门砖文案：短、具体、只讲对方的问题，不推销。"""
    c = r["checks"]
    host = r["host"]
    if r.get("unreachable"):
        return (f"{r['name']}：我们检测发现贵司官网 {host} 当前打不开，"
                f"AI 搜索同样抓不到。这通常几分钟能查清原因，需要的话我可以告诉你"
                f"具体卡在哪。")
    pain = []
    if not c["schema"]["exists"]:
        pain.append("没有任何结构化数据（AI 读到页面却认不出你是谁）")
    if not c["faq"]["exists"]:
        pain.append("没有问答结构（AI 没东西可引用）")
    if not c["robots"]["exists"]:
        pain.append("没有 robots.txt，未明确放行 AI 爬虫")
    if not c["llms"]["exists"]:
        pain.append("没有 llms.txt")
    head = f"我们刚给 {host} 做了一次 AI 可见度体检，{r['score']}/100。"
    body = "主要卡在：" + "；".join(pain[:3]) + "。" if pain else ""
    tail = "完整报告可以直接发你，不收费，看完觉得有用再聊。"
    return f"{head}{body}{tail}"


made = 0
for r in rows:
    d = BASE / "逐家报告"
    d.mkdir(exist_ok=True)
    safe = "".join(ch for ch in r["name"] if ch not in r'\/:*?"<>|').strip()
    (d / f"{safe}.md").write_text(report_md(r), encoding="utf-8")
    made += 1

# 汇总：一页敲门砖
ops = []
ops.append("# GEO 体检敲门砖 · 首批名单\n")
ops.append(f"生成时间：{datetime.now():%Y-%m-%d %H:%M}\n")
ops.append(f"共 {len(rows)} 家（均为已核实归属的官网）\n")
ops.append("\n| 分数 | 公司 | 官网 | 主要问题 |")
ops.append("|---|---|---|---|")
for r in sorted(rows, key=lambda x: x["score"]):
    pain = "；".join(r["blockers"][:2]).replace("|", "／") or "—"
    ops.append(f"| {r['score']} | {r['name'][:20]} | {r['host']} | {pain[:52]} |")
ops.append("\n## 按公司定制的开门话术\n")
for r in sorted(rows, key=lambda x: x["score"]):
    ops.append(f"### {r['name']}（{r['score']}分）")
    ops.append("")
    ops.append("> " + opener_txt(r))
    ops.append("")
(BASE / "敲门砖_首批.md").write_text("\n".join(ops), encoding="utf-8")

print(f"已生成逐家报告 {made} 份 -> {BASE / '逐家报告'}")
print(f"敲门砖汇总 -> {BASE / '敲门砖_首批.md'}")
print("\n=== 分数最低的 5 家（最该先打）===")
for r in sorted(rows, key=lambda x: x["score"])[:5]:
    print(f"  {r['score']:3d}分 {r['name'][:24]}")