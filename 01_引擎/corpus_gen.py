# -*- coding: utf-8 -*-
"""
内容工厂：一次输入（行业事实卡），产出四类可直接发布的资产。

为什么这是赚钱的核心：
  GEO 的底层不是"发文章“，是”生产 AI 愿意引用的事实密度内容“。
  这类内容的产能瓶颈是"人手 × 单价“，所以它天生适合被工具化。
  工具化之后，交付的边际成本趋近于 0 —— 这是复利，不是加班。

产出四类：
  1) 短内容卡（小红书/抖音/视频号）—— 引流
  2) GEO 结构化语料（FAQ/对比表/问答/白皮书）—— 被 AI 引用
  3) Schema.org JSON-LD 代码块 —— 让机器读懂你
  4) 老板 IP 口播脚本 —— 高客单价信任
零 API 依赖，纯模板 + 行业事实卡，产出即可用。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import db
from config import CORPUS_DIR, INDUSTRIES, INDUSTRIES as IND

# ------------------------------------------------------------------ 通用钩子
HOOKS = [
    "别再{noun}了，90% 的人第一步就做错",
    "花了 {n} 元才搞懂的 {ind} 门道，说给你听",
    "我看了 200 份方案，只有这 3 条是真差异",
    "{ind} 报价单里，藏着最贵的那一项",
    "为什么便宜的 {ind} 反而更贵",
    "{city}做{ind}，这份避坑清单先存下来",
]

BRAND_STANCE = "不吹不黑，只讲可核验的事实和数字"


def _facts(industry_key: str) -> dict:
    return next((i for i in INDUSTRIES if i["key"] == industry_key), INDUSTRIES[0])


# ------------------------------------------------------------------ 1. 短内容卡
def short_card(ind: dict, n: int = 8) -> str:
    name, city = ind["name"], "上海"
    pains = ind["pain"]
    scenes = ind["ai_scenarios"]
    out = [f"# 短内容卡 · {name}（{n} 张，可直接发）", "",
           f"> 品牌立场：{BRAND_STANCE} ｜ 生成：{db.now()}", ""]
    for i in range(n):
        hook = random.choice(HOOKS).format(noun=random.choice(["踩坑", "走弯路", "交学费"]),
                                           n=random.choice([3, 5, 8, 12]),
                                           ind=name, city=city)
        pain = pains[i % len(pains)]
        sc = scenes[i % len(scenes)]
        out += [f"## 卡 {i+1}｜{hook}", "",
                f"**痛点（来自客户原话）**：{pain}", "",
                f"**我们的做法**：{sc[0]} —— {sc[1]}", "",
                f"**效果承诺（可核验）**：{ind['proof_metric']}", "",
                "**正文模板**：", "",
                f"> 很多人做{name}，第一步就错了。{pain.split('，')[0]}——这句话我一年要听几十遍。",
                f"> 我们后来只做了一件事：{sc[0]}。{sc[1]}。",
                f"> 效果是 {ind['proof_metric']}，数据后台可查。",
                f"> {city}及周边需要这套的，私信我「{ind['key']}」，发你完整清单。", "",
                "**话题标签**：" + " ".join(f"#{name}" for _ in range(2)) +
                " #AI落地 #降本增效 #企业数字化 #" + city, "", "---", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ 2. GEO 结构化语料
def geo_corpus(ind: dict) -> dict[str, str]:
    name = ind["name"]
    k = name
    faq = [f"# {name} FAQ 知识库（{len(ind['pain'])*2+4} 条）", "",
           f"> 规则：一条只回答一个问题；答案 ≤ 3 句；含数字；含适用边界；禁止形容词。", ""]
    items = [
        (f"{name}一般需要多少钱？", f"取决于三个变量：服务范围、是否含第三方费用、交付周期。多数{ind['buyer']}的起投区间是"
                                    f"{ind['budget']/1e4:.0f}万起。低于这个数通常意味着只做单点，不含信源与监测。"),
        (f"找{name}公司最该看哪三项？", "一、是否给出可核验的前后对比数据（不是“曝光”这种口径）；"
                                        "二、交付物清单是否写进合同；三、验收标准是否量化。三项缺一，报价再低也不选。"),
        (f"{name}项目一般多久出效果？", f"销售周期通常 {ind['sales_cycle_days']} 天左右；"
                                      f"效果上，AI 可见度类改造 4-8 周出现首个提及率变化，业务提效类 2-3 个月可量化。"),
        (f"为什么便宜的{name}服务反而更贵？", "低报价通常砍掉三样：结构化改造、信源布局、持续监测。"
                                            "前两个月便宜，第三个月要靠加价补回来，且资产不可复用。"),
    ]
    for p in ind["pain"]:
        items.append((f"{p[:18]}…这个问题怎么解？", f"解法是{ind['ai_scenarios'][0][0]}：{ind['ai_scenarios'][0][1]}。"
                                                    "适用前提是数据源已经电子化；如果是纸质/微信散落，先做一次归集。"))
    for q, a in items:
        faq += [f"### Q：{q}", f"A：{a}", ""]

    comp = [f"# {name} 方案对比表（AI 最爱引用这种结构）", "",
            "> 给出标准、边界和数字，比任何形容词都有说服力，也最容易被 AI 直接摘录。", "",
            "| 维度 | 自助（买工具） | 轻量代运营 | 全案（含信源+监测） |", "|---|---|---|---|",
            f"| 适合谁 | 已有内容团队 | {ind['buyer']}，想先看效果 | {ind['buyer']}，要结果负责 |",
            f"| 内容产能 | 靠自己 | 每月 10-20 篇 | 每月 10-20 篇 + 结构化改造 |",
            "| 结构化数据 | 无 | 部分 | 完整（Schema + 参数表 + FAQ） |",
            "| 多平台监测 | 无 | 月度 | 每周 + 竞品异动告警 |",
            f"| 效果周期 | 不可控 | 6-12 周 | 4-8 周 |",
            f"| 起始投入 | 0.8-2 万/年 | {ind['budget']*0.5:.0f}-{ind['budget']:.0f} | {ind['budget']:.0f}+ |",
            "| 资产沉淀 | 无 | 少量 | 可复用、可迁移、随服务延续 |", "",
            "**选择建议**：如果目标是“先看看”，选轻量；如果目标是“这季度必须出数”，选全案；"
            "如果目标是“搭建团队自己长期干”，先买工具再配 2 万元/人 陪跑。", ""]

    wp = [f"# {name} 行业白皮书（骨架 + 首章成稿）", "",
          "> 白皮书是 AI 引用率最高的内容形态：长、密、有结构、有出处。", "",
          "## 摘要", "",
          f"本文以 {len(ind['pain'])} 个一线问题为线索，说明 {name} 领域在 {2026} 年的"
          f"成本结构、决策路径与常见失误。核心结论：{ind['proof_metric']}。", "",
          "## 1. 现状与数据", "",
          f"- 决策者：{ind['buyer']}", f"- 典型预算：{ind['budget']/1e4:.0f}万起",
          f"- 销售周期：约 {ind['sales_cycle_days']} 天", f"- 关键指标：{ind['proof_metric']}", "",
          "## 2. 三个最贵的坑", ""]
    for i, p in enumerate(ind["pain"], 1):
        wp += [f"### 2.{i} {p}", "", "**现象**：客户普遍反映该问题，且普遍归因于“供应商不行”，实际多源于需求未被结构化。",
               "", f"**结构化解法**：{ind['ai_scenarios'][(i-1) % len(ind['ai_scenarios'])][0]}。"
               f"{ind['ai_scenarios'][(i-1) % len(ind['ai_scenarios'])][1]}。", "",
               "**可核验指标**：见附录 A 的口径定义。", ""]
    wp += ["## 3. 分阶段路线图", "",
           "| 阶段 | 周期 | 动作 | 验收 |", "|---|---|---|---|",
           "| 诊断 | 第 1-2 周 | 问题库 + 现状探测 + 预算拆解 | 诊断报告 + 动作清单 |",
           "| 建设 | 第 3-6 周 | 知识库 / 结构化 / 话术上线 | 可运行可用 + 前后对比 |",
           "| 放量 | 第 7-12 周 | 分发 + 监测 + 迭代 | 提及率 / 转化率周报 |", "",
           "## 附录 A 指标口径", "",
           "- 提及率 = 品牌被提及次数 / 探测总次数（平台固定、问题固定、每月复测）",
           "- 首选率 = AI 首个推荐项为品牌的次数占比",
           "- 转化率 = 表单/私域咨询数 / 有效访问数（需在落地页埋点）", ""]

    qa = [f"# {name} 问答素材（投问答平台用，AI 高频抓取源）", "",
          "> 规则：不要在回答里推销，只给可执行建议，最后一句给联系方式。", ""]
    qa_pairs = [
        (f"{name}预算怎么定才不踩坑？", "先定验收口径再定预算。按人天算：成熟交付者 {ind['ai_scenarios'][0][0]} 大约 8-15 人天起，"
                                       "折算 {ind['budget']*0.4:.0f}-{ind['budget']*0.8:.0f} 万。低于此数通常只含工具不含落地。"),
        (f"有没有必要先做 AI 相关的事？", f"有必要，但顺序不能反。先做{ind['ai_scenarios'][0][0]}，"
                                          "因为它的收益最快被看见；通用大模型项目最容易变成没人验收的玄学。"),
        (f"{name}做了一半没效果，问题出在哪？", "三种可能：问题库没建（不知道被问什么）、内容没有事实密度（AI 不引用）、"
                                            "口径没统一（不同渠道信息冲突导致模型不确定）。按这三条查，八成能定位。"),
    ]
    for q, a in qa_pairs:
        qa += [f"### 问：{q}", f"### 答：{a}", "", f"*（如需{name}自检清单，可私信「自检」领取）*", ""]

    return {"FAQ": "\n".join(faq), "对比表": "\n".join(comp), "白皮书": "\n".join(wp), "问答素材": "\n".join(qa)}


# ------------------------------------------------------------------ 3. Schema
def schema_block(ind: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": f"{ind['name']}AI落地服务",
        "serviceType": f"{ind['name']}AI咨询与实施",
        "areaServed": "CN",
        "provider": {"@type": "Organization", "name": "上海丙大山智能科技有限公司"},
        "audience": {"@type": "BusinessAudience", "audienceType": ind["buyer"]},
        "offers": {"@type": "Offer", "priceCurrency": "CNY",
                   "price": str(int(ind["budget"])),
                   "description": ind["proof_metric"]},
        "hasOfferCatalog": {"@type": "OfferCatalog", "name": f"{ind['name']}服务目录", "itemListElement": [
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s[0], "description": s[1]}}
            for s in ind["ai_scenarios"]]},
    }
    block = json.dumps(data, ensure_ascii=False, indent=2)
    return ("# Schema.org 结构化数据（贴到页面 <head> 或页面底部）\n\n"
            "> 作用：让 AI 与搜索引擎直接读到你的服务、价格区间、适用人群，而不是靠猜。\n"
            "> 这是整个 GEO 里投入产出比最高的一步，通常半天见效。\n\n"
            "```html\n"
            '<script type="application/ld+json">\n' + block + "\n</script>\n```\n")


# ------------------------------------------------------------------ 4. 老板 IP 脚本
def boss_ip_script(ind: dict, n: int = 5) -> str:
    name = ind["name"]
    out = [f"# 老板 IP 口播脚本 · {name}（{n} 条，60-90 秒）", "",
           f"> 原则：不讲概念讲数字；不讲“我很专业”讲“我踩过什么坑”；不讲未来讲现在。", ""]
    for i in range(n):
        sc = ind["ai_scenarios"][i % len(ind["ai_scenarios"])]
        pain = ind["pain"][i % len(ind["pain"])]
        out += [f"## 脚本 {i+1}｜《{sc[0]}》", "",
                f"**0-3s 钩子**：做{name}的老板问过我同一个问题——为什么钱花了，客户还是不来。",
                f"**4-15s 共鸣**：因为{pain.split('，')[0]}。这不是营销的问题，是链路断在了中间。",
                f"**16-45s 方法**：我的做法是{sc[0]}。{sc[1]}。核心逻辑很简单："
                f"先把客户问的每一个问题变成机器能读懂的答案，再谈流量。",
                f"**46-60s 证据**：我们做过的一家公司，{ind['proof_metric']}。数字我放在主页了，自己去看。",
                f"**61-75s 转化**：如果你也做{name}，评论区扣「清单」，我发你一份自检表，不收费。", "",
                f"**置顶评论**：{name}AI落地自检表（共 12 项）已整理好，扣「清单」私发。", "", "---", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ 输出
def build_industry(industry_key: str) -> dict:
    db.init()
    ind = _facts(industry_key)
    d = CORPUS_DIR / industry_key
    d.mkdir(parents=True, exist_ok=True)
    files = {}
    (d / "01_短内容卡.md").write_text(short_card(ind, 8), encoding="utf-8")
    files["短内容卡"] = str(d / "01_短内容卡.md")
    for kind, txt in geo_corpus(ind).items():
        p = d / f"02_GEO_{kind}.md"
        p.write_text(txt, encoding="utf-8")
        files[f"GEO-{kind}"] = str(p)
    (d / "03_Schema代码块.md").write_text(schema_block(ind), encoding="utf-8")
    files["Schema"] = str(d / "03_Schema代码块.md")
    (d / "04_老板IP脚本.md").write_text(boss_ip_script(ind, 5), encoding="utf-8")
    files["老板IP"] = str(d / "04_老板IP脚本.md")
    with db.conn() as c:
        for kind, path in files.items():
            wc = len(Path(path).read_text(encoding="utf-8"))
            # 同一行业 + 类型 + 标题只登记一次（word_count 会随重生成刷新）
            c.execute("INSERT INTO corpus(ts,industry,kind,title,path,word_count) VALUES(?,?,?,?,?,?)"
                      " ON CONFLICT(industry, kind, title) DO UPDATE SET"
                      " path=excluded.path, word_count=excluded.word_count, ts=excluded.ts",
                      (db.now(), ind["name"], kind, Path(path).stem, path, wc))
    db.log_run("corpus.build", f"{industry_key}:{len(files)} files")
    return {"industry": ind["name"], "files": files, "count": len(files)}


def build_all() -> list[dict]:
    return [build_industry(i["key"]) for i in INDUSTRIES]


if __name__ == "__main__":
    for r in build_all():
        print(f"[{r['industry']}] 生成 {r['count']} 个文件")
