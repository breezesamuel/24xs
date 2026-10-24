# -*- coding: utf-8 -*-
"""
Loot Drop 情报模块：通过 MCP 接入创业墓地，自动挖掘可重建的市场缺口。
核心策略：找 2015-2018 年 B 轮死于「单位经济模型」的项目，用现代 AI/Serverless 栈翻盘。
"""
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

INTEL_DIR = Path(__file__).resolve().parent
INTEL_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class DeadStartup:
    id: str
    name: str
    sector: str
    product_type: str
    country: str
    funding_total: float  # USD
    cause_of_death: str
    year_died: int
    rebuild_plan: Optional[dict] = None
    market_potential_score: float = 0.0  # 0-100
    difficulty_rating: str = "medium"
    scalability_rating: str = "medium"

@dataclass
class RebuildOpportunity:
    startup: DeadStartup
    why_rebuildable: str
    suggested_stack: list[str]
    revenue_model: str
    mvp_steps: list[str]
    mistakes_to_avoid: list[str]
    estimated_market_size: str
    capital_required_usd: float
    time_to_mvp_weeks: int

class LootDropIntel:
    """通过 stdio MCP (JSON-RPC) 调用 loot-drop.io 的只读情报服务。"""

    # MCP tools/list 返回的合法枚举，必须原样使用，否则 API 报 Invalid enum value
    CAUSE_ENUM = {
        "all": [
            "Competition", "Unit Economics", "Ran Out of Cash", "No Market Need",
            "Legal/Regulatory", "Product/Tech Failure", "Team/Founder Conflict",
        ],
        # 现代 AI/Serverless 栈能实质改善的失败原因
        "reversible": ["Unit Economics", "No Market Need", "Product/Tech Failure"],
    }

    def __init__(self, cache_ttl_sec: int = 300):
        self.cache_ttl_sec = cache_ttl_sec
        self._cache = {}

    def _run_mcp(self, tool: str, args: dict) -> dict:
        """通过 stdio + JSON-RPC 调用 MCP 服务器。

        旧实现把工具名和参数当命令行传给 npx，但 mcp-lootdrop 是 stdio MCP
        服务器（启动后打印 "ready (stdio)"），必须走 initialize -> tools/call。
        """
        try:
            from intel.mcp_client import call_lootdrop
        except ImportError:
            try:
                from .mcp_client import call_lootdrop
            except ImportError:
                # 以脚本方式直接运行时（python intel\lootdrop_intel.py），
                # 包上下文不存在，需把 08_军团 加入 sys.path
                import sys as _sys
                from pathlib import Path as _Path
                _root = str(_Path(__file__).resolve().parent.parent)
                if _root not in _sys.path:
                    _sys.path.insert(0, _root)
                try:
                    from intel.mcp_client import call_lootdrop
                except ImportError:
                    return {"error": "mcp_client 不可用"}
        res = call_lootdrop(tool, args or {})
        if isinstance(res, dict) and res.get("isError"):
            return {"error": res.get("text", "MCP 工具返回错误")}
        return res

    def diagnose(self) -> dict:
        return self._run_mcp("lootdrop_diagnose", {})

    def search_startups(self,
                        sector: Optional[str] = None,
                        cause: Optional[str] = None,
                        product_type: Optional[str] = None,
                        min_funding: Optional[float] = None,
                        max_funding: Optional[float] = None,
                        years: Optional[str] = None,  # e.g. "2015-2018"
                        limit: int = 50,
                        sort_by: str = "funding_desc") -> list[DeadStartup]:
        """搜索失败项目。优先找：B轮、2015-2018、死于单位经济、融资 500w-5000w 美元。"""
        args = {"limit": limit, "sort_by": sort_by}
        if sector: args["sector"] = sector
        if cause: args["cause"] = cause
        if product_type: args["product_type"] = product_type
        if min_funding: args["min_funding"] = min_funding
        if max_funding: args["max_funding"] = max_funding
        if years: args["years"] = years

        raw = self._run_mcp("search_startups", args)
        if isinstance(raw, dict) and raw.get("error"):
            print(f"[WARN] MCP search failed: {raw['error']}", file=sys.stderr)
            return self._fallback_local_data()

        items = self._extract_items(raw)
        startups = []
        for item in items:
            s = DeadStartup(
                id=item.get("id", ""),
                name=item.get("name", ""),
                sector=item.get("sector", ""),
                product_type=item.get("product_type", ""),
                country=item.get("country", ""),
                funding_total=float(item.get("funding_total", 0) or 0),
                cause_of_death=item.get("cause_of_death", ""),
                year_died=int(item.get("year_died", 0) or 0),
            )
            startups.append(s)
        if not startups:
            print("[WARN] MCP 未返回可解析记录，使用离线兜底", file=sys.stderr)
            return self._fallback_local_data()
        return startups

    # ---------- 响应解析：MCP 文本工具返回 markdown，需解析 ----------
    @staticmethod
    def _extract_items(raw) -> list[dict]:
        """统一从 MCP 响应里取出记录列表。

        mcp-lootdrop 的多数工具返回 markdown 文本而非 JSON，格式为：
            - **WeWork** (#2035) · Real Estate · Marketplace · † Unit Economics · $22.0B
              ↳ description...
        """
        if isinstance(raw, list):
            return raw
        if not isinstance(raw, dict):
            return []

        # 1) 已是 JSON 结构
        for key in ("data", "results", "startups", "items"):
            if isinstance(raw.get(key), list):
                return raw[key]

        # 2) markdown 文本
        text = raw.get("text")
        if not text and isinstance(raw.get("content"), list):
            text = "\n".join(
                c.get("text", "") for c in raw["content"] if c.get("type") == "text"
            )
        if not text:
            return []

        return LootDropIntel._parse_markdown_listings(text)

    _MD_ROW = re.compile(
        r"^-\s+\*\*(?P<name>[^*]+)\*\*\s*\((?P<id>[^)]+)\)\s*·\s*(?P<rest>.+?)\s*$"
    )

    @classmethod
    def _parse_markdown_listings(cls, text: str) -> list[dict]:
        out = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            m = cls._MD_ROW.match(line)
            if not m:
                continue
            parts = [p.strip() for p in m.group("rest").split("·")]
            funding = 0.0
            cause = ""
            sector = product_type = ""
            for p in parts:
                if p.startswith("†"):
                    cause = p.lstrip("†").strip()
                elif p.startswith("$"):
                    digits = re.sub(r"[^0-9.]", "", p)
                    if digits:
                        val = float(digits)
                        # B/M/K 换算
                        unit = p.upper()
                        if "B" in unit:
                            val *= 1_000
                        elif "M" in unit:
                            pass
                        elif "K" in unit:
                            val /= 1_000
                        funding = val
                elif not sector:
                    sector = p
                elif not product_type:
                    product_type = p
            ident = m.group("id").strip()
            out.append({
                "id": ident,
                "name": m.group("name").strip(),
                "sector": sector,
                "product_type": product_type,
                "country": "",
                "funding_total": funding,
                "cause_of_death": cause,
                "year_died": 0,
            })
        return out

    def get_rebuild_plan(self, startup_id: str) -> Optional[dict]:
        """get_startup 要求 id 为数字，搜索结果里的 '#2035' 需先转成 2035。

        实测返回是 markdown 而非 JSON，关键段落形如：
            ## Scores
            Difficulty 2/5 · Scalability 2/5 · Market potential: medium
            ## 🔁 Rebuild plan — FlexOS
            <正文>
            **MVP steps:**
            1. ...
            **Tech stack:** Next.js, PostgreSQL, ...
        因此需要自行解析。
        """
        numeric = self._numeric_id(startup_id)
        if numeric is None:
            return self._fallback_rebuild_plan(startup_id)
        raw = self._run_mcp("get_startup", {"id": numeric})
        if isinstance(raw, dict) and raw.get("error"):
            return self._fallback_rebuild_plan(startup_id)

        text = raw.get("text", "") if isinstance(raw, dict) else ""
        if not text:
            items = self._extract_items(raw)
            for item in items:
                if isinstance(item, dict) and item.get("rebuild_plan"):
                    return item["rebuild_plan"]
            return None

        plan = self._parse_startup_markdown(text)
        return plan or self._fallback_rebuild_plan(startup_id)

    @staticmethod
    def _numeric_id(value) -> Optional[int]:
        m = re.search(r"\d+", str(value))
        return int(m.group(0)) if m else None

    # difficulty/scalability 是 1-5 分，5 最难；反转为"越大越好"的 0-100 分
    _DIFFICULTY_PENALTY = {"easy": 0, "medium": 15, "hard": 35}
    _SCALE_BONUS = {"high": 25, "medium": 12, "low": 0}

    @classmethod
    def _parse_startup_markdown(cls, text: str) -> Optional[dict]:
        """解析 get_startup 的 markdown，抽出评分与重建方案"""
        if "Rebuild plan" not in text:
            return None

        plan: dict = {}

        # --- 评分段 ---
        m = re.search(r"Difficulty\s+(\d)\s*/\s*5", text)
        difficulty_n = int(m.group(1)) if m else None
        m = re.search(r"Scalability\s+(\d)\s*/\s*5", text)
        scale_n = int(m.group(1)) if m else None

        if difficulty_n is not None:
            plan["difficulty_rating"] = (
                "easy" if difficulty_n <= 2 else "medium" if difficulty_n == 3 else "hard"
            )
        if scale_n is not None:
            plan["scalability_rating"] = (
                "high" if scale_n >= 4 else "medium" if scale_n == 3 else "low"
            )

        m = re.search(r"Market potential:\s*(\w+)", text, re.IGNORECASE)
        if m:
            pot = m.group(1).lower()
            plan["_market_potential_word"] = pot
            plan["market_potential_score"] = {
                "very high": 92, "high": 80, "medium": 62, "medium-high": 78,
                "low": 35, "very low": 15,
            }.get(pot, 60)

        # 若 MCP 未给市场潜力，用难度/可扩展性推导一个可排序的分数
        if "market_potential_score" not in plan and (difficulty_n is not None):
            base = 100 - difficulty_n * 12
            base += cls._SCALE_BONUS.get(plan.get("scalability_rating", "medium"), 0)
            plan["market_potential_score"] = max(30, min(95, base))

        # --- 重建方案正文 ---
        idx = text.find("Rebuild plan")
        body = text[idx:]
        m = re.search(r"Rebuild plan\s*(?:—|-)?\s*([A-Za-z0-9][\w .'-]*)", body)
        if m and m.group(1).strip():
            plan["name"] = m.group(1).strip()

        m = re.search(r"\*\*MVP steps:\*\*\s*(.+?)(?:\n\n|\*\*|$)", body, re.DOTALL)
        if m:
            steps = [re.sub(r"^\s*\d+\.\s*", "", ln).strip()
                     for ln in m.group(1).splitlines() if ln.strip()]
            plan["mvp_steps"] = [s for s in steps if s][:8]

        m = re.search(r"\*\*Tech stack:\*\*\s*(.+)", body)
        if m:
            stack = [s.strip() for s in m.group(1).split(",") if s.strip()]
            plan["suggested_tech_stack"] = stack

        m = re.search(r"\*\*Mistakes to avoid:\*\*\s*(.+?)(?:\n\n|\*\*|$)", body, re.DOTALL)
        if m:
            plan["mistakes_to_avoid"] = [
                re.sub(r"^\s*[-*]\s*", "", ln).strip()
                for ln in m.group(1).splitlines() if ln.strip()
            ][:8]

        m = re.search(r"\*\*Revenue model:\*\*\s*(.+)", body)
        if m:
            plan["revenue_model"] = m.group(1).strip()[:300]

        m = re.search(r"\*\*Estimated capital required[^\d$]*\$?\s*([\d,]+)", body, re.IGNORECASE)
        if m:
            plan["estimated_capital_required_usd"] = float(m.group(1).replace(",", ""))

        m = re.search(r"\*\*Time to MVP:\*\*\s*(\d+)", body, re.IGNORECASE)
        if m:
            plan["time_to_mvp_weeks"] = int(m.group(1))

        return plan if plan else None

    def get_failure_landscape(self) -> dict:
        return self._run_mcp("failure_landscape", {})

    def get_graveyard_stats(self, by: str = "cause") -> dict:
        return self._run_mcp("graveyard_stats", {"by": by})

    def top_startups_by_capital(self, limit: int = 20) -> list[DeadStartup]:
        raw = self._run_mcp("top_startups", {"limit": limit, "rank_by": "capital"})
        startups = []
        for item in raw.get("data", []):
            s = DeadStartup(
                id=item.get("id", ""),
                name=item.get("name", ""),
                sector=item.get("sector", ""),
                product_type=item.get("product_type", ""),
                country=item.get("country", ""),
                funding_total=float(item.get("funding_total", 0) or 0),
                cause_of_death=item.get("cause_of_death", ""),
                year_died=int(item.get("year_died", 0) or 0),
            )
            startups.append(s)
        return startups

    def find_rebuildable_gems(self, max_results: int = 20) -> list[RebuildOpportunity]:
        """
        核心挖掘逻辑：
        1. 筛选：B轮融资、2015-2018 年死、死因属"可被现代技术栈翻转"的类别
        2. 获取重建方案
        3. 打分：市场潜力 > 70、难度 ≤ medium、可扩展性 ≥ medium
        4. 估算所需本金（≤ 10k USD 优先）

        注意：cause 必须取 MCP schema 允许的枚举值，否则 API 返回
        "Invalid enum value"。合法值见 CAUSE_ENUM。
        """
        # 可被 AI/Serverless 栈改善的失败原因：单位经济、现金流、无市场需求、技术失败
        candidates = []
        for cause in self.CAUSE_ENUM["reversible"]:
            candidates += self.search_startups(
                cause=cause,
                years="2015-2018",
                min_funding=500_000,
                max_funding=10_000_000,
                limit=50
            )

        # 去重
        seen = set()
        uniq = []
        for c in candidates:
            if c.id not in seen:
                seen.add(c.id)
                uniq.append(c)

        opportunities = []
        for s in uniq[:max_results]:
            plan = self.get_rebuild_plan(s.id)
            if not plan:
                continue
            s.rebuild_plan = plan  # 附加到 startup 供显示用

            # 简单打分
            market_score = float(plan.get("market_potential_score", 0) or 0)
            diff = str(plan.get("difficulty_rating", "medium")).lower()
            scale = str(plan.get("scalability_rating", "medium")).lower()

            if market_score < 70 or diff == "hard" or scale == "low":
                continue

            # 把评分同步回 startup 顶层：search_startups 的扁平记录里这些字段为 0，
            # 真实值只存在于嵌套的 rebuild_plan 中，不同步会导致排序与展示全为 0
            s.market_potential_score = market_score
            s.difficulty_rating = diff
            s.scalability_rating = scale

            capital_req = float(plan.get("estimated_capital_required_usd", 10000) or 10000)
            if capital_req > 15000:  # 超过单次实验预算，标记但不优先
                continue

            opp = RebuildOpportunity(
                startup=s,
                why_rebuildable=f"原死因 {s.cause_of_death}，现代 AI/Serverless 栈可翻转单位经济",
                suggested_stack=plan.get("suggested_tech_stack", ["Next.js", "Vercel", "Supabase", "OpenAI/DeepSeek", "Stripe"]),
                revenue_model=plan.get("revenue_model", "SaaS subscription"),
                mvp_steps=plan.get("mvp_steps", ["Define core workflow", "Build MVP in 2 weeks", "Launch to waitlist"]),
                mistakes_to_avoid=plan.get("mistakes_to_avoid", ["Overbuilding", "Ignoring unit economics", "Premature scaling"]),
                estimated_market_size=plan.get("estimated_market_size", "Unknown"),
                capital_required_usd=capital_req,
                time_to_mvp_weeks=int(plan.get("time_to_mvp_weeks", 4) or 4),
            )
            opportunities.append(opp)

        # 按市场潜力 / 所需本金 排序（市场潜力取自 startup 顶层，已同步）
        opportunities.sort(
            key=lambda o: o.startup.market_potential_score / max(o.capital_required_usd, 1),
            reverse=True,
        )
        return opportunities

    def _fallback_local_data(self) -> list[DeadStartup]:
        """离线兜底：内置几个经典案例（来自 Loot Drop 公开数据）。"""
        return [
            DeadStartup("honestbee", "Honestbee", "Marketplace", "Food Delivery", "Singapore", 15_000_000, "Unit economics + operational complexity", 2020),
            DeadStartup("99dresses", "99dresses", "Marketplace", "Fashion Resale", "Australia", 3_500_000, "Two-sided logistics unit economics", 2016),
            DeadStartup("arivale", "Arivale", "Health", "Personalized Wellness", "USA", 50_000_000, "Regulatory + unit economics", 2019),
            DeadStartup("anki", "Anki", "Hardware", "Consumer Robotics", "USA", 200_000_000, "High CAPEX + unit economics", 2019),
            DeadStartup("rdio", "Rdio", "Consumer", "Music Streaming", "USA", 125_000_000, "Outcompeted by Spotify freemium", 2015),
            DeadStartup("juju", "Juju", "SaaS", "Job Search Aggregator", "UK", 2_000_000, "Unit economics + competition", 2018),
            DeadStartup("skillshare_clone", "Skillshare Clone", "EdTech", "Course Marketplace", "USA", 5_000_000, "Content creation bottleneck + CAC", 2017),
        ]

    def _fallback_rebuild_plan(self, startup_id: str) -> Optional[dict]:
        """离线重建方案兜底。"""
        plans = {
            "honestbee": {
                "market_potential_score": 85,
                "difficulty_rating": "medium",
                "scalability_rating": "high",
                "suggested_tech_stack": ["Next.js", "Vercel", "Supabase", "OpenAI", "Stripe", "PostGIS"],
                "revenue_model": "SaaS subscription + marketplace take-rate",
                "mvp_steps": ["Define core logistics workflow", "Build driver/restaurant dashboard", "Launch in 1 city", "Add AI route optimization"],
                "mistakes_to_avoid": ["Overbuilding logistics", "Ignoring unit economics per order", "Premature multi-city expansion"],
                "estimated_market_size": "$50B+ food delivery logistics SaaS",
                "estimated_capital_required_usd": 8000,
                "time_to_mvp_weeks": 6,
            },
            "99dresses": {
                "market_potential_score": 78,
                "difficulty_rating": "medium",
                "scalability_rating": "high",
                "suggested_tech_stack": ["Next.js", "Vercel", "Supabase", "DeepSeek", "Stripe", "Resend"],
                "revenue_model": "Transaction fee + seller subscription",
                "mvp_steps": ["Build peer-to-peer listing flow", "Add AI photo enhancement", "Launch waitlist", "Integrate shipping API"],
                "mistakes_to_avoid": ["Holding inventory", "Manual quality control", "Ignoring return logistics"],
                "estimated_market_size": "$20B+ fashion resale",
                "estimated_capital_required_usd": 5000,
                "time_to_mvp_weeks": 4,
            },
            "arivale": {
                "market_potential_score": 72,
                "difficulty_rating": "hard",
                "scalability_rating": "medium",
                "suggested_tech_stack": ["Next.js", "Vercel", "Supabase", "OpenAI", "FHIR", "HIPAA-compliant hosting"],
                "revenue_model": "B2B SaaS to clinics + consumer subscription",
                "mvp_steps": ["Build compliant data pipeline", "Create biomarker dashboard", "Pilot with 1 clinic", "Add AI health coach"],
                "mistakes_to_avoid": ["Skipping compliance", "Direct-to-consumer without clinician loop", "Overpromising outcomes"],
                "estimated_market_size": "$30B+ preventive health",
                "estimated_capital_required_usd": 15000,
                "time_to_mvp_weeks": 12,
            },
            "juju": {
                "market_potential_score": 82,
                "difficulty_rating": "easy",
                "scalability_rating": "high",
                "suggested_tech_stack": ["Next.js", "Vercel", "Supabase", "DeepSeek", "Stripe", "pgvector"],
                "revenue_model": "Affiliate + SaaS subscription for recruiters",
                "mvp_steps": ["Aggregate job feeds via API", "Add AI resume matcher", "Launch Chrome extension", "Recruiter dashboard"],
                "mistakes_to_avoid": ["Building own ATS", "Ignoring SEO", "Manual curation"],
                "estimated_market_size": "$10B+ job search",
                "estimated_capital_required_usd": 3000,
                "time_to_mvp_weeks": 3,
            },
            "skillshare_clone": {
                "market_potential_score": 75,
                "difficulty_rating": "medium",
                "scalability_rating": "high",
                "suggested_tech_stack": ["Next.js", "Vercel", "Supabase", "OpenAI Whisper", "Mux", "Stripe"],
                "revenue_model": "Creator revenue share + enterprise licenses",
                "mvp_steps": ["Build video upload/transcode", "AI chaptering + search", "Creator studio", "Corporate LMS integration"],
                "mistakes_to_avoid": ["Producing content yourself", "Ignoring creator economics", "Feature bloat"],
                "estimated_market_size": "$15B+ creator education",
                "estimated_capital_required_usd": 7000,
                "time_to_mvp_weeks": 5,
            },
        }
        return plans.get(startup_id)

def save_opportunities(opps: list[RebuildOpportunity], filepath: Path):
    data = [asdict(o) for o in opps]
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_opportunities(filepath: Path) -> list[RebuildOpportunity]:
    if not filepath.exists():
        return []
    data = json.loads(filepath.read_text(encoding="utf-8"))
    return [RebuildOpportunity(**d) for d in data]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Loot Drop 情报挖掘")
    parser.add_argument("--max", type=int, default=20, help="最大返回数")
    parser.add_argument("--output", type=str, default="rebuild_opportunities.json", help="输出文件")
    args = parser.parse_args()

    intel = LootDropIntel()
    print("[*] 诊断 MCP 连接...")
    diag = intel.diagnose()
    print(f"    {diag}")

    print("[*] 挖掘可重建项目...")
    opps = intel.find_rebuildable_gems(max_results=args.max)

    out_path = INTEL_DIR / args.output
    save_opportunities(opps, out_path)
    print(f"[+] 发现 {len(opps)} 个高价值重建机会，已保存到 {out_path}")
    for i, o in enumerate(opps[:5], 1):
        print(f"  {i}. {o.startup.name} ({o.startup.sector}) - 市场潜力 {o.startup.rebuild_plan.get('market_potential_score', 'N/A') if o.startup.rebuild_plan else 'N/A'} - 需资金 ${o.capital_required_usd:,.0f} - MVP {o.time_to_mvp_weeks}周")