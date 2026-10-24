# -*- coding: utf-8 -*-
"""支付宝异步通知的对抗性测试。

核心用例：构造一条**签名完全正确**的回调（用"支付宝私钥"签，模拟真实通道），
只把金额改成 ¥0.01，验证网关不会发货。
——验签只能证明消息来自支付宝，证明不了"钱付够了"。
"""
import base64
import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payment_gateway import AlipayGateway, ConfigCrypto  # noqa: E402

APP_ID = "2021006197622702"
SELLER = "2088-PLACEHOLDER-PID"


def _load_app_private_key() -> str:
    """读本机真实应用私钥（只进内存，不打印、不落盘）。

    读不到就跳过整个测试类 —— 不允许因为找不到文件而假绿。
    """
    good = Path(r"C:\Users\46012\Documents\支付宝开放平台密钥工具"
               r"\密钥20260923101118\应用私钥RSA2048-敏感数据，请妥善保管.txt")
    if not good.exists():
        raise unittest.SkipTest(f"未找到应用私钥: {good}")
    blob = "".join(re.search(r"MII[A-Za-z0-9+/]{600,}={0,2}",
                             good.read_text(encoding="utf-8",
                                            errors="replace")).group().split())
    raw = base64.b64decode(blob + "=" * (-len(blob) % 4))
    return RSA.import_key(raw).export_key().decode()


class TestAlipayNotifyVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        crypto = ConfigCrypto()
        # 扮演支付宝：它的私钥给回调签名，它的公钥配置给网关
        cls.alipay = RSA.generate(2048)
        cls.gw = AlipayGateway({
            "app_id": APP_ID, "seller_id": SELLER,
            "notify_url": "https://example.com/api/notify",
            "private_key_enc": crypto.encrypt(_load_app_private_key()),
            "alipay_public_key_enc": crypto.encrypt(
                cls.alipay.publickey().export_key().decode()),
        }, crypto)

    def body(self, **over):
        d = {
            "app_id": APP_ID, "seller_id": SELLER,
            "trade_no": "2026093022001", "out_trade_no": "GEO-AAA111",
            "total_amount": "500.00", "gmt_payment": "2026-09-30 10:00:00",
            "trade_status": "TRADE_SUCCESS", "notify_id": "n-1",
            "buyer_id": "2088buyer",
        }
        d.update(over)
        d = {k: v for k, v in d.items() if v != ""}
        s = "&".join(f"{k}={v}" for k, v in sorted(d.items()))
        d["sign"] = base64.b64encode(
            pkcs1_15.new(self.alipay).sign(SHA256.new(s.encode()))).decode()
        return urlencode(d).encode()

    def verify(self, body, amount="500.00", order="GEO-AAA111"):
        return self.gw.verify_notify({}, body, expected_amount=amount,
                                     expected_order=order)

    def test_valid_notify_accepted(self):
        n = self.verify(self.body())
        self.assertIsNotNone(n)
        self.assertEqual(n.amount_cny, Decimal("500.00"))
        self.assertEqual(n.order_id, "GEO-AAA111")

    def test_cent_payment_cannot_buy_yearly_plan(self):
        """签名正确但只付 ¥0.01 —— 必须拒绝"""
        self.assertIsNone(self.verify(self.body(total_amount="0.01")))

    def test_amount_mismatch_rejected(self):
        """付 ¥500 想冒充 ¥150 季付"""
        self.assertIsNone(self.verify(self.body(), amount="150.00"))

    def test_app_id_mismatch_rejected(self):
        self.assertIsNone(self.verify(self.body(app_id="2021000000000000")))

    def test_seller_id_mismatch_rejected(self):
        """钱进了别人账户"""
        self.assertIsNone(self.verify(self.body(seller_id="2088-OTHER")))

    def test_out_trade_no_mismatch_rejected(self):
        """串单：用 A 单的付款通知去发 B 单"""
        self.assertIsNone(self.verify(self.body(), order="GEO-BBB222"))

    def test_non_success_status_rejected(self):
        self.assertIsNone(self.verify(self.body(trade_status="WAIT_BUYER_PAY")))

    def test_tampered_signature_rejected(self):
        b = self.body().decode()
        head, _, tail = b.partition("&sign=")
        self.assertIsNone(self.verify(
            (head + "&sign=AAAA" + tail[4:]).encode()))

    def test_missing_amount_rejected(self):
        self.assertIsNone(self.verify(self.body(total_amount="")))


if __name__ == "__main__":
    unittest.main(verbosity=2)