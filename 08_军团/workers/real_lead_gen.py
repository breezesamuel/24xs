# -*- coding: utf-8 -*-
"""
Real Lead Gen Worker：用 Page-Agent 抓取真实 ICP 公司。
目标来源（按优先级）：
1. 企查查/天眼查/启信宝 - 公司基础信息 + 高管/股东
2. 官网 - 业务描述、团队页、新闻
3. 招聘页（BOSS直聘/拉勾/猎聘） - 招聘 JD 直接暴露痛点
4. 领英/脉脉 - 高管背景、公司动态
5. 微信公众号/小红书/抖音 - 内容营销情况、是否在做 SEO/GEO
"""
import asyncio
import json
import re
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from workers.page_agent_worker import PageAgentWorker, WorkerTask

LEADS_DIR = Path(__file__).resolve().parent.parent / "08_军团" / "experiments" / "real_leads"
LEADS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class RealLead:
    company: str
    industry: str
    city: str
    contact: str  # 姓名（职位）
    pain: str     # 从 JD/官网/内容推断的痛点
    channel: str  # 来源：qichacha/website/jobs/linkedin/wechat
    evidence_url: str
    icp_score: int = 0
    tier: str = "B"

class RealLeadGenWorker:
    """真实线索挖掘 Worker。每个任务 = 一个关键词/来源组合。"""

    def __init__(self, worker: PageAgentWorker):
        self.worker = worker

    async def scrape_qichacha_keyword(self, keyword: str, city: str = "", max_pages: int = 2) -> list[RealLead]:
        """企查查关键词搜索。返回公司列表页链接，再逐个进详情页。"""
        leads = []
        base_url = "https://www.qcc.com/search"
        for page in range(1, max_pages + 1):
            search_url = f"{base_url}?key={quote_plus(keyword)}&p={page}"
            if city:
                search_url += f"&area={quote_plus(city)}"

            task = WorkerTask(
                id=f"qcc_{keyword}_{page}_{uuid.uuid4().hex[:6]}",
                name=f"QCC搜索: {keyword} 第{page}页",
                instruction=f"""
访问企查查搜索结果页，提取前 10 家公司的：
1. 公司名称（完整全称）
2. 详情页链接
3. 注册地址（城市）
4. 法人代表/高管姓名
返回 JSON 数组，每项包含：company, detail_url, city, legal_person
""",
                target_url=search_url,
                max_steps=15,
                output_schema={"type": "array", "items": {"type": "object", "properties": {"company": {"type": "string"}, "detail_url": {"type": "string"}, "city": {"type": "string"}, "legal_person": {"type": "string"}}}}
            )
            result = await self.worker.execute(task)
            if result.success and result.output:
                for item in result.output:
                    # 进详情页抓更多
                    detail = await self._scrape_company_detail(item["detail_url"], item["company"])
                    if detail:
                        leads.append(RealLead(
                            company=item["company"],
                            industry=keyword,
                            city=item.get("city", city) or detail.get("city", ""),
                            contact=f"{item.get('legal_person', '未知')}(法人/高管)",
                            pain=detail.get("pain", f"{keyword} 行业获客依赖单一渠道，AI 搜索曝光为零"),
                            channel="qichacha",
                            evidence_url=item["detail_url"],
                        ))
            await asyncio.sleep(2)  # 礼貌延迟
        return leads

    async def _scrape_company_detail(self, detail_url: str, company_name: str) -> Optional[dict]:
        """抓详情页：官网链接、业务范围、招聘情况、社媒账号。"""
        task = WorkerTask(
            id=f"detail_{uuid.uuid4().hex[:8]}",
            name=f"详情页: {company_name}",
            instruction=f"""
访问公司详情页，提取：
1. 官网链接（如果有）
2. 经营范围/主营业务（前 3 项）
3. 是否有招聘信息（有则提取 1-2 个 JD 标题）
4. 是否有微信公众号/抖音/小红书链接
返回 JSON 对象。
""",
            target_url=detail_url,
            max_steps=15,
            output_schema={"type": "object", "properties": {"website": {"type": "string"}, "business_scope": {"type": "array", "items": {"type": "string"}}, "job_titles": {"type": "array", "items": {"type": "string"}}, "social_links": {"type": "array", "items": {"type": "string"}}, "city": {"type": "string"}}}
        )
        result = await self.worker.execute(task)
        if result.success and result.output:
            return result.output
        return None

    async def scrape_job_board(self, keyword: str, city: str = "", board: str = "boss") -> list[RealLead]:
        """招聘板块搜索：JD 直接暴露痛点。"""
        urls = {
            "boss": f"https://www.zhipin.com/web/geek/job?query={quote_plus(keyword)}&city={quote_plus(city)}",
            "lagou": f"https://www.lagou.com/wn/jobs?kd={quote_plus(keyword)}&city={quote_plus(city)}",
        }
        url = urls.get(board, urls["boss"])

        task = WorkerTask(
            id=f"jobs_{board}_{keyword}_{uuid.uuid4().hex[:6]}",
            name=f"招聘搜索: {keyword} @ {board}",
            instruction=f"""
访问招聘搜索结果页，提取前 15 条职位的：
1. 公司名称
2. 职位标题
3. 职位描述前 200 字（重点找：获客、SEO、内容、AI、转化、流量、品牌曝光等关键词）
4. 公司所在城市
返回 JSON 数组。
""",
            target_url=url,
            max_steps=20,
            output_schema={"type": "array", "items": {"type": "object", "properties": {"company": {"type": "string"}, "title": {"type": "string"}, "jd_snippet": {"type": "string"}, "city": {"type": "string"}}}}
        )
        result = await self.worker.execute(task)
        leads = []
        if result.success and result.output:
            for item in result.output:
                # 从 JD 推断痛点
                pain = self._infer_pain_from_jd(item["jd_snippet"], keyword)
                leads.append(RealLead(
                    company=item["company"],
                    industry=keyword,
                    city=item.get("city", city) or "",
                    contact="招聘负责人/业务负责人",
                    pain=pain,
                    channel=f"jobs_{board}",
                    evidence_url=url,
                ))
        return leads

    async def scrape_website(self, company: str, website: str) -> Optional[RealLead]:
        """抓官网：业务描述、团队、新闻、是否在做内容/SEO。"""
        task = WorkerTask(
            id=f"site_{company}_{uuid.uuid4().hex[:6]}",
            name=f"官网分析: {company}",
            instruction=f"""
访问 {website}，提取：
1. 核心业务描述（首屏/关于我们）
2. 团队/高管页面的关键人姓名+职位
3. 是否有博客/新闻/案例/资源中心（统计文章数、最近更新时间）
4. 是否有 SEO/SEM 痕迹（title/description/结构化数据/站点地图）
5. 是否在投放广告/做内容营销
返回 JSON。
""",
            target_url=website,
            max_steps=20,
            output_schema={"type": "object", "properties": {"business_desc": {"type": "string"}, "key_people": {"type": "array", "items": {"type": "string"}}, "content_activity": {"type": "object", "properties": {"has_blog": {"type": "boolean"}, "article_count": {"type": "integer"}, "last_update": {"type": "string"}}}, "seo_signals": {"type": "object", "properties": {"has_sitemap": {"type": "boolean"}, "has_structured_data": {"type": "boolean"}, "title_optimized": {"type": "boolean"}}}, "marketing_signals": {"type": "array", "items": {"type": "string"}}}}
        )
        result = await self.worker.execute(task)
        if result.success and result.output:
            data = result.output
            pain = self._infer_pain_from_website(data, company)
            contact = data.get("key_people", ["决策者"])[0] if data.get("key_people") else "决策者"
            return RealLead(
                company=company,
                industry="",  # 后续补全
                city="",
                contact=f"{contact}(官网高管)",
                pain=pain,
                channel="website",
                evidence_url=website,
            )
        return None

    def _infer_pain_from_jd(self, jd: str, keyword: str) -> str:
        jd_lower = jd.lower()
        signals = []
        if any(w in jd_lower for w in ["获客", "线索", "转化", "流量", "cac", "roi"]):
            signals.append("获客成本高/渠道单一")
        if any(w in jd_lower for w in ["seo", "搜索优化", "关键词", "排名", "流量"]):
            signals.append("SEO 依赖度高但效果不稳定")
        if any(w in jd_lower for w in ["内容", "文案", "公众号", "小红书", "抖音", "视频号"]):
            signals.append("内容产出依赖人力，难规模化")
        if any(w in jd_lower for w in ["ai", "大模型", "智能体", "自动化", "提效"]):
            signals.append("想接入 AI 但无落地场景")
        if any(w in jd_lower for w in ["品牌", "曝光", "知名度", "公关"]):
            signals.append("品牌声量不足，AI 搜索不可见")
        return "；".join(signals) if signals else f"{keyword} 行业获客依赖单一渠道，AI 搜索曝光为零"

    def _infer_pain_from_website(self, data: dict, company: str) -> str:
        signals = []
        seo = data.get("seo_signals", {})
        content = data.get("content_activity", {})
        marketing = data.get("marketing_signals", [])

        if not seo.get("has_sitemap") or not seo.get("title_optimized"):
            signals.append("官网 SEO 基建缺失，搜索引擎/AI 难抓取")
        if not content.get("has_blog") or content.get("article_count", 0) < 10:
            signals.append("内容资产薄弱，无长尾关键词覆盖")
        if "付费广告" in marketing or "SEM" in marketing:
            signals.append("过度依赖付费流量，边际成本递增")
        if not any("ai" in m.lower() or "智能" in m for m in marketing):
            signals.append("未布局 AI 搜索/GEO，品牌在 AI 回答中不可见")
        return "；".join(signals) if signals else f"{company} 官网内容资产薄弱，AI 搜索不可见"

    async def enrich_lead(self, lead: RealLead) -> RealLead:
        """补全单个线索：如果有官网，抓官网；补全行业/城市。"""
        # 这里可以加更多补全逻辑
        return lead

async def demo():
    worker = PageAgentWorker()
    gen = RealLeadGenWorker(worker)

    print("[*] 测试：招聘板块搜索 'AI 落地' 相关职位")
    leads = await gen.scrape_job_board("AI 落地", city="上海", board="boss")
    print(f"[+] 得到 {len(leads)} 条线索")
    for l in leads[:3]:
        print(f"  - {l.company} | {l.city} | {l.contact} | {l.pain[:50]}...")

    # 保存
    out = LEADS_DIR / f"leads_jobs_{uuid.uuid4().hex[:8]}.json"
    out.write_text(json.dumps([asdict(l) for l in leads], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] 保存到 {out}")

if __name__ == "__main__":
    asyncio.run(demo())