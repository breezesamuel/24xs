# Generate OpenAPI 3.0 spec for the platform
import json
from pathlib import Path

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

openapi = {
    "openapi": "3.0.3",
    "info": {
        "title": "丙大山数字资产平台 API",
        "version": "2.0.0",
        "description": "商业级数字资产交易平台 - 资产发现、购买、交付、验证、客户门户、管理后台",
        "contact": {"name": "丙大山智能科技", "email": "supi24@163.com"},
        "license": {"name": "Proprietary"}
    },
    "servers": [
        {"url": "https://geo-audit-24xs.vercel.app", "description": "生产环境"},
        {"url": "http://localhost:8787", "description": "本地开发"}
    ],
    "security": [{"BearerAuth": []}],
    "components": {
        "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
        "schemas": {
            "Asset": {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "string", "example": "V-20261003-001234"},
                    "type": {"type": "string", "example": "采购方画像"},
                    "name": {"type": "string", "example": "采购方画像_上海市医疗器械采购中心"},
                    "source": {"type": "string", "example": "11_数据资产/ccgp_production.db:buyer_profile"},
                    "proof": {"type": "string", "example": "a1b2c3d4e5f6..."},
                    "proof_type": {"type": "string", "enum": ["sha256", "sha256_chain"]},
                    "price_cny_ref": {"type": "number", "format": "float", "example": 500.0},
                    "price_cny_floor": {"type": "number", "format": "float", "example": 100.0},
                    "deliverable": {"type": "string", "example": "采购方全维度画像（历史采购、预算、偏好、供应商网络）"},
                    "tags": {"type": "array", "items": {"type": "string"}, "example": ["ccgp", "buyer_profile", "high_value"]},
                    "files": {"type": "array", "items": {"type": "string"}}
                }
            },
            "AssetList": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "total": {"type": "integer", "example": 1056693},
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"}
                }
            },
            "SearchParams": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "关键词"},
                    "type": {"type": "string", "description": "资产类型过滤"},
                    "limit": {"type": "integer", "default": 50, "maximum": 200}
                }
            },
            "SearchResult": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "sample": {"type": "array", "items": {"$ref": "#/components/schemas/Asset"}},
                    "total": {"type": "integer"}
                }
            },
            "VerificationRequest": {
                "type": "object",
                "properties": {
                    "proof": {"type": "string"},
                    "data": {"type": "object"},
                    "parent_proof": {"type": "string"},
                    "variant_index": {"type": "integer"}
                },
                "required": ["proof"]
            },
            "VerificationResult": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "match": {"type": "boolean"},
                    "computed": {"type": "string"},
                    "error": {"type": "string"}
                }
            },
            "PricingRequest": {
                "type": "object",
                "properties": {
                    "asset_type": {"type": "string"},
                    "qty": {"type": "integer", "default": 1},
                    "bundle": {"type": "string"},
                    "tier": {"type": "string", "enum": ["starter", "professional", "enterprise"]}
                }
            },
            "PricingResult": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "asset_type": {"type": "string"},
                    "qty": {"type": "integer"},
                    "unit_price": {"type": "number"},
                    "discount": {"type": "number"},
                    "final_unit_price": {"type": "number"},
                    "total": {"type": "number"},
                    "tier_pricing": {"type": "object"}
                }
            },
            "PurchaseRequest": {
                "type": "object",
                "required": ["asset_id"],
                "properties": {
                    "asset_id": {"type": "string"},
                    "qty": {"type": "integer", "default": 1},
                    "bundle": {"type": "string"},
                    "amount_cny": {"type": "number"}
                }
            },
            "PurchaseResponse": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "checkout_url": {"type": "string", "format": "uri"},
                    "payment_url": {"type": "string", "format": "uri"},
                    "purchase_id": {"type": "string"},
                    "error": {"type": "string"}
                }
            },
            "DeliveryResponse": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "download_url": {"type": "string", "format": "uri"},
                    "expires_at": {"type": "string", "format": "date-time"},
                    "error": {"type": "string"}
                }
            },
            "CustomerProfile": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "email": {"type": "string"},
                    "company_name": {"type": "string"},
                    "tier": {"type": "string", "enum": ["starter", "professional", "enterprise"]},
                    "status": {"type": "string"},
                    "credit_balance": {"type": "integer"},
                    "total_spent": {"type": "number"},
                    "total_assets_purchased": {"type": "integer"},
                    "billing_cycle": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"}
                }
            },
            "CreditsInfo": {
                "type": "object",
                "properties": {
                    "balance": {"type": "integer"},
                    "tier": {"type": "string"},
                    "included_credits": {"type": "integer"},
                    "used_this_month": {"type": "integer"},
                    "remaining": {"type": "integer"},
                    "utilization_pct": {"type": "number"},
                    "overage_rate": {"type": "number"},
                    "renews_at": {"type": "string", "format": "date-time"}
                }
            },
            "PurchaseRecord": {
                "type": "object",
                "properties": {
                    "purchase_id": {"type": "string"},
                    "asset_ids": {"type": "array", "items": {"type": "string"}},
                    "bundle_id": {"type": "string", "nullable": true},
                    "license_type": {"type": "string"},
                    "amount_cny": {"type": "number"},
                    "credits_used": {"type": "integer"},
                    "status": {"type": "string"},
                    "payment_txn_id": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "completed_at": {"type": "string", "format": "date-time", "nullable": true},
                    "delivery_status": {"type": "string"},
                    "delivery_url": {"type": "string", "format": "uri", "nullable": true},
                    "delivery_expires_at": {"type": "string", "format": "date-time", "nullable": true}
                }
            },
            "ApiKey": {
                "type": "object",
                "properties": {
                    "key_id": {"type": "string"},
                    "name": {"type": "string"},
                    "permissions": {"type": "array", "items": {"type": "string"}},
                    "rate_limit": {"type": "integer"},
                    "status": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "last_used_at": {"type": "string", "format": "date-time", "nullable": true},
                    "expires_at": {"type": "string", "format": "date-time", "nullable": true}
                }
            },
            "Invoice": {
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "string"},
                    "purchase_id": {"type": "string"},
                    "amount_cny": {"type": "number"},
                    "tax_cny": {"type": "number"},
                    "status": {"type": "string"},
                    "issued_at": {"type": "string", "format": "date-time"},
                    "pdf_url": {"type": "string", "format": "uri"}
                }
            },
            "UsageRecord": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "api_calls": {"type": "integer"},
                    "search_queries": {"type": "integer"},
                    "assets_viewed": {"type": "integer"},
                    "credits_consumed": {"type": "integer"}
                }
            },
            "Error": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean", "example": false},
                    "error": {"type": "string"}
                }
            },
            "RateLimitInfo": {
                "type": "object",
                "properties": {
                    "allowed": {"type": "boolean"},
                    "minute": {"type": "object", "properties": {"limit": {"type": "integer"}, "remaining": {"type": "integer"}, "reset_in": {"type": "integer"}}},
                    "hour": {"type": "object", "properties": {"limit": {"type": "integer"}, "remaining": {"type": "integer"}, "reset_in": {"type": "integer"}}},
                    "day": {"type": "object", "properties": {"limit": {"type": "integer"}, "remaining": {"type": "integer"}, "reset_in": {"type": "integer"}}},
                    "burst": {"type": "object", "properties": {"limit": {"type": "integer"}, "available": {"type": "integer"}}}
                }
            }
        }
    },
    "paths": {
        "/api/assets": {
            "get": {
                "summary": "获取资产目录",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 100, "maximum": 500}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}}
                ],
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AssetList"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/search": {
            "get": {
                "summary": "全文搜索资产",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}},
                    {"name": "type", "in": "query", "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}}
                ],
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SearchResult"}}}},
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/verify": {
            "post": {
                "summary": "验证资产 Proof",
                "security": [{"BearerAuth": []}],
                "requestBody": {"required": true, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/VerificationRequest"}}}},
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/VerificationResult"}}}},
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/pricing": {
            "get": {
                "summary": "查询动态定价",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "asset_type", "in": "query", "schema": {"type": "string"}},
                    {"name": "qty", "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "bundle", "in": "query", "schema": {"type": "string"}},
                    {"name": "tier", "in": "query", "schema": {"type": "string", "enum": ["starter", "professional", "enterprise"]}}
                ],
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PricingResult"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/purchase": {
            "post": {
                "summary": "发起购买",
                "security": [{"BearerAuth": []}],
                "requestBody": {"required": true, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PurchaseRequest"}}}},
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PurchaseResponse"}}}},
                    "400": {"$ref": "#/components/responses/BadRequest"},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/deliver": {
            "post": {
                "summary": "查询/触发交付",
                "security": [{"BearerAuth": []}],
                "requestBody": {"required": true, "content": {"application/json": {"schema": {"type": "object", "required": ["purchase_id", "txn_id"], "properties": {"purchase_id": {"type": "string"}, "txn_id": {"type": "string"}}}}}},
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DeliveryResponse"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/portal/profile": {
            "get": {
                "summary": "获取客户档案",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CustomerProfile"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/portal/credits": {
            "get": {
                "summary": "获取积分信息",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreditsInfo"}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/portal/purchases": {
            "get": {
                "summary": "列出购买记录",
                "security": [{"BearerAuth": []}],
                "parameters": [
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}}
                ],
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}, "data": {"type": "array", "items": {"$ref": "#/components/schemas/PurchaseRecord"}}, "total": {"type": "integer"}, "page": {"type": "integer"}, "limit": {"type": "integer"}}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/portal/api-keys": {
            "get": {
                "summary": "列出 API Keys",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "成功", "content": {"application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}, "data": {"type": "array", "items": {"$ref": "#/components/schemas/ApiKey"}}}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            },
            "post": {
                "summary": "创建 API Key",
                "security": [{"BearerAuth": []}],
                "requestBody": {"required": true, "content": {"application/json": {"schema": {"type": "object", "properties": {"name": {"type": "string"}, "permissions": {"type": "array", "items": {"type": "string"}}, "rate_limit": {"type": "integer"}}}}}},
                "responses": {
                    "201": {"description": "创建成功", "content": {"application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}, "data": {"$ref": "#/components/schemas/ApiKey"}, "api_key": {"type": "string"}}}}}},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/api/admin/dashboard": {
            "get": {
                "summary": "管理后台仪表盘",
                "security": [{"BearerAuth": []}],
                "responses": {
                    "200": {"description": "成功"},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "403": {"$ref": "#/components/responses/Forbidden"}
                }
            }
        },
        "/api/monitoring": {
            "get": {
                "summary": "系统监控",
                "security": [{"BearerAuth": []}],
                "parameters": [{"name": "action", "in": "query", "schema": {"type": "string", "enum": ["health", "metrics", "alerts"]}}],
                "responses": {
                    "200": {"description": "成功"},
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        }
    },
    "responses": {
        "Unauthorized": {"description": "未授权", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
        "Forbidden": {"description": "禁止访问", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
        "BadRequest": {"description": "请求参数错误", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
        "TooManyRequests": {"description": "限流", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}, "headers": {"X-RateLimit-Retry-After": {"schema": {"type": "integer"}}}}}
    }
}

with open(OUT / "openapi.json", "w", encoding="utf-8") as f:
    json.dump(openapi, f, ensure_ascii=False, indent=2)

print("OpenAPI spec saved to", OUT / "openapi.json")
