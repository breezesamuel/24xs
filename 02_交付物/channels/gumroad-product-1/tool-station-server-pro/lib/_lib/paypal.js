// PayPal REST Gateway (Node.js version for Vercel Serverless)
const LIVE_BASE = "https://api-m.paypal.com";
const SANDBOX_BASE = "https://api-m.sandbox.paypal.com";
const FX_CNY_PER_USD = parseFloat(process.env.PAYPAL_FX_CNY_PER_USD || "7.2");

function mask(value, keep = 6) {
  if (!value) return "";
  const s = String(value);
  if (s.length <= keep * 2) return "*".repeat(s.length);
  return `${s.slice(0, keep)}${'*'.repeat(s.length - keep * 2)}${s.slice(-keep)}`;
}

function getAuthHeader(clientId, secret) {
  const raw = Buffer.from(`${clientId}:${secret}`).toString("base64");
  return `Basic ${raw}`;
}

export class PayPalGateway {
  constructor(clientId, secret) {
    this.clientId = clientId;
    this.secret = secret;
    const env = (process.env.PAYPAL_ENV || "").toLowerCase();
    this.baseUrl = env === "sandbox" ? SANDBOX_BASE : LIVE_BASE;
    this.env = env === "sandbox" ? "sandbox" : "live";
    this._tokenCache = null;
  }

  async getAccessToken() {
    if (!this.clientId || !this.secret) {
      return { status: "config_missing", error: "PayPal client_id/secret not configured" };
    }
    const url = `${this.baseUrl}/v1/oauth2/token`;
    const headers = {
      Authorization: getAuthHeader(this.clientId, this.secret),
      "Content-Type": "application/x-www-form-urlencoded",
    };
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers,
        body: "grant_type=client_credentials",
      });
      const data = await resp.json();
      if (!resp.ok) {
        return { status: "error", http: resp.status, error: JSON.stringify(data).slice(0, 300) };
      }
      this._tokenCache = data;
      return {
        status: "ok",
        token_type: data.token_type,
        expires_in: data.expires_in,
        app_id: data.app_id,
        scope: data.scope,
        access_token: data.access_token,
      };
    } catch (e) {
      return { status: "error", error: String(e) };
    }
  }

  async _bearer() {
    if (!this._tokenCache?.access_token) {
      const r = await this.getAccessToken();
      if (r.status !== "ok") return null;
    }
    return this._tokenCache.access_token;
  }

  async verifyCredentials() {
    const r = await this.getAccessToken();
    if (r.status !== "ok") {
      return { status: r.status, env: this.env, error: r.error, http: r.http };
    }
    return {
      status: "ok",
      env: this.env,
      base_url: this.baseUrl,
      token_type: r.token_type,
      expires_in: r.expires_in,
      app_id: r.app_id,
      client_id: mask(this.clientId.slice(0, 6), 3),
    };
  }

  async createOrder({ amountUsd, currency = "USD", description = "", customId = "", referenceId = "", returnUrl, cancelUrl }) {
    const token = await this._bearer();
    if (!token) return { status: "error", error: "Failed to get PayPal access token" };
    const url = `${this.baseUrl}/v2/checkout/orders`;
    const payload = {
      intent: "CAPTURE",
      purchase_units: [{
        amount: { currency_code: currency, value: amountUsd.toFixed(2) },
        description: description.slice(0, 127),
        custom_id: customId.slice(0, 127),
        reference_id: referenceId.slice(0, 127),
      }],
      application_context: {
        brand_name: "AI Money Platform",
        user_action: "PAY_NOW",
        return_url: returnUrl,
        cancel_url: cancelUrl,
      },
    };
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        return { status: "error", http: resp.status, error: JSON.stringify(data).slice(0, 300) };
      }
      const approve = (data.links || []).find(l => ["approve", "payer-action"].includes(l.rel))?.href || null;
      return {
        status: "created",
        order_id: data.id,
        approve_url: approve,
        raw_status: data.status,
        env: this.env,
        currency,
        amount: amountUsd.toFixed(2),
      };
    } catch (e) {
      return { status: "error", error: String(e) };
    }
  }

  async captureOrder(orderId) {
    const token = await this._bearer();
    if (!token) return { status: "error", error: "Failed to get PayPal access token" };
    const url = `${this.baseUrl}/v2/checkout/orders/${orderId}/capture`;
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: "{}",
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        return { status: "error", http: resp.status, error: JSON.stringify(data).slice(0, 300) };
      }
      return {
        status: "completed",
        order_id: orderId,
        raw_status: data.status,
        env: this.env,
        capture: this._extractCapture(data),
      };
    } catch (e) {
      return { status: "error", error: String(e) };
    }
  }

  _extractCapture(data) {
    try {
      const pu = (data.purchase_units || [{}])[0];
      const cap = ((pu.payments || {}).captures || [{}])[0];
      return {
        id: cap.id,
        status: cap.status,
        amount: (cap.amount || {}).value,
        currency: (cap.amount || {}).currency_code,
      };
    } catch {
      return {};
    }
  }

  /**
   * 只读查单：返回订单当前状态（CREATED / APPROVED / COMPLETED / VOIDED …）。
   * 用途: 客户页不用手动刷新 —— 前端轮询本接口即可自动确认"已付款"。
   */
  async getOrder(orderId) {
    const token = await this._bearer();
    if (!token) return { status: "error", error: "Failed to get PayPal access token" };
    const url = `${this.baseUrl}/v2/checkout/orders/${encodeURIComponent(orderId)}`;
    try {
      const resp = await fetch(url, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        return { status: "error", http: resp.status, error: JSON.stringify(data).slice(0, 200) };
      }
      const pu = (data.purchase_units || [{}])[0];
      return {
        status: data.status || "unknown",
        order_id: data.id,
        completed: data.status === "COMPLETED",
        payer: (pu.payer || {}).email_address || null,
        custom_id: pu.custom_id || null,
        reference_id: pu.reference_id || null,
        capture: this._extractCapture(data),
        env: this.env,
      };
    } catch (e) {
      return { status: "error", error: String(e) };
    }
  }
}

export function cnyToUsd(priceCny) {
  return Math.round(priceCny / FX_CNY_PER_USD * 100) / 100;
}