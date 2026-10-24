# -*- coding: utf-8 -*-
"""
capital/tests/test_security.py
资金栈安全回归测试：确保敏感数据不再硬编码、关键动作默认关闭
运行：python -X utf8 -m capital.tests.test_security
"""
import json
import os
import re
import sys
import tempfile
import base64
import unittest
from decimal import Decimal
from pathlib import Path

CAPITAL_DIR = Path(__file__).resolve().parent.parent
SWARM_DIR = CAPITAL_DIR.parent
for p in (str(SWARM_DIR), str(CAPITAL_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from capital.payment_gateway import (  # noqa: E402
    AlipayGateway, WechatGateway, PaymentGatewayManager, ConfigCrypto,
)
from capital.dividend_distributor import (  # noqa: E402
    DividendDistributor, Shareholder, SYSTEM_APPROVER_BLOCKLIST,
)
from capital.tax_filer import TaxFiler  # noqa: E402
from capital.capital_allocator import CapitalAllocator, AllocationBucket  # noqa: E402

# 泄露过/曾硬编码的敏感特征：银行卡号、税号、身份证、手机号
BANK_CARD_RE = re.compile(r"\b\d{16,19}\b")
TAX_ID_RE = re.compile(r"\b91\d{6}[0-9A-Z]{8,12}\b")
ID_CARD_RE = re.compile(r"\b\d{17}[\dXx]\b")
PHONE_RE = re.compile(r"\b1[3-9]\d{9}\b")

SOURCE_FILES = sorted(CAPITAL_DIR.glob("*.py"))

# 允许的占位数字（测试/示例常量，不算真实敏感信息）
ALLOWED_PLACEHOLDERS = {
    "2021000000000000",  # 支付宝示例 app_id
    "1600000000",        # 微信示例商户号
    "1234567890ABCDEF",  # 证书序列号占位
    "0123456789abcdef0123456789abcdef",  # api_v3_key 占位
}


class TestNoHardcodedSecrets(unittest.TestCase):
    """源代码中不得出现银行卡号/税号/身份证/手机号等敏感数据"""

    def _scan(self):
        findings = []
        for f in SOURCE_FILES:
            text = f.read_text(encoding="utf-8")
            for name, rx in (
                ("bank_card", BANK_CARD_RE),
                ("tax_id", TAX_ID_RE),
                ("id_card", ID_CARD_RE),
                ("phone", PHONE_RE),
            ):
                for m in rx.finditer(text):
                    if m.group(0) not in ALLOWED_PLACEHOLDERS:
                        findings.append(f"{f.name}: {name}={m.group(0)}")
        return findings

    def test_no_sensitive_numbers_in_source(self):
        findings = self._scan()
        self.assertEqual([], findings, f"硬编码敏感信息: {findings}")

    def test_no_hardcoded_shareholder_names(self):
        """股东姓名必须来自加密名册，源码不得出现具体自然人姓名

        禁用值在运行时拼接，避免把真实姓名/账号写进测试文件本身。
        """
        combined = "\n".join(f.read_text(encoding="utf-8") for f in SOURCE_FILES)
        for forbidden in self._forbidden_values():
            self.assertNotIn(forbidden, combined, f"源码仍含敏感值: {forbidden[:2]}***")

    @staticmethod
    def _forbidden_values():
        return [
            "廖" + "献云",
            "徐汇" + "长桥支行",
            "6222" + "031001026162672",
        ]

    def test_no_hardcoded_company_tax_id(self):
        combined = "\n".join(f.read_text(encoding="utf-8") for f in SOURCE_FILES)
        self.assertNotIn("91310000MA", combined, "源码仍含硬编码税号")


class TestTaxFilerFailClosed(unittest.TestCase):
    def test_submit_always_false(self):
        with tempfile.TemporaryDirectory() as td:
            cap = CapitalAllocator(state_dir=td)
            filer = TaxFiler(cap, entity_path=Path(td) / "entity.json")
            # 即便人工批准且指定提交人，也不得返回 True
            self.assertFalse(filer.submit_if_approved("2026-09", True, "accountant"))
            self.assertFalse(filer.submit_if_approved("2026-09", False, ""))

    def test_entity_profile_supplies_identity(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "entity.json").write_text(
                json.dumps({"company_name": "测试主体", "tax_id": "TEST0001"}),
                encoding="utf-8")
            cap = CapitalAllocator(state_dir=td)
            filer = TaxFiler(cap, entity_path=td / "entity.json")
            self.assertEqual("测试主体", filer.entity.get("company_name"))
            vat = filer.preview_vat("2026-09")
            self.assertEqual("测试主体", vat.company_name)


class TestDividendFailClosed(unittest.TestCase):
    def _dist(self, td):
        cap = CapitalAllocator(state_dir=td)
        return DividendDistributor(cap, Path(td) / "dividend_config.enc")

    def test_execute_defaults_to_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dist = self._dist(td)
            plan = dist.create_plan(
                "2026-Q3", Decimal("10000"), Decimal("0"),
                [Shareholder(id="s1", name="外部股东A", share_ratio=Decimal("1.0"))])
            # 默认不执行
            self.assertEqual([], dist.execute(plan.plan_id))
            # 批准但无留痕证据，仍拒绝
            dist.approve(plan.plan_id, "张三")
            dist.approve(plan.plan_id, "李四")
            self.assertEqual([], dist.execute(plan.plan_id, approved_by_human=True))

    def test_system_accounts_cannot_approve(self):
        with tempfile.TemporaryDirectory() as td:
            dist = self._dist(td)
            plan = dist.create_plan(
                "2026-Q3", Decimal("10000"), Decimal("0"),
                [Shareholder(id="s1", name="外部股东A", share_ratio=Decimal("1.0"))])
            for fake in ("CEO", "CFO", "admin", "system"):
                self.assertFalse(dist.approve(plan.plan_id, fake),
                                 f"{fake} 不应被接受为审批人")
            self.assertIn("ceo", SYSTEM_APPROVER_BLOCKLIST)

    def test_dual_approval_requires_two_distinct_humans(self):
        with tempfile.TemporaryDirectory() as td:
            dist = self._dist(td)
            plan = dist.create_plan(
                "2026-Q3", Decimal("10000"), Decimal("0"),
                [Shareholder(id="s1", name="外部股东A", share_ratio=Decimal("1.0"))])
            self.assertFalse(dist.approve(plan.plan_id, "张三"))
            self.assertTrue(dist.approve(plan.plan_id, "李四"))

    def test_register_missing_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            dist = self._dist(td)
            self.assertEqual([], dist.load_shareholder_register())

    def test_no_hardcoded_register_in_cycle(self):
        combined = (CAPITAL_DIR / "dividend_distributor.py").read_text(encoding="utf-8")
        self.assertIn("load_shareholder_register", combined)
        self.assertNotIn("bank_account=\"6", combined)


class TestPaymentNotifyFailClosed(unittest.TestCase):
    def _assert_refuses_live_request(self, gw):
        """占位私钥下不得发出真实网络请求"""
        with self.assertRaises(Exception):
            gw._request("POST", "/v3/pay/transactions/native", {})

    def test_wechat_rejects_unconfigured_callback(self):
        with tempfile.TemporaryDirectory() as td:
            crypto = ConfigCrypto()
            gw = WechatGateway({
                "appid": "wx1", "mch_id": "1",
                "api_v3_key_enc": crypto.encrypt("0123456789abcdef0123456789abcdef"),
                "cert_serial": "ABC",
                "private_key_enc": crypto.encrypt("-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"),
                "notify_url": "https://x/n",
            }, crypto)
            body = json.dumps({
                "id": "1", "event_type": "TRANSACTION.SUCCESS",
                "resource": {"algorithm": "AEAD_AES_256_GCM", "ciphertext": "AAAA"},
            }).encode()
            # 无签名头 + 无平台公钥 => 必须拒绝
            self.assertIsNone(gw.verify_notify({}, body))

    def test_wechat_rejects_bad_signature(self):
        with tempfile.TemporaryDirectory() as td:
            crypto = ConfigCrypto()
            gw = WechatGateway({
                "appid": "wx1", "mch_id": "1",
                "api_v3_key_enc": crypto.encrypt("0123456789abcdef0123456789abcdef"),
                "cert_serial": "ABC",
                "private_key_enc": crypto.encrypt("-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"),
                "wechatpay_public_key_enc": crypto.encrypt("-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"),
                "notify_url": "https://x/n",
            }, crypto)
            body = b'{"resource":{"ciphertext":"AAAA"}}'
            bad = {
                "Wechatpay-Timestamp": "1", "Wechatpay-Nonce": "n",
                "Wechatpay-Signature": base64.b64encode(b"garbage").decode(),
            }
            self.assertIsNone(gw.verify_notify(bad, body))

    def test_wechat_rejects_missing_signature_headers(self):
        with tempfile.TemporaryDirectory() as td:
            crypto = ConfigCrypto()
            gw = WechatGateway({
                "appid": "wx1", "mch_id": "1",
                "api_v3_key_enc": crypto.encrypt("0123456789abcdef0123456789abcdef"),
                "cert_serial": "ABC",
                "private_key_enc": crypto.encrypt("-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"),
                "wechatpay_public_key_enc": crypto.encrypt("x"),
                "notify_url": "https://x/n",
            }, crypto)
            self.assertIsNone(gw.verify_notify({}, b"{}"))

    def test_wechat_refuses_live_api_without_real_key(self):
        """占位私钥下不得发出真实网络请求"""
        with tempfile.TemporaryDirectory() as td:
            crypto = ConfigCrypto()
            gw = WechatGateway({
                "appid": "wx1", "mch_id": "1",
                "api_v3_key_enc": crypto.encrypt("0123456789abcdef0123456789abcdef"),
                "cert_serial": "ABC",
                "private_key_enc": crypto.encrypt("-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"),
                "notify_url": "https://x/n",
            }, crypto)
            self._assert_refuses_live_request(gw)

    def test_alipay_notify_parses_urlencoded(self):
        """回调体是已编码的 form，需解回原值；验签失败必须拒绝"""
        with tempfile.TemporaryDirectory() as td:
            crypto = ConfigCrypto()
            gw = AlipayGateway({
                "app_id": "2021", "notify_url": "https://x/n",
                "private_key_enc": crypto.encrypt("-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"),
                "alipay_public_key_enc": crypto.encrypt("-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"),
            }, crypto)
            from urllib.parse import urlencode
            body = urlencode({
                "trade_no": "T1", "out_trade_no": "O1", "total_amount": "100.00",
                "gmt_payment": "2026-09-30 10:00:00", "trade_status": "TRADE_SUCCESS",
                "sign": "badsign",
            }).encode()
            self.assertIsNone(gw.verify_notify({}, body))

    def test_alipay_sign_str_excludes_empty_and_sign(self):
        params = {"b": "2", "a": "1", "empty": "", "sign": "x", "sign_type": "RSA2"}
        s = AlipayGateway._build_sign_str(params)
        self.assertEqual("a=1&b=2", s)


class TestCapitalAllocatorAccounting(unittest.TestCase):
    def test_completed_experiment_still_consumes_budget(self):
        """回归：实验关闭后预算不得被退还，否则可无限超发"""
        with tempfile.TemporaryDirectory() as td:
            cap = CapitalAllocator(state_dir=td)
            bucket = AllocationBucket.EXPERIMENT_BUDGET
            start = cap.available(bucket)
            self.assertTrue(cap.allocate(bucket, "e1", "test", Decimal("1000")))
            mid = cap.available(bucket)
            self.assertEqual(start - Decimal("1000"), mid)
            cap.spend("e1", Decimal("1000"), "api")
            cap.close("e1", "done")
            after = cap.available(bucket)
            self.assertEqual(mid, after, "关闭实验不应退还已支出预算")

    def test_cancelled_experiment_returns_budget(self):
        with tempfile.TemporaryDirectory() as td:
            cap = CapitalAllocator(state_dir=td)
            bucket = AllocationBucket.EXPERIMENT_BUDGET
            start = cap.available(bucket)
            cap.allocate(bucket, "e2", "test", Decimal("500"))
            cap.close("e2", "cancelled")
            cap.ledger[-1].status = "cancelled"
            self.assertEqual(start, cap.available(bucket))


class TestCryptoKeyConsistency(unittest.TestCase):
    def test_manager_roundtrip_with_master_key_file(self):
        """回归：__main__ 曾用不同密码写文件，导致 InvalidToken"""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            cfg = td / "payment_config.enc"
            crypto = ConfigCrypto()
            cfg.write_text(crypto.encrypt_dict({
                "alipay": {
                    "app_id": "2021000000000000",
                    "notify_url": "https://example.invalid/alipay",
                    "private_key_enc": crypto.encrypt("-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"),
                    "alipay_public_key_enc": crypto.encrypt("-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"),
                },
                "wechat": {
                    "appid": "wx1234567890",
                    "mch_id": "1600000000",
                    "cert_serial": "1234567890ABCDEF",
                    "notify_url": "https://example.invalid/wechat",
                    "api_v3_key_enc": crypto.encrypt("0123456789abcdef0123456789abcdef"),
                    "private_key_enc": crypto.encrypt("-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"),
                },
            }), encoding="utf-8")
            mgr = PaymentGatewayManager(cfg)
            self.assertEqual({"alipay", "wechat"}, set(mgr.gateways))

    def test_env_key_takes_precedence(self):
        with tempfile.TemporaryDirectory() as td:
            env = base64.urlsafe_b64encode(b"0" * 32).decode()
            old = os.environ.get("PAYMENT_MASTER_KEY")
            os.environ["PAYMENT_MASTER_KEY"] = env
            try:
                self.assertEqual(env.encode(), ConfigCrypto().key)
            finally:
                if old is None:
                    os.environ.pop("PAYMENT_MASTER_KEY", None)
                else:
                    os.environ["PAYMENT_MASTER_KEY"] = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
