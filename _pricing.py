# Pricing engine with commercial rules
import json
from pathlib import Path

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

pricing = {
    "version": "2.0",
    "currency": "CNY",
    "rules": {
        # Volume discounts
        "volume_discounts": [
            {"min_qty": 1, "max_qty": 9, "discount": 0.00},
            {"min_qty": 10, "max_qty": 49, "discount": 0.05},
            {"min_qty": 50, "max_qty": 99, "discount": 0.10},
            {"min_qty": 100, "max_qty": 499, "discount": 0.15},
            {"min_qty": 500, "max_qty": 999, "discount": 0.20},
            {"min_qty": 1000, "max_qty": 9999, "discount": 0.25},
            {"min_qty": 10000, "max_qty": None, "discount": 0.30}
        ],
        # Bundle pricing
        "bundles": {
            "ccgp_full_buyer": {
                "name": "采购方全景包",
                "includes": ["buyer_profile", "buyer_notices", "buyer_categories", "buyer_timeline"],
                "base_price": 2000.00,
                "bundle_discount": 0.20,
                "final_price": 1600.00
            },
            "geo_audit_full": {
                "name": "GEO全平台审计包",
                "includes": ["client_audit", "platform_analysis", "competitor_comparison", "action_plan"],
                "base_price": 15000.00,
                "bundle_discount": 0.15,
                "final_price": 12750.00
            },
            "sales_starter_pack": {
                "name": "销售启动包",
                "includes": ["leads_50", "outreach_templates_10", "content_assets_5"],
                "base_price": 15000.00,
                "bundle_discount": 0.25,
                "final_price": 11250.00
            },
            "due_diligence_pack": {
                "name": "尽调合规包",
                "includes": ["entity_dossier", "industry_map", "web_evidence", "crossref_verification"],
                "base_price": 8000.00,
                "bundle_discount": 0.20,
                "final_price": 6400.00
            },
            "market_intel_quarterly": {
                "name": "季度市场情报订阅",
                "includes": ["category_analysis_q", "province_analysis_q", "keyword_trends_q", "agency_ranking_q"],
                "base_price": 50000.00,
                "billing": "quarterly",
                "bundle_discount": 0.10,
                "final_price": 45000.00
            }
        },
        # Subscription tiers
        "subscriptions": {
            "starter": {
                "name": "启动版",
                "monthly_fee": 2999.00,
                "included_credits": 5000,  # credits per month
                "credit_value": 1.00,     # 1 credit = ¥1
                "overage_rate": 0.80,
                "features": ["api_access", "search", "basic_verify", "email_support"]
            },
            "professional": {
                "name": "专业版",
                "monthly_fee": 9999.00,
                "included_credits": 20000,
                "credit_value": 1.00,
                "overage_rate": 0.60,
                "features": ["api_access", "search", "verify", "webhook", "bulk_download", "priority_support", "custom_bundles"]
            },
            "enterprise": {
                "name": "企业版",
                "monthly_fee": 49999.00,
                "included_credits": 100000,
                "credit_value": 1.00,
                "overage_rate": 0.40,
                "features": ["all_pro", "dedicated_api", "sla", "custom_integration", "account_manager", "white_label", "data_export"]
            }
        },
        # Credit system
        "credits": {
            "asset_prices_credits": {
                "招采公告": 5,
                "招采明细行": 10,
                "采购方画像": 500,
                "品类市场分析": 2000,
                "区域市场分析": 1500,
                "项目全周期分析": 3000,
                "代理机构情报": 800,
                "关键词市场分析": 1200,
                "GEO客户端审计报告": 5000,
                "GEO平台分析": 3000,
                "GEO探测": 20,
                "商业线索档案": 200,
                "销售话术模板": 100,
                "内容资产": 50,
                "数据源分析": 500,
                "结构化提取记录": 5,
                "企业全维档案": 100,
                "行业企业图谱": 2000,
                "网页证据快照": 20,
                "实体关联确证": 500
            }
        }
    }
}

with open(OUT / "pricing_engine.json", "w", encoding="utf-8") as f:
    json.dump(pricing, f, ensure_ascii=False, indent=2)

print("Pricing engine saved")
