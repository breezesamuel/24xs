# -*- coding: utf-8 -*-
"""全局配置：路径、目标、行业库、报价库。零外部依赖。"""
from __future__ import annotations

import json
import os
from pathlib import Path

# ---------------------------------------------------------------- 路径
ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = ROOT / "01_引擎"
OUT_DIR = ROOT / "99_产出"
DATA_DIR = ROOT / "99_产出" / "_data"
REPORT_DIR = OUT_DIR / "报告"
LEAD_DIR = OUT_DIR / "获客名单"
CORPUS_DIR = OUT_DIR / "内容语料"
FIN_DIR = OUT_DIR / "财务"
DB_PATH = DATA_DIR / "factory.sqlite3"

for _d in (OUT_DIR, DATA_DIR, REPORT_DIR, LEAD_DIR, CORPUS_DIR, FIN_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 经营目标
# 唯一北极星：6 个月内 1000 万元进账（GM 定，AI 不改）
TARGET_CNY = 10_000_000
HORIZON_DAYS = 180
START_DATE = "2026-09-30"          # 第 52 次轮询当天
CURRENCY = "CNY"

# ---------------------------------------------------------------- 人工成本口径
# 用于报价与分账，避免拍脑袋
COST = {
    "pm_daysalary": 1800,        # 项目经理 人天成本
    "arch_daysalary": 3000,      # 架构师 人天成本
    "writer_daysalary": 1200,    # 内容主笔 人天成本
    "dev_daysalary": 2600,       # 开发 人天成本
    "ops_daysalary": 900,        # 运营 人天成本
    "api_cny_per_1k_token": 0.003,  # 国产大模型约 1-4 元/百万 token，取中位 3 元/百万 = 0.003 元/千 token
    "tax_rate": 0.06,            # 增值税 6%（技术服务）
}

# ---------------------------------------------------------------- 报价库（2026 公开行情）
# 来源：2026-06~2026-09 国内公开报价整理，见 06_情报/02_竞品与报价情报.md
PRICING = {
    "GEO_SaaS":       {"entry": 798,   "pro": 4464,   "ent": 17548,  "unit": "元/年"},
    "GEO_run":        {"starter": 15000, "pro": 45000, "ent": 150000, "unit": "元/年"},
    "GEO_full":       {"mid": 100000,  "large": 300000, "group": 800000, "unit": "元/年"},
    "AGENT_pilot":    {"light": 50000,  "cross": 220000, "group": 750000, "unit": "元/项目"},
    "AGENT_retainer": {"basic": 15000,  "adv": 35000, "annual": 220000, "unit": "元/月"},
    "TRAIN_cohort":   {"online": 19800, "camp": 68000, "inhouse": 120000, "unit": "元/期"},
}

# ---------------------------------------------------------------- 垂直行业库
# 每个行业 = 一个可复制的交付包。GPO 原则：宁可 3 个行业做到 90 分，不做 30 个 40 分。
INDUSTRIES = [
    {
        "key": "home_improvement",
        "name": "家装/装修",
        "buyer": "老板本人（决策链最短）",
        "budget": 3e4,
        "pain": [
            "客单价高但线上获客贵，一条有效线索 300-800 元",
            "客户比价期长达 2-3 个月，销售反复被问同样的问题",
            "老板 IP 没做起来，抖音/小红书有曝光但接不住咨询",
        ],
        "ai_scenarios": [
            ("量房/报价单自动整理", "把销售在微信里发的语音/照片自动转成标准报价单，单次省 40 分钟"),
            ("客户提问知识库", "把 300 个历史客户问题做成知识库，客服首响从 2 小时到 30 秒"),
            ("老板 IP 短视频流水线", "每周 5 条口播稿，从客户真实提问自动生成"),
        ],
        "proof_metric": "单条线索成本下降 50%，成交周期缩短 30%",
        "risk": "强季节性（春节后/装修季）",
        "channels": ["小红书", "抖音", "抖音本地生活", "美团/大众点评", "微信视频号"],
        "avg_ticket": 3.5e4,
        "sales_cycle_days": 21,
    },
    {
        "key": "legal",
        "name": "律师/律所",
        "buyer": "主任律师",
        "budget": 8e4,
        "pain": [
            "内容获客严重依赖个人品牌，主任一停更线索就断",
            "专业内容检索难，潜在客户问的都是长尾问题",
            "AI 幻觉导致法律意见表述风险，需要人工复核卡点",
        ],
        "ai_scenarios": [
            ("案件要素抽取", "从起诉状/合同里抽要素，30 分钟压缩到 3 分钟"),
            ("法条与类案检索助手", "带出处引用，人工确认后使用"),
            ("主任 IP 内容工厂", "把咨询高频问题变成科普内容"),
        ],
        "proof_metric": "内容产能 3 倍，AI 回答中的品牌提及率进前 3",
        "risk": "合规红线，必须人工复核环节",
        "channels": ["知乎", "公众号", "抖音", "小红书"],
        "avg_ticket": 8e4,
        "sales_cycle_days": 30,
    },
    {
        "key": "cross_border",
        "name": "跨境电商",
        "buyer": "运营负责人/老板",
        "budget": 12e4,
        "pain": [
            "选品/listing 效率低，团队 3 人产出 30 个 SKU",
            "客服时区覆盖不全，差评集中在响应慢",
            "广告 ROAS 下滑，亟需新流量入口",
        ],
        "ai_scenarios": [
            ("多语种 listing 批量生成 + 合规校验", "英/日/德/西同步产出"),
            ("AI 客服多时区值守", "夜间与周末不掉线"),
            ("评论与退货原因聚类", "每周自动出质量报告"),
        ],
        "proof_metric": "listing 产出提速 5 倍，客服响应 <5 分钟",
        "risk": "平台合规，改文案需留档",
        "channels": ["官网/独立站", "LinkedIn", "YouTube", "行业站", "Google 目录"],
        "avg_ticket": 12e4,
        "sales_cycle_days": 14,
    },
    {
        "key": "local_service",
        "name": "本地生活（教培/健身/汽修）",
        "buyer": "门店老板",
        "budget": 1.2e4,
        "pain": [
            "客户只在附近找，靠口碑和团购，但没有复购沉淀",
            "群里发的优惠被薅羊毛，非目标客占一半",
            "店员不会拍内容，账号常年停更",
        ],
        "ai_scenarios": [
            ("门店内容日历", "每周 5 条图文+2条短视频，含团购文案"),
            ("私域自动回复", "社群/企微问题自动应答 + 到店提醒"),
            ("老客召回脚本", "按消费周期自动发个性化召回"),
        ],
        "proof_metric": "到店咨询量 +30%，员工内容产出从 0 到每周 7 条",
        "risk": "单店预算低，必须走标准化小包 + 加盟式渠道",
        "avg_ticket": 1.2e4,
        "sales_cycle_days": 7,
    },
    {
        "key": "manufacturing",
        "name": "制造业（工业品/设备）",
        "buyer": "市场总监 / 外贸负责人",
        "budget": 25e4,
        "pain": [
            "一个有效询盘成本 2000-5000 元，销售周期 3-9 个月",
            "技术参数埋在 PDF 和图纸里，AI 答不上来",
            "官网常年不更新，AI 搜索里完全不被提及",
        ],
        "ai_scenarios": [
            ("参数知识库 + Schema 结构化", "让 AI 能引用你的规格而不是编"),
            ("询盘分级与自动回复", "技术问题自动分类并路由给对应工程师"),
            ("多语种技术白皮书", "英/西/阿语，面向海外买家提问"),
        ],
        "proof_metric": "询盘量月均 +40%，单询盘成本下降 50%",
        "risk": "决策链长，IDC 需覆盖到 6 个月",
        "channels": ["行业门户", "展会", "Google", "LinkedIn", "行业协会"],
        "avg_ticket": 25e4,
        "sales_cycle_days": 60,
    },
]

# ---------------------------------------------------------------- GEO 方法论白帽三件套
# 复利来源：资产一旦建好，每次交付边际成本递减
GEO_PLAYBOOK = {
    "audit": "问题库构建（按行业真实提问聚类，覆盖 决策型/对比型/价格型/避坑型）",
    "build": "结构化语料：FAQ 知识库 + 参数对比表 + Schema 标记 + 案例白皮书",
    "distribute": "权威信源分发：官网/知乎/公众号/行业站/百科 + 问答素材",
    "monitor": "多平台提及率监测 + 竞品异动告警 + 月度归因复盘",
}

# ---------------------------------------------------------------- 引擎参数
ENGINE = {
    "geo_platforms": ["DeepSeek", "豆包", "Kimi", "元宝", "通义", "ChatGPT", "Perplexity", "Gemini"],
    "geo_intents": ["推荐型", "对比型", "价格型", "避坑型", "教程型"],
    "sample_per_industry": 60,        # 每个行业默认采样问题数
    "lead_daily_target": 40,          # 每日新增潜客
    "outreach_per_day": 60,
}


def ensure_dirs() -> None:
    for d in (OUT_DIR, DATA_DIR, REPORT_DIR, LEAD_DIR, CORPUS_DIR, FIN_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load(path: Path, default=None):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default if default is not None else {}


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def money(x: float) -> str:
    return f"{x:,.0f}"


_ILLEGAL = '<>:"/\\|?*'


def safe_name(s: str, limit: int = 40) -> str:
    """把任意业务名称转成安全的文件名（Windows 禁用 / \\ : * ? " < > |，并限长）。"""
    out = "".join("_" if ch in _ILLEGAL or ord(ch) < 32 else ch for ch in str(s))
    out = out.strip(" .")
    out = out.replace("/", "-").replace("\\", "-")
    return (out or "unnamed")[:limit]


if __name__ == "__main__":
    ensure_dirs()
    print("engine ready")
    print("ROOT      :", ROOT)
    print("OUT_DIR   :", OUT_DIR)
    print("DB        :", DB_PATH)
    print("目标      :", money(TARGET_CNY), CURRENCY, "/", HORIZON_DAYS, "天")
    print("行业数    :", len(INDUSTRIES))
