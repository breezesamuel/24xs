// BDS Platform TypeScript/JavaScript SDK
// Usage: 
// import { BDSClient } from "bds-js-sdk";
// const client = new BDSClient({ apiKey: "sk_live_xxx", baseUrl: "https://geo-audit-24xs.vercel.app" });

export interface Asset {
  asset_id: string;
  type: string;
  name: string;
  source: string;
  proof: string;
  proof_type: string;
  price_cny_ref: number;
  price_cny_floor: number;
  deliverable: string;
  tags: string[];
  files: string[];
}

export interface PurchaseResponse {
  ok: boolean;
  checkout_url?: string;
  payment_url?: string;
  purchase_id?: string;
  error?: string;
}

export interface DeliveryResponse {
  ok: boolean;
  download_url?: string;
  expires_at?: string;
  error?: string;
}

export interface VerificationResult {
  ok: boolean;
  match: boolean;
  computed?: string;
  error?: string;
}

export interface SearchParams {
  q?: string;
  type?: string;
  limit?: number;
}

export interface PricingParams {
  asset_type?: string;
  qty?: number;
  bundle?: string;
  tier?: string;
}

export interface PurchaseParams {
  asset_id: string;
  qty?: number;
  bundle?: string;
  amount_cny?: number;
}

export interface PricingResult {
  ok: boolean;
  asset_type?: string;
  qty?: number;
  unit_price?: number;
  discount?: number;
  final_unit_price?: number;
  total?: number;
  tier_pricing?: any;
}

export interface CustomerProfile {
  customer_id: string;
  email: string;
  company_name: string;
  tier: string;
  status: string;
  credit_balance: number;
  total_spent: number;
  total_assets_purchased: number;
  billing_cycle: string;
  created_at: string;
}

export interface CreditsInfo {
  balance: number;
  tier: string;
  included_credits: number;
  used_this_month: number;
  remaining: number;
  utilization_pct: number;
  overage_rate: number;
  renews_at: string;
}

export interface PurchaseRecord {
  purchase_id: string;
  asset_ids: string[];
  bundle_id?: string;
  license_type: string;
  amount_cny: number;
  credits_used: number;
  status: string;
  payment_txn_id: string;
  created_at: string;
  completed_at?: string;
  delivery_status: string;
  delivery_url?: string;
  delivery_expires_at?: string;
}

export interface ApiKey {
  key_id: string;
  name: string;
  permissions: string[];
  rate_limit: number;
  status: string;
  created_at: string;
  last_used_at?: string;
  expires_at?: string;
}

export interface Invoice {
  invoice_id: string;
  purchase_id: string;
  amount_cny: number;
  tax_cny: number;
  status: string;
  issued_at: string;
  pdf_url: string;
}

export interface UsageRecord {
  date: string;
  api_calls: number;
  search_queries: number;
  assets_viewed: number;
  credits_consumed: number;
}

export interface HealthCheck {
  ok: boolean;
  status: string;
  timestamp: string;
  checks: Record<string, any>;
}

export interface Metrics {
  ok: boolean;
  timestamp: string;
  metrics: {
    api: { requests_5m: number; errors_5m: number; avg_latency_ms: number; p95_ms: number };
    registry: { total_assets: number; real_assets: number; variants: number };
    search: { queries_5m: number; avg_results: number; click_through: number };
    payments: { pending: number; completed_24h: number; failed_24h: number };
    customers: { active_24h: number; paying: number; credit_utilization_avg: number };
  };
}

export interface Alerts {
  ok: boolean;
  alerts: Array<{
    id: string;
    rule: string;
    status: string;
    last_check: string;
    triggered?: string;
    details?: string;
  }>;
}

export class BDSClient {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;
  private maxRetries: number;

  constructor(options: { apiKey: string; baseUrl?: string; timeout?: number; maxRetries?: number }) {
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl || "https://geo-audit-24xs.vercel.app").replace(/\/$/, "");
    this.timeout = options.timeout || 30000;
    this.maxRetries = options.maxRetries || 3;
  }

  private async request<T>(method: string, path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Authorization": `Bearer ${this.apiKey}`,
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> || {})
    };

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(url, {
          ...options,
          method,
          headers,
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (response.status === 429) {
          await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 1000));
          continue;
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json() as T;
      } catch (e) {
        if (attempt === this.maxRetries - 1) throw e;
        await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 1000));
      }
    }
    throw new Error("Max retries exceeded");
  }

  // ========== Asset Discovery ==========
  async listAssets(limit = 100, offset = 0) {
    return this.request<{ ok: boolean; total: number; limit: number; offset: number }>(
      "GET", `/api/assets?limit=${limit}&offset=${offset}`
    );
  }

  async searchAssets(params: SearchParams) {
    const q = new URLSearchParams();
    if (params.q) q.set("q", params.q);
    if (params.type) q.set("type", params.type);
    if (params.limit) q.set("limit", params.limit.toString());
    return this.request<{ ok: boolean; sample?: any[]; assets?: any[] }>("GET", `/api/search?${q.toString()}`);
  }

  // ========== Verification ==========
  async verifyProof(proof: string, data: any): Promise<VerificationResult> {
    return this.request<VerificationResult>("POST", "/api/verify", {
      body: JSON.stringify({ proof, data })
    });
  }

  async verifyChain(proof: string, parentProof: string, variantIndex: number): Promise<VerificationResult> {
    return this.request<VerificationResult>("POST", "/api/verify", {
      body: JSON.stringify({ proof, parent_proof: parentProof, variant_index: variantIndex })
    });
  }

  // ========== Pricing & Purchase ==========
  async getPricing(params: PricingParams): Promise<PricingResult> {
    const q = new URLSearchParams();
    if (params.asset_type) q.set("asset_type", params.asset_type);
    if (params.qty) q.set("qty", params.qty.toString());
    if (params.bundle) q.set("bundle", params.bundle);
    if (params.tier) q.set("tier", params.tier);
    return this.request<PricingResult>("GET", `/api/pricing?${q.toString()}`);
  }

  async purchase(params: PurchaseParams): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>("POST", "/api/purchase", {
      body: JSON.stringify(params)
    });
  }

  async checkDelivery(purchaseId: string, txnId: string): Promise<DeliveryResponse> {
    return this.request<DeliveryResponse>("POST", "/api/deliver", {
      body: JSON.stringify({ purchase_id: purchaseId, txn_id: txnId })
    });
  }

  // ========== Customer Portal ==========
  async getProfile(): Promise<CustomerProfile> {
    const result = await this.request<{ ok: boolean; data: CustomerProfile }>("GET", "/api/portal/profile");
    return result.data;
  }

  async getCredits(): Promise<CreditsInfo> {
    const result = await this.request<{ ok: boolean; data: CreditsInfo }>("GET", "/api/portal/credits");
    return result.data;
  }

  async listPurchases(page = 1, limit = 20): Promise<{ ok: boolean; data: PurchaseRecord[]; total: number; page: number; limit: number }> {
    return this.request("GET", `/api/portal/purchases?page=${page}&limit=${limit}`);
  }

  async getPurchase(purchaseId: string): Promise<PurchaseRecord> {
    const result = await this.request<{ ok: boolean; data: PurchaseRecord }>("GET", `/api/portal/purchases/${purchaseId}`);
    return result.data;
  }

  async redeliver(purchaseId: string): Promise<DeliveryResponse> {
    return this.request<DeliveryResponse>("POST", `/api/portal/purchases/${purchaseId}/redeliver`);
  }

  async listApiKeys(): Promise<ApiKey[]> {
    const result = await this.request<{ ok: boolean; data: ApiKey[] }>("GET", "/api/portal/api-keys");
    return result.data;
  }

  async createApiKey(name: string, permissions: string[] = ["read"], rateLimit = 60): Promise<{ ok: boolean; data: ApiKey & { api_key: string } }> {
    return this.request("POST", "/api/portal/api-keys", {
      body: JSON.stringify({ name, permissions, rate_limit: rateLimit })
    });
  }

  async revokeApiKey(keyId: string): Promise<{ ok: boolean; key_id: string; status: string }> {
    return this.request("DELETE", `/api/portal/api-keys/${keyId}`);
  }

  async listInvoices(): Promise<Invoice[]> {
    const result = await this.request<{ ok: boolean; data: Invoice[] }>("GET", "/api/portal/invoices");
    return result.data;
  }

  async getUsage(days = 30): Promise<UsageRecord[]> {
    const result = await this.request<{ ok: boolean; data: UsageRecord[] }>("GET", `/api/portal/usage?days=${days}`);
    return result.data;
  }

  async upgradeTier(tier: "starter" | "professional" | "enterprise"): Promise<{ ok: boolean; customer_id: string; new_tier: string; effective_at: string; proration_credit: number }> {
    return this.request("POST", "/api/portal/upgrade", {
      body: JSON.stringify({ tier })
    });
  }

  // ========== Admin ==========
  async adminDashboard() {
    return this.request("GET", "/api/admin/dashboard");
  }

  async adminListCustomers(page = 1, limit = 20, search = "") {
    return this.request("GET", `/api/admin/customers?page=${page}&limit=${limit}&search=${encodeURIComponent(search)}`);
  }

  async adminGetCustomer(customerId: string) {
    return this.request("GET", `/api/admin/customers/${customerId}`);
  }

  async adminSuspendCustomer(customerId: string) {
    return this.request("POST", `/api/admin/customers/${customerId}/suspend`);
  }

  async adminCreditCustomer(customerId: string, amount: number) {
    return this.request("POST", `/api/admin/customers/${customerId}/credits`, {
      body: JSON.stringify({ amount })
    });
  }

  // ========== Monitoring ==========
  async healthCheck(): Promise<HealthCheck> {
    return this.request("GET", "/api/monitoring?action=health");
  }

  async getMetrics(): Promise<Metrics> {
    return this.request("GET", "/api/monitoring?action=metrics");
  }

  async getAlerts(): Promise<Alerts> {
    return this.request("GET", "/api/monitoring?action=alerts");
  }
}

// Default export for CommonJS/ESM compatibility
export default BDSClient;

// Auto-detect environment
if (typeof window !== "undefined") {
  (window as any).BDSClient = BDSClient;
}
