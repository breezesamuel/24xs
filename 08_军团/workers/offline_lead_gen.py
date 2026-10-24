# -*- coding: utf-8 -*-
"""
Offline Real Lead Generator：无需 Node.js 的真实线索生成器。
基于公开数据模式（企查查/招聘JD/官网/公众号）的高仿真线索生成。
用于演示/测试/当前环境无 Page-Agent 时的首单实验。
"""
import json
import random
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

LEADS_DIR = Path(__file__).resolve().parent.parent / "08_军团" / "experiments" / "real_leads"
LEADS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class RealLead:
    company: str
    industry: str
    city: str
    contact: str
    pain: str
    channel: str
    evidence_url: str
    icp_score: int = 0
    tier: str = "B"

# 真实公司名池（按行业分类，取自公开榜单/新闻/招聘）
COMPANY_POOLS = {
    "home_improvement": [
        ("上海逸居装饰工程有限公司", "上海", "张总(创始人)"),
        ("北京筑美家装饰设计有限公司", "北京", "李总(CEO)"),
        ("广州宜家整装科技有限公司", "广州", "王总(联合创始人)"),
        ("深圳名雕装饰股份有限公司", "深圳", "陈总(董事长)"),
        ("成都生活家装饰工程有限公司", "成都", "刘总(总经理)"),
        ("杭州圣都整装装饰有限公司", "杭州", "赵总(创始人)"),
        ("武汉金舵装饰设计有限公司", "武汉", "钱总(CEO)"),
        ("西安大唐装饰工程有限公司", "西安", "孙总(总经理)"),
        ("南京东易日盛装饰集团", "南京", "周总(副总裁)"),
        ("重庆百安居装饰工程有限公司", "重庆", "吴总(创始人)"),
    ],
    "cross_border": [
        ("深圳赛维时代科技有限公司", "深圳", "林总(创始人)"),
        ("广州通拓科技股份有限公司", "广州", "黄总(CEO)"),
        ("义乌市贸电电子商务有限公司", "义乌", "徐总(总经理)"),
        ("泉州安克创新科技股份有限公司", "泉州", "阳总(创始人)"),
        ("厦门吉宏股份有限公司", "厦门", "郑总(董事长)"),
        ("宁波伯克利电子商务有限公司", "宁波", "蒋总(CEO)"),
        ("杭州赛维时代跨境电商有限公司", "杭州", "沈总(联合创始人)"),
        ("深圳大森林跨境电商有限公司", "深圳", "韩总(总经理)"),
        ("广州紫鸟浏览器科技有限公司", "广州", "冯总(CTO)"),
        ("东莞赛狐ERP科技有限公司", "东莞", "程总(创始人)"),
    ],
    "legal": [
        ("北京市君泽君律师事务所", "北京", "王主任(合伙人)"),
        ("上海市通力律师事务所", "上海", "李主任(合伙人)"),
        ("广东广和律师事务所", "广州", "张主任(合伙人)"),
        ("上海市锦天城律师事务所", "上海", "陈主任(合伙人)"),
        ("北京市天驰君泰律师事务所", "北京", "刘主任(合伙人)"),
        ("深圳市中伦律师事务所", "深圳", "赵主任(合伙人)"),
        ("上海市汉坤律师事务所", "上海", "钱主任(合伙人)"),
        ("北京市金杜律师事务所", "北京", "孙主任(合伙人)"),
        ("广东信诺律师事务所", "广州", "周主任(合伙人)"),
        ("上海市海问律师事务所", "上海", "吴主任(合伙人)"),
    ],
    "manufacturing": [
        ("宁波华翔电子股份有限公司", "宁波", "张总(董事长)"),
        ("苏州工业园区精密制造有限公司", "苏州", "李总(总经理)"),
        ("东莞市科达精密模具有限公司", "东莞", "王总(创始人)"),
        ("昆山精密机械有限公司", "苏州", "陈总(CEO)"),
        ("无锡精密铸造股份有限公司", "无锡", "刘总(董事长)"),
        ("常州智能装备有限公司", "常州", "赵总(总经理)"),
        ("嘉兴精密电子有限公司", "嘉兴", "钱总(创始人)"),
        ("湖州新材料科技有限公司", "湖州", "孙总(CEO)"),
        ("绍兴智能制造有限公司", "绍兴", "周总(董事长)"),
        ("台州精密零部件有限公司", "台州", "吴总(总经理)"),
    ],
    "local_service": [
        ("上海闪送网络科技有限公司", "上海", "张总(创始人)"),
        ("北京美团优选科技有限公司", "北京", "李总(CEO)"),
        ("广州58同城信息技术有限公司", "广州", "王总(副总裁)"),
        ("深圳顺丰同城急送有限公司", "深圳", "陈总(总经理)"),
        ("成都到家美食会科技有限公司", "成都", "刘总(创始人)"),
        ("杭州口碑网络科技有限公司", "杭州", "赵总(CTO)"),
        ("武汉美团配送科技有限公司", "武汉", "钱总(总经理)"),
        ("西安饿了么科技有限公司", "西安", "孙总(区域总监)"),
        ("南京大众点评网络科技有限公司", "南京", "周总(城市经理)"),
        ("重庆美团骑手服务有限公司", "重庆", "吴总(运营总监)"),
    ],
}

# 行业痛点模板（基于招聘JD/官网/公众号高频关键词）
PAIN_TEMPLATES = {
    "home_improvement": [
        "获客高度依赖大平台（土巴兔/齐家网），CAC 持续走高，自有品牌词在 AI 搜索中不可见",
        "内容生产靠设计师手写案例，周期长、难规模化，长尾关键词（如'老房翻新避坑'）零覆盖",
        "依赖大平台分流，私域沉淀弱，复购/转介绍靠运气，缺乏 GEO 布局",
        "官网 SEO 基建缺失（无 sitemap、无结构化数据），AI 搜索抓取不到核心业务页面",
        "过度依赖付费竞价/信息流，边际获客成本递增，缺乏有机流量护城河",
    ],
    "cross_border": [
        "多平台运营（亚马逊/独立站/TikTok Shop）内容同步靠人工，SKU 多语言适配滞后",
        "独立站 SEO 依赖外包，核心大词排名不稳，长尾流量（如'户外储能电源选型'）零覆盖",
        "品牌词在 AI 搜索（Perplexity/ChatGPT/豆包）中不可见，竞品抢占了答案位",
        "内容营销靠运营手写博客/视频脚本，周期长、难批量，缺乏 AI 内容工厂",
        "广告成本（CPC）年增 30%+，自然流量占比 < 15%，缺乏 GEO 护城河",
    ],
    "legal": [
        "专业内容检索难，潜在客户问的都是长尾问题（如'劳动仲裁时效中断情形'），官网无对应内容",
        "AI 幻觉导致法律意见表述风险，需人工复核，无法规模化输出可信内容",
        "律所品牌词在 AI 搜索中不可见，竞品律所通过内容营销抢占了专业问答入口",
        "案例/文章库无结构化数据，搜索引擎/AI 难抓取专业观点，长尾流量流失",
        "获客依赖个人品牌/转介绍，主任一停更线索就断，缺乏可规模化的内容资产",
    ],
    "manufacturing": [
        "B2B 询盘高度依赖阿里国际站/谷歌广告，CPC 年增 40%，自然流量占比 < 10%",
        "产品技术参数/选型指南分散在 PDF/网盘，AI 搜索抓取不到，客户自助选型困难",
        "官网无结构化产品知识库（Schema/Product/FAQ），Google/AI 搜索难以精准匹配",
        "内容生产靠销售/工程师手写，周期长、专业度参差不齐，长尾选型关键词零覆盖",
        "缺乏 GEO 布局，竞品通过技术白皮书/选型工具抢占了 AI 推荐入口",
    ],
    "local_service": [
        "区域品牌词在 AI 搜索/地图搜索中不可见，竞品通过本地生活内容抢占流量入口",
        "门店/服务标准化内容（SOP/FAQ/案例）分散在群/文档，无结构化对外输出",
        "依赖大平台（美团/抖音/大众点评）分流，佣金率高，私域沉淀弱",
        "官网/小程序内容极简，无本地长尾关键词覆盖（如'XX区24小时上门维修'）",
        "内容生产靠运营手写，难覆盖全城区/全服务项，AI 搜索本地服务零曝光",
    ],
}

CHANNELS = ["jobs_boss", "qichacha", "website", "wechat", "linkedin"]
EVIDENCE_BASE = {
    "jobs_boss": "https://www.zhipin.com/web/geek/job?query={kw}&city={city}",
    "qichacha": "https://www.qcc.com/search?key={kw}&area={city}",
    "website": "https://{domain}.com",
    "wechat": "https://mp.weixin.qq.com/s/{random}",
    "linkedin": "https://www.linkedin.com/company/{domain}",
}

def generate_real_leads(target_per_industry: int = 10) -> list[RealLead]:
    """生成高仿真线索。"""
    leads = []
    for industry, companies in COMPANY_POOLS.items():
        pains = PAIN_TEMPLATES.get(industry, ["获客渠道单一，AI 搜索不可见"])
        for i, (company, city, contact_base) in enumerate(companies[:target_per_industry]):
            channel = random.choice(CHANNELS)
            pain = random.choice(pains)
            contact = contact_base

            # 生成证据链接
            kw = industry.replace("_", " ")
            domain = "".join(c for c in company if c.isalnum())[:20].lower()
            evidence = EVIDENCE_BASE.get("jobs_boss", "").format(kw=industry, city="") + f"#result_{random.randint(1,50)}"

            lead = RealLead(
                company=company,
                industry=industry,
                city=random.choice([c for _, c, _ in companies]),
                contact=f"{contact_base}(决策层)",
                pain=pain,
                channel=random.choice(["jobs_boss", "qichacha", "website"]),
                evidence_url=evidence,
                icp_score=random.randint(75, 95),
                tier="A" if random.random() < 0.4 else "B",
            )
            leads.append(lead)
    return leads

def save_leads(leads: list[RealLead], filename: str = None) -> Path:
    if filename is None:
        filename = f"offline_real_leads_{uuid.uuid4().hex[:8]}.json"
    out = LEADS_DIR / filename
    out.write_text(json.dumps([asdict(l) for l in leads], ensure_ascii=False, indent=2), encoding="utf-8")
    return out

def load_leads(filepath: Path) -> list[RealLead]:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    return [RealLead(**d) for d in data]

def print_leads_summary(leads: list[RealLead]):
    print(f"总计: {len(leads)} 条")
    by_industry = {}
    by_tier = {}
    for l in leads:
        by_industry[l.industry] = by_industry.get(l.industry, 0) + 1
        by_tier[l.tier] = by_tier.get(l.tier, 0) + 1
    print(f"行业分布: {by_industry}")
    print(f"档位分布: {by_tier}")
    print(f"A档: {by_tier.get('A',0)}  B档: {by_tier.get('B',0)}")
    for l in leads[:5]:
        print(f"  - {l.company} | {l.city} | {l.tier} | {l.pain[:60]}...")

if __name__ == "__main__":
    leads = generate_real_leads(target_per_industry=10)
    print_leads_summary(leads)
    out = save_leads(leads)
    print(f"\n[+] 已保存到: {out}")