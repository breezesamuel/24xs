const { checkEntitlement, consumeEntitlement, getCustomer, saveCustomer, loadDb } = require("../lib/entitlements.js");

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  [PASS] ${message}`);
  } else {
    failed++;
    console.log(`  [FAIL] ${message}`);
  }
}

async function testEntitlementCheck() {
  console.log("\n--- 权益校验测试 ---");
  const result = await checkEntitlement({ customerId: "NONEXISTENT", action: "search", cost: 1 });
  assert(!result.allowed, "不存在的客户应被拒绝");
  assert(result.code === 401, "不存在的客户返回 401");
}

async function testConsumeEntitlement() {
  console.log("\n--- 积分扣减测试 ---");
  const db = loadDb();
  const testCustomer = {
    customer_id: "TEST-CUSTOMER-001",
    email: "test@example.com",
    tier: "professional",
    status: "active",
    billing_cycle: "monthly",
    included_credits: 100,
    used_this_month: 0,
    credit_balance: 100,
    renews_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  };
  db.customers.push(testCustomer);
  const { saveDb } = require("../lib/entitlements.js");
  saveDb(db);

  const result = await consumeEntitlement({ customerId: "TEST-CUSTOMER-001", action: "search", cost: 1 });
  assert(result.allowed, "有效客户应允许消费");
  assert(result.consumed === 1, "消费积分数正确");

  const customer = await getCustomer("TEST-CUSTOMER-001");
  assert(customer.used_this_month === 1, "已用积分更新正确");
}

async function testInsufficientCredits() {
  console.log("\n--- 积分不足测试 ---");
  const db = loadDb();
  const testCustomer = {
    customer_id: "TEST-CUSTOMER-002",
    email: "test2@example.com",
    tier: "starter",
    status: "active",
    billing_cycle: "monthly",
    included_credits: 10,
    used_this_month: 10,
    credit_balance: 10,
    renews_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  };
  db.customers.push(testCustomer);
  const { saveDb } = require("../lib/entitlements.js");
  saveDb(db);

  const result = await checkEntitlement({ customerId: "TEST-CUSTOMER-002", action: "search", cost: 1 });
  assert(!result.allowed, "积分不足应被拒绝");
  assert(result.code === 402, "积分不足返回 402");
}

async function testExpiredSubscription() {
  console.log("\n--- 订阅过期测试 ---");
  const db = loadDb();
  const testCustomer = {
    customer_id: "TEST-CUSTOMER-003",
    email: "test3@example.com",
    tier: "professional",
    status: "expired",
    billing_cycle: "monthly",
    included_credits: 100,
    used_this_month: 0,
    credit_balance: 100,
    renews_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  };
  db.customers.push(testCustomer);
  const { saveDb } = require("../lib/entitlements.js");
  saveDb(db);

  const result = await checkEntitlement({ customerId: "TEST-CUSTOMER-003", action: "search", cost: 1 });
  assert(!result.allowed, "过期订阅应被拒绝");
  assert(result.code === 403, "过期订阅返回 403");
}

async function testMonthlyReset() {
  console.log("\n--- 月度重置测试 ---");
  const db = loadDb();
  const testCustomer = {
    customer_id: "TEST-CUSTOMER-004",
    email: "test4@example.com",
    tier: "professional",
    status: "active",
    billing_cycle: "monthly",
    included_credits: 100,
    used_this_month: 50,
    credit_balance: 100,
    renews_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  };
  db.customers.push(testCustomer);
  const { saveDb } = require("../lib/entitlements.js");
  saveDb(db);

  const result = await checkEntitlement({ customerId: "TEST-CUSTOMER-004", action: "search", cost: 1 });
  assert(result.allowed, "过期续费日期应触发重置");
  const customer = await getCustomer("TEST-CUSTOMER-004");
  assert(customer.used_this_month === 0, "重置后已用积分为 0");
}

async function main() {
  console.log("========================================");
  console.log("丙大山数字资产平台 - 集成测试");
  console.log("========================================");

  await testEntitlementCheck();
  await testConsumeEntitlement();
  await testInsufficientCredits();
  await testExpiredSubscription();
  await testMonthlyReset();

  console.log("\n========================================");
  console.log(`结果: ${passed} 通过, ${failed} 失败`);
  console.log("========================================");

  if (failed > 0) {
    process.exit(1);
  }
}

main().catch(e => {
  console.error("测试异常:", e);
  process.exit(1);
});