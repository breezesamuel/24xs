# Customer management with licensing, usage tracking, access control
import json, hashlib, secrets
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# License types
licenses = {
    "internal-use-license-v1": {
        "name": "内部使用许可",
        "scope": "internal",
        "allowed": ["view", "analyze", "internal_report"],
        "forbidden": ["resell", "redistribute", "public_display", "training_ai"],
        "attribution_required": True,
        "warranty": "none",
        "liability_cap": 0
    },
    "commercial-single-v1": {
        "name": "商业单次使用许可",
        "scope": "commercial_single",
        "allowed": ["view", "analyze", "internal_report", "client_deliverable"],
        "forbidden": ["resell", "redistribute", "public_display", "training_ai", "saas_embedding"],
        "attribution_required": True,
        "warranty": "data_accuracy_best_effort",
        "liability_cap": "purchase_price"
    },
    "commercial-multi-v1": {
        "name": "商业多次使用许可",
        "scope": "commercial_multi",
        "allowed": ["view", "analyze", "internal_report", "client_deliverable", "team_sharing"],
        "forbidden": ["resell", "redistribute", "public_display", "training_ai", "saas_embedding"],
        "attribution_required": True,
        "warranty": "data_accuracy_best_effort",
        "liability_cap": "5x_purchase_price"
    },
    "enterprise-redistribution-v1": {
        "name": "企业再分发许可",
        "scope": "enterprise_redistribution",
        "allowed": ["view", "analyze", "internal_report", "client_deliverable", "team_sharing", "saas_embedding", "derived_products"],
        "forbidden": ["raw_resell", "public_display"],
        "attribution_required": True,
        "warranty": "data_accuracy_sla",
        "liability_cap": "contractual",
        "requires_negotiation": True
    }
}

# Default license per asset type
asset_license_map = {
    "招采公告": "commercial-single-v1",
    "招采明细行": "commercial-single-v1",
    "采购方画像": "commercial-multi-v1",
    "品类市场分析": "commercial-multi-v1",
    "区域市场分析": "commercial-multi-v1",
    "项目全周期分析": "commercial-multi-v1",
    "代理机构情报": "commercial-multi-v1",
    "关键词市场分析": "commercial-multi-v1",
    "GEO客户端审计报告": "commercial-multi-v1",
    "GEO平台分析": "commercial-multi-v1",
    "GEO探测": "commercial-single-v1",
    "商业线索档案": "commercial-multi-v1",
    "销售话术模板": "commercial-multi-v1",
    "内容资产": "commercial-single-v1",
    "数据源分析": "commercial-multi-v1",
    "结构化提取记录": "commercial-single-v1",
    "企业全维档案": "commercial-multi-v1",
    "行业企业图谱": "commercial-multi-v1",
    "网页证据快照": "commercial-single-v1",
    "实体关联确证": "commercial-multi-v1",
    # variants
    "default": "commercial-single-v1"
}

license_registry = {
    "version": "1.0",
    "licenses": licenses,
    "asset_license_map": asset_license_map,
    "issued_licenses": [],  # populated at purchase
    "revoked_licenses": []
}

with open(OUT / "license_registry.json", "w", encoding="utf-8") as f:
    json.dump(license_registry, f, ensure_ascii=False, indent=2)

# Customer database schema
customer_schema = {
    "version": "1.0",
    "tables": {
        "customers": {
            "fields": {
                "customer_id": "string (CUST-YYYYMMDD-XXXXXX)",
                "email": "string (unique)",
                "company_name": "string",
                "contact_name": "string",
                "phone": "string",
                "tier": "string (starter/professional/enterprise)",
                "status": "string (active/suspended/cancelled)",
                "created_at": "iso8601",
                "billing_cycle": "string (monthly/quarterly/annual)",
                "payment_method": "string (moltspay/alipay/wechat/bank)",
                "moltspay_customer_id": "string",
                "credit_balance": "integer",
                "total_spent": "number",
                "total_assets_purchased": "integer"
            },
            "indexes": ["email", "customer_id", "status"]
        },
        "purchases": {
            "fields": {
                "purchase_id": "string (PUR-YYYYMMDD-XXXXXX)",
                "customer_id": "string",
                "asset_ids": "array[string]",
                "bundle_id": "string|null",
                "license_type": "string",
                "amount_cny": "number",
                "credits_used": "integer",
                "status": "string (pending/completed/refunded/failed)",
                "payment_txn_id": "string",
                "created_at": "iso8601",
                "completed_at": "iso8601|null",
                "delivery_status": "string (pending/delivered/expired)",
                "delivery_url": "string|null",
                "delivery_expires_at": "iso8601|null"
            },
            "indexes": ["customer_id", "purchase_id", "status", "payment_txn_id"]
        },
        "usage_logs": {
            "fields": {
                "log_id": "string",
                "customer_id": "string",
                "asset_id": "string",
                "action": "string (view/download/api_call/verify)",
                "timestamp": "iso8601",
                "ip": "string",
                "user_agent": "string",
                "credits_consumed": "integer"
            },
            "indexes": ["customer_id", "asset_id", "timestamp"]
        },
        "api_keys": {
            "fields": {
                "key_id": "string (KEY-XXXXXX)",
                "customer_id": "string",
                "key_hash": "string (sha256)",
                "name": "string",
                "permissions": "array[string]",
                "rate_limit": "integer (req/min)",
                "status": "string (active/revoked)",
                "created_at": "iso8601",
                "last_used_at": "iso8601|null",
                "expires_at": "iso8601|null"
            },
            "indexes": ["customer_id", "key_id", "key_hash"]
        }
    }
}

with open(OUT / "customer_schema.json", "w", encoding="utf-8") as f:
    json.dump(customer_schema, f, ensure_ascii=False, indent=2)

# Customer API endpoints (for CF Pages functions)
print("Customer schema and license registry saved")
