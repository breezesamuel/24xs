const fs = require("fs");
const path = require("path");
const { loadDb, saveDb, getCustomer } = require("../../../lib/entitlements.js");

const REG = path.resolve(__dirname, "../../../11_数据资产/registry_real_verified");

function extractCustomerId(request) {
  const auth = request.headers.get("authorization") || request.headers.get("Authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return request.headers.get("x-customer-id") || null;
}

function isAdmin(customer) {
  if (!customer) return false;
  const adminEmails = ["admin@24xs.com", "supi24@163.com"];
  if (customer.email && adminEmails.includes(customer.email)) return true;
  if (customer.tier === "admin") return true;
  return false;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "list";
  const customerId = extractCustomerId(request);

  if (!customerId) {
    return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }

  const customer = await getCustomer(customerId);
  if (!isAdmin(customer)) {
    return new Response(JSON.stringify({ ok: false, error: "forbidden" }), { status: 403, headers: { "Content-Type": "application/json" } });
  }

  const backupDir = path.join(REG, "backups");
  if (!fs.existsSync(backupDir)) fs.mkdirSync(backupDir, { recursive: true });

  if (action === "list") {
    const backups = [];
    if (fs.existsSync(backupDir)) {
      const files = fs.readdirSync(backupDir);
      for (const file of files) {
        const filePath = path.join(backupDir, file);
        const stats = fs.statSync(filePath);
        backups.push({
          filename: file,
          size_mb: (stats.size / 1024 / 1024).toFixed(2),
          created_at: stats.mtime.toISOString()
        });
      }
    }
    backups.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return new Response(JSON.stringify({ ok: true, data: backups }), { headers: { "Content-Type": "application/json" } });
  }

  if (action === "create" && request.method === "POST") {
    const db = loadDb();
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `backup_${timestamp}.json`;
    const filePath = path.join(backupDir, filename);

    const backup = {
      version: "2.0.0",
      created_at: new Date().toISOString(),
      created_by: customerId,
      data: {
        customers: db.customers || [],
        purchases: db.purchases || [],
        usage_records: (db.usage_records || []).slice(-10000),
        invoices: db.invoices || [],
        audit_logs: (db.audit_logs || []).slice(-10000)
      }
    };

    fs.writeFileSync(filePath, JSON.stringify(backup, null, 2));

    return new Response(JSON.stringify({
      ok: true,
      data: {
        filename,
        size_mb: (fs.statSync(filePath).size / 1024 / 1024).toFixed(2),
        created_at: backup.created_at
      }
    }), { status: 201, headers: { "Content-Type": "application/json" } });
  }

  if (action === "restore" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const { filename } = body;

    if (!filename) {
      return new Response(JSON.stringify({ ok: false, error: "filename_required" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }

    const filePath = path.join(backupDir, filename);
    if (!fs.existsSync(filePath)) {
      return new Response(JSON.stringify({ ok: false, error: "backup_not_found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }

    const backup = JSON.parse(fs.readFileSync(filePath, "utf8"));
    const db = loadDb();

    if (backup.data.customers) db.customers = backup.data.customers;
    if (backup.data.purchases) db.purchases = backup.data.purchases;
    if (backup.data.invoices) db.invoices = backup.data.invoices;

    saveDb(db);

    return new Response(JSON.stringify({
      ok: true,
      data: {
        restored_from: filename,
        restored_at: new Date().toISOString(),
        customers: db.customers.length,
        purchases: db.purchases.length
      }
    }), { headers: { "Content-Type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: false, error: "unknown_action" }), { status: 400, headers: { "Content-Type": "application/json" } });
}