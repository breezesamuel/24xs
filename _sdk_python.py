# Python SDK for the platform
import json, hashlib, hmac, time, uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    import requests
except ImportError:
    requests = None

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

@dataclass
class Asset:
    asset_id: str
    type: str
    name: str
    source: str
    proof: str
    proof_type: str
    price_cny_ref: float
    price_cny_floor: float
    deliverable: str
    tags: List[str]
    files: List[str]

@dataclass
class PurchaseResponse:
    ok: bool
    checkout_url: Optional[str] = None
    payment_url: Optional[str] = None
    purchase_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class DeliveryResponse:
    ok: bool
    download_url: Optional[str] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None

@dataclass
class VerificationResult:
    ok: bool
    match: bool
    computed: Optional[str] = None
    error: Optional[str] = None

class BDSClient:
    """
    丙大山数字资产平台 Python SDK
    
    Usage:
        client = BDSClient(api_key="sk_live_xxx", base_url="https://geo-audit-24xs.vercel.app")
        assets = client.search_assets(q="采购方画像", type="采购方画像", limit=10)
        purchase = client.purchase(asset_id="V-20261003-001234", qty=1)
        delivery = client.verify_delivery(purchase_id="PUR-xxx", txn_id="moltspay_txn_xxx")
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://geo-audit-24xs.vercel.app",
        timeout: int = 30,
        max_retries: int = 3
    ):
        if requests is None:
            raise ImportError("requests library required: pip install requests")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "bds-python-sdk/1.0"
        })
    
    def _request(self, method: str, path: str, **kwargs) -> Dict:
        url = f"{self.base_url}{path}"
        for attempt in range(self.max_retries):
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        raise Exception("Max retries exceeded")
    
    # ========== Asset Discovery ==========
    def list_assets(self, limit: int = 100, offset: int = 0) -> Dict:
        """获取资产目录"""
        return self._request("GET", "/api/assets", params={"limit": limit, "offset": offset})
    
    def search_assets(
        self,
        q: str = "",
        type: str = "",
        limit: int = 50
    ) -> Dict:
        """全文搜索资产"""
        params = {"limit": limit}
        if q: params["q"] = q
        if type: params["type"] = type
        return self._request("GET", "/api/search", params=params)
    
    def get_asset(self, asset_id: str) -> Dict:
        """获取单个资产详情（需遍历或搜索）"""
        return self.search_assets(q=asset_id, limit=1)
    
    # ========== Verification ==========
    def verify_proof(self, proof: str, data: Any) -> VerificationResult:
        """验证单条资产 proof"""
        result = self._request("POST", "/api/verify", json={"proof": proof, "data": data})
        return VerificationResult(**result)
    
    def verify_chain(self, proof: str, parent_proof: str, variant_index: int) -> VerificationResult:
        """验证链式变体 proof"""
        result = self._request("POST", "/api/verify", json={
            "proof": proof,
            "parent_proof": parent_proof,
            "variant_index": variant_index
        })
        return VerificationResult(**result)
    
    def verify_merkle(self, asset_ids: List[str]) -> Dict:
        """批量验证 Merkle proof（需配合注册表顺序）"""
        return self._request("POST", "/api/verify/merkle", json={"asset_ids": asset_ids})
    
    # ========== Purchase & Delivery ==========
    def get_pricing(self, asset_type: str = "", qty: int = 1, bundle: str = "", tier: str = "") -> Dict:
        """获取动态定价"""
        params = {"qty": qty}
        if asset_type: params["asset_type"] = asset_type
        if bundle: params["bundle"] = bundle
        if tier: params["tier"] = tier
        return self._request("GET", "/api/pricing", params=params)
    
    def purchase(
        self,
        asset_id: str,
        qty: int = 1,
        bundle: str = "",
        amount_cny: Optional[float] = None
    ) -> PurchaseResponse:
        """发起购买，返回支付链接"""
        payload = {"asset_id": asset_id, "qty": qty}
        if bundle: payload["bundle"] = bundle
        if amount_cny: payload["amount_cny"] = amount_cny
        result = self._request("POST", "/api/purchase", json=payload)
        return PurchaseResponse(**result)
    
    def check_delivery(self, purchase_id: str, txn_id: str) -> DeliveryResponse:
        """查询交付状态 / 触发交付"""
        result = self._request("POST", "/api/deliver", json={
            "purchase_id": purchase_id,
            "txn_id": txn_id
        })
        return DeliveryResponse(**result)
    
    def redeliver(self, purchase_id: str) -> DeliveryResponse:
        """重新生成下载链接（Portal API）"""
        result = self._request("POST", f"/api/portal/purchases/{purchase_id}/redeliver")
        return DeliveryResponse(**result)
    
    # ========== Customer Portal ==========
    def get_profile(self) -> Dict:
        return self._request("GET", "/api/portal/profile")
    
    def get_credits(self) -> Dict:
        return self._request("GET", "/api/portal/credits")
    
    def list_purchases(self, page: int = 1, limit: int = 20) -> Dict:
        return self._request("GET", "/api/portal/purchases", params={"page": page, "limit": limit})
    
    def get_purchase(self, purchase_id: str) -> Dict:
        return self._request("GET", f"/api/portal/purchases/{purchase_id}")
    
    def list_api_keys(self) -> Dict:
        return self._request("GET", "/api/portal/api-keys")
    
    def create_api_key(self, name: str, permissions: List[str] = None, rate_limit: int = 60) -> Dict:
        return self._request("POST", "/api/portal/api-keys", json={
            "name": name,
            "permissions": permissions or ["read"],
            "rate_limit": rate_limit
        })
    
    def revoke_api_key(self, key_id: str) -> Dict:
        return self._request("DELETE", f"/api/portal/api-keys/{key_id}")
    
    def list_invoices(self) -> Dict:
        return self._request("GET", "/api/portal/invoices")
    
    def get_usage(self, days: int = 30) -> Dict:
        return self._request("GET", "/api/portal/usage", params={"days": days})
    
    def upgrade_tier(self, tier: str) -> Dict:
        return self._request("POST", "/api/portal/upgrade", json={"tier": tier})
    
    # ========== Admin (requires admin token) ==========
    def admin_dashboard(self) -> Dict:
        return self._request("GET", "/api/admin/dashboard")
    
    def admin_list_customers(self, page: int = 1, limit: int = 20, search: str = "") -> Dict:
        return self._request("GET", "/api/admin/customers", params={"page": page, "limit": limit, "search": search})
    
    def admin_get_customer(self, customer_id: str) -> Dict:
        return self._request("GET", f"/api/admin/customers/{customer_id}")
    
    def admin_suspend_customer(self, customer_id: str) -> Dict:
        return self._request("POST", f"/api/admin/customers/{customer_id}/suspend")
    
    def admin_credit_customer(self, customer_id: str, amount: int) -> Dict:
        return self._request("POST", f"/api/admin/customers/{customer_id}/credits", json={"amount": amount})
    
    def admin_list_purchases(self, page: int = 1, limit: int = 20, status: str = "") -> Dict:
        params = {"page": page, "limit": limit}
        if status: params["status"] = status
        return self._request("GET", "/api/admin/purchases", params=params)
    
    def admin_analytics(self) -> Dict:
        return self._request("GET", "/api/admin/analytics")
    
    # ========== Health & Monitoring ==========
    def health_check(self) -> Dict:
        return self._request("GET", "/api/monitoring", params={"action": "health"})
    
    def get_metrics(self) -> Dict:
        return self._request("GET", "/api/monitoring", params={"action": "metrics"})
    
    def get_alerts(self) -> Dict:
        return self._request("GET", "/api/monitoring", params={"action": "alerts"})

# CLI helper
def main():
    import argparse
    parser = argparse.ArgumentParser(description="BDS Platform CLI")
    parser.add_argument("--api-key", required=True, help="API Key (sk_live_xxx)")
    parser.add_argument("--base-url", default="https://geo-audit-24xs.vercel.app")
    sub = parser.add_subparsers(dest="cmd")
    
    # search
    p = sub.add_parser("search", help="搜索资产")
    p.add_argument("-q", "--query", default="")
    p.add_argument("-t", "--type", default="")
    p.add_argument("-l", "--limit", type=int, default=20)
    
    # verify
    p = sub.add_parser("verify", help="验证 proof")
    p.add_argument("--proof", required=True)
    p.add_argument("--data", default="")
    p.add_argument("--parent-proof", default="")
    p.add_argument("--variant-index", type=int, default=0)
    
    # purchase
    p = sub.add_parser("purchase", help="发起购买")
    p.add_argument("--asset-id", required=True)
    p.add_argument("--qty", type=int, default=1)
    p.add_argument("--bundle", default="")
    
    # pricing
    p = sub.add_parser("pricing", help="查询价格")
    p.add_argument("--type", default="")
    p.add_argument("--qty", type=int, default=1)
    p.add_argument("--bundle", default="")
    
    args = parser.parse_args()
    client = BDSClient(args.api_key, args.base_url)
    
    if args.cmd == "search":
        result = client.search_assets(args.query, args.type, args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "verify":
        if args.parent_proof:
            result = client.verify_chain(args.proof, args.parent_proof, args.variant_index)
        else:
            data = json.loads(args.data) if args.data else {}
            result = client.verify_proof(args.proof, data)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    elif args.cmd == "purchase":
        result = client.purchase(args.asset_id, args.qty, args.bundle)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    elif args.cmd == "pricing":
        result = client.get_pricing(args.type, args.qty, args.bundle)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
