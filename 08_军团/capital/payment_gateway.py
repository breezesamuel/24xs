# -*- coding: utf-8 -*-
"""
Payment Gateway: 统一收款入口
支持：支付宝当面付/网页支付、微信支付 Native/JSAPI、银企直连(EBICS)
设计：幂等、可审计、可重试、配置加密
"""
import json
import time
import uuid
import hashlib
import hmac
import base64
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote_plus, parse_qs
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# =========================
# 数据结构
# =========================
@dataclass
class PaymentOrder:
    order_id: str
    amount_cny: Decimal
    subject: str
    body: str
    notify_url: str
    return_url: str
    buyer_id: Optional[str] = None
    extra: Dict[str, Any] = None

@dataclass
class PaymentResult:
    success: bool
    gateway: str
    order_id: str
    trade_no: Optional[str] = None
    pay_url: Optional[str] = None
    qr_code: Optional[str] = None
    raw_response: Dict = None
    error: Optional[str] = None

@dataclass
class NotifyData:
    gateway: str
    trade_no: str
    order_id: str
    amount_cny: Decimal
    paid_at: datetime
    buyer_id: Optional[str] = None
    raw: Dict = None

# =========================
# 配置加密管理
# =========================
class ConfigCrypto:
    """配置加密：使用 Fernet (AES-128-CBC+HMAC) / PBKDF2

    密钥来源优先级：显式参数 > 环境变量 PAYMENT_MASTER_KEY > 同目录 .master.key
    """
    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.key = self._derive_key(master_key)
        else:
            env_key = os.environ.get("PAYMENT_MASTER_KEY")
            if env_key:
                self.key = env_key.encode()
            else:
                key_file = Path(__file__).resolve().parent / ".master.key"
                if key_file.exists():
                    self.key = key_file.read_bytes().strip()
                else:
                    self.key = Fernet.generate_key()
                    key_file.write_bytes(self.key)
                    self._restrict(key_file)
        self.fernet = Fernet(self.key)

    @staticmethod
    def _restrict(key_file: Path):
        try:
            import stat
            key_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    def _derive_key(self, password: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"capital_salt_2026",
            iterations=100_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self.fernet.decrypt(token.encode()).decode()

    def encrypt_dict(self, data: Dict) -> str:
        return self.encrypt(json.dumps(data, ensure_ascii=False))

    def decrypt_dict(self, token: str) -> Dict:
        return json.loads(self.decrypt(token))


# =========================
# 网关基类
# =========================
class BaseGateway(ABC):
    def __init__(self, config: Dict, crypto: ConfigCrypto):
        self.config = config
        self.crypto = crypto
        self.name = self.__class__.__name__.replace("Gateway", "").lower()

    @abstractmethod
    def create_order(self, order: PaymentOrder) -> PaymentResult:
        pass

    @abstractmethod
    def verify_notify(self, headers: Dict, body: bytes) -> Optional[NotifyData]:
        pass

    def _log_request(self, action: str, order_id: str, req: Dict, resp: Dict):
        audit = {
            "ts": datetime.now().isoformat(),
            "gateway": self.name,
            "action": action,
            "order_id": order_id,
            "request": {k: v for k, v in req.items() if "key" not in k.lower() and "secret" not in k.lower()},
            "response": {k: v for k, v in resp.items() if "key" not in k.lower() and "secret" not in k.lower()},
        }
        logger.info("PAYMENT_AUDIT: %s", json.dumps(audit, ensure_ascii=False))


# =========================
# 支付宝网关
# =========================
class AlipayGateway(BaseGateway):
    def __init__(self, config: Dict, crypto: ConfigCrypto):
        super().__init__(config, crypto)
        self.app_id = config["app_id"]
        self.private_key = crypto.decrypt(config["private_key_enc"])
        self.alipay_public_key = crypto.decrypt(config["alipay_public_key_enc"])
        self.notify_url = config["notify_url"]
        self.gateway_url = config.get("gateway_url", "https://openapi.alipay.com/gateway.do")
        self.sign_type = "RSA2"
        # seller_id = 支付宝分配给你商户的 PID。回调里必须核对它，
        # 否则钱进了别的账户也会被当成已付款发货。
        self.seller_id = config.get("seller_id", "")

    @staticmethod
    def _build_sign_str(params: Dict) -> str:
        """支付宝 RSA2 签名原文：过滤空值与 sign/sign_type，按 key 升序，key=value& 拼接"""
        keys = sorted(k for k in params if k not in ("sign", "sign_type") and params[k] not in (None, ""))
        return "&".join(f"{k}={params[k]}" for k in keys)

    def _sign(self, params: Dict) -> str:
        sign_str = self._build_sign_str(params)
        from Crypto.Signature import pkcs1_15
        from Crypto.Hash import SHA256
        from Crypto.PublicKey import RSA
        key = RSA.import_key(self.private_key)
        signature = pkcs1_15.new(key).sign(SHA256.new(sign_str.encode()))
        return base64.b64encode(signature).decode()

    def _verify_sign(self, params: Dict, sign: str) -> bool:
        if not sign:
            return False
        sign_str = self._build_sign_str(params)
        from Crypto.Signature import pkcs1_15
        from Crypto.Hash import SHA256
        from Crypto.PublicKey import RSA
        try:
            key = RSA.import_key(self.alipay_public_key)
            pkcs1_15.new(key).verify(SHA256.new(sign_str.encode()), base64.b64decode(sign))
            return True
        except Exception as e:
            logger.warning("Alipay sign verify error: %s", e)
            return False

    def create_order(self, order: PaymentOrder) -> PaymentResult:
        biz_content = {
            "out_trade_no": order.order_id,
            "total_amount": str(order.amount_cny),
            "subject": order.subject,
            "body": order.body,
            "notify_url": order.notify_url or self.notify_url,
            "return_url": order.return_url,
        }
        params = {
            "app_id": self.app_id,
            "method": "alipay.trade.page.pay",
            "format": "JSON",
            "charset": "UTF-8",
            "sign_type": self.sign_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps(biz_content, separators=(",", ":"), ensure_ascii=False),
        }
        params["sign"] = self._sign(params)
        pay_url = f"{self.gateway_url}?{urlencode(params, quote_via=quote_plus)}"

        self._log_request("create_order", order.order_id, params, {"pay_url": pay_url})
        return PaymentResult(
            success=True,
            gateway="alipay",
            order_id=order.order_id,
            pay_url=pay_url,
            raw_response={"pay_url": pay_url},
        )

    def verify_notify(self, headers: Dict, body: bytes,
                      expected_amount=None, expected_order: Optional[str] = None) -> Optional[NotifyData]:
        """校验支付宝异步通知。任何一项不符都返回 None（fail-closed）。

        注意：验签只能证明消息来自支付宝。必须额外核对 app_id、seller_id、
        金额和订单号，否则可能被用假通知白嫖额度。金额与订单号应该传入
        **我方订单库中的期望值**，而不是直接信任回调里的值。
        """
        try:
            raw_pairs = parse_qs(body.decode("utf-8"), keep_blank_values=True)
            data = {k: v[0] for k, v in raw_pairs.items()}
        except Exception as e:
            logger.warning("Alipay notify body parse failed: %s", e)
            return None

        sign = data.pop("sign", "")
        data.pop("sign_type", None)
        if not self._verify_sign(data, sign):
            logger.warning("Alipay notify sign verify failed")
            return None
        if data.get("trade_status") not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            return None

        if data.get("app_id") != self.app_id:
            logger.warning("Alipay notify app_id mismatch")
            return None
        if self.seller_id and data.get("seller_id") != self.seller_id:
            logger.warning("Alipay notify seller_id mismatch")
            return None

        try:
            got = Decimal(data["total_amount"]).quantize(Decimal("0.01"))
        except (KeyError, ValueError, ArithmeticError):
            logger.warning("Alipay notify total_amount missing/invalid")
            return None
        if expected_amount is not None:
            want = Decimal(str(expected_amount)).quantize(Decimal("0.01"))
            if got != want:
                logger.warning("Alipay notify amount mismatch")
                return None
        if expected_order and data.get("out_trade_no") != expected_order:
            logger.warning("Alipay notify out_trade_no mismatch")
            return None

        try:
            return NotifyData(
                gateway="alipay",
                trade_no=data["trade_no"],
                order_id=data["out_trade_no"],
                amount_cny=got,
                paid_at=datetime.strptime(data["gmt_payment"], "%Y-%m-%d %H:%M:%S"),
                buyer_id=data.get("buyer_id"),
                raw=data,
            )
        except (KeyError, ValueError) as e:
            logger.warning("Alipay notify field error: %s", e)
            return None


# =========================
# 微信支付网关
# =========================
class WechatGateway(BaseGateway):
    def __init__(self, config: Dict, crypto: ConfigCrypto):
        super().__init__(config, crypto)
        self.mch_id = config["mch_id"]
        self.api_v3_key = crypto.decrypt(config["api_v3_key_enc"])
        self.cert_serial = config["cert_serial"]
        self.private_key = crypto.decrypt(config["private_key_enc"])
        self.wechatpay_public_key = config.get("wechatpay_public_key_enc", "")
        if self.wechatpay_public_key:
            self.wechatpay_public_key = crypto.decrypt(self.wechatpay_public_key)
        self.notify_url = config["notify_url"]
        self.base_url = config.get("base_url", "https://api.mch.weixin.qq.com")

    def _sign(self, method: str, url: str, timestamp: str, nonce: str, body: str) -> str:
        sign_str = f"{method}\n{url}\n{timestamp}\n{nonce}\n{body}\n"
        from Crypto.Signature import pkcs1_15
        from Crypto.Hash import SHA256
        from Crypto.PublicKey import RSA
        key = RSA.import_key(self.private_key)
        signature = pkcs1_15.new(key).sign(SHA256.new(sign_str.encode()))
        return base64.b64encode(signature).decode()

    def _verify_sign(self, headers: Dict, body_str: str) -> bool:
        """微信支付 APIv3 应答/回调验签：Wechatpay-Timestamp\nWechatpay-Nonce\nbody\n"""
        timestamp = headers.get("Wechatpay-Timestamp", "")
        nonce = headers.get("Wechatpay-Nonce", "")
        signature = headers.get("Wechatpay-Signature", "")
        if not (timestamp and nonce and signature):
            logger.warning("Wechat notify missing signature headers")
            return False
        sign_str = f"{timestamp}\n{nonce}\n{body_str}\n"
        from Crypto.Signature import pkcs1_15
        from Crypto.Hash import SHA256
        from Crypto.PublicKey import RSA
        try:
            key = RSA.import_key(self.wechatpay_public_key)
            pkcs1_15.new(key).verify(SHA256.new(sign_str.encode()), base64.b64decode(signature))
            return True
        except Exception as e:
            logger.warning("Wechat notify sign verify error: %s", e)
            return False

    def _decrypt_resource(self, resource: Dict) -> Dict:
        """APIv3 资源解密：AES-256-GCM，associated_data + nonce + ciphertext"""
        if resource.get("algorithm") != "AEAD_AES_256_GCM":
            raise ValueError(f"unsupported algorithm: {resource.get('algorithm')}")
        key = self.api_v3_key.encode()
        if len(key) != 32:
            raise ValueError("api_v3_key must be 32 bytes")
        ciphertext = base64.b64decode(resource["ciphertext"])
        nonce = resource["nonce"].encode()
        aad = resource.get("associated_data", "").encode()
        aesgcm = AESGCM(key)
        plain = aesgcm.decrypt(nonce, ciphertext, aad)
        return json.loads(plain.decode("utf-8"))

    def _request(self, method: str, path: str, body: Dict = None) -> Dict:
        import requests
        url = f"{self.base_url}{path}"
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False) if body else ""
        # 签名串中的 URL 必须是完整 URL（含 scheme 与 host）
        signature = self._sign(method, url, timestamp, nonce, body_str)
        auth = f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mch_id}",nonce_str="{nonce}",timestamp="{timestamp}",serial_no="{self.cert_serial}",signature="{signature}"'
        headers = {
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Idempotency-Key": str(uuid.uuid4()),
            "User-Agent": "capital-automation/1.0",
        }
        if not self.private_key or "..." in self.private_key:
            raise RuntimeError("Wechat private_key not configured; refusing live API call")
        resp = requests.request(method, url, headers=headers, data=body_str.encode("utf-8"), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def create_order(self, order: PaymentOrder) -> PaymentResult:
        body = {
            "appid": self.config["appid"],
            "mchid": self.mch_id,
            "description": order.subject,
            "out_trade_no": order.order_id,
            "notify_url": order.notify_url or self.notify_url,
            "amount": {"total": int(order.amount_cny * 100), "currency": "CNY"},
        }
        if order.body:
            body["detail"] = order.body
        resp = self._request("POST", "/v3/pay/transactions/native", body)
        self._log_request("create_order", order.order_id, body, resp)
        return PaymentResult(
            success=True,
            gateway="wechat",
            order_id=order.order_id,
            trade_no=resp.get("prepay_id"),
            qr_code=resp.get("code_url"),
            raw_response=resp,
        )

    def verify_notify(self, headers: Dict, body: bytes) -> Optional[NotifyData]:
        """微信支付回调：必须验签 + 解密，缺一不可；任何异常一律拒绝（fail-closed）"""
        body_str = body.decode("utf-8")
        if not self.wechatpay_public_key:
            logger.error("Wechat notify rejected: wechatpay_public_key not configured")
            return None
        if not self._verify_sign(headers, body_str):
            logger.warning("Wechat notify sign verify failed")
            return None
        try:
            data = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.warning("Wechat notify JSON parse failed: %s", e)
            return None

        try:
            decrypted = self._decrypt_resource(data["resource"])
        except Exception as e:
            logger.warning("Wechat notify resource decrypt failed: %s", e)
            return None

        if decrypted.get("trade_state") != "SUCCESS":
            return None
        try:
            return NotifyData(
                gateway="wechat",
                trade_no=decrypted["transaction_id"],
                order_id=decrypted["out_trade_no"],
                amount_cny=Decimal(str(decrypted["amount"]["total"])) / 100,
                paid_at=datetime.strptime(decrypted["success_time"], "%Y-%m-%dT%H:%M:%S%z"),
                buyer_id=decrypted.get("payer", {}).get("openid"),
                raw={"envelope": data, "resource": decrypted},
            )
        except (KeyError, ValueError) as e:
            logger.warning("Wechat notify field error: %s", e)
            return None


# =========================
# 银企直连网关
# =========================
class BankEBICSGateway(BaseGateway):
    def __init__(self, config: Dict, crypto: ConfigCrypto):
        super().__init__(config, crypto)
        self.host = config["host"]
        self.user = config["user"]
        self.passphrase = crypto.decrypt(config["pass_enc"])
        self.cert_path = config["cert_path"]
        self.cert_pass = crypto.decrypt(config["cert_pass_enc"])

    def create_order(self, order: PaymentOrder) -> PaymentResult:
        # EBICS 协议较复杂，通常用成熟库 (如 python-ebics)
        # 这里仅定义接口，实际需对接具体银行
        logger.warning("BankEBICSGateway.create_order not fully implemented")
        return PaymentResult(
            success=False,
            gateway="bank_ebics",
            order_id=order.order_id,
            error="EBICS gateway not fully implemented",
        )

    def verify_notify(self, headers: Dict, body: bytes) -> Optional[NotifyData]:
        # 银行回调通常是文件落地或 HTTP 回调，按银行文档解析
        return None


# =========================
# 统一网关管理器
# =========================
class PaymentGatewayManager:
    def __init__(self, config_path: Path, master_key: Optional[str] = None):
        self.config_path = config_path
        self.crypto = ConfigCrypto(master_key)
        self.gateways: Dict[str, BaseGateway] = {}
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Payment config not found: {self.config_path}")
        enc_config = self.config_path.read_text(encoding="utf-8")
        config = self.crypto.decrypt_dict(enc_config)

        if "alipay" in config:
            self.gateways["alipay"] = AlipayGateway(config["alipay"], self.crypto)
        if "wechat" in config:
            self.gateways["wechat"] = WechatGateway(config["wechat"], self.crypto)
        if "bank_ebics" in config:
            self.gateways["bank_ebics"] = BankEBICSGateway(config["bank_ebics"], self.crypto)

    def create_order(self, order: PaymentOrder, preferred: str = "alipay") -> PaymentResult:
        gateway = self.gateways.get(preferred)
        if not gateway:
            # 降级尝试
            for g in self.gateways.values():
                try:
                    return g.create_order(order)
                except Exception as e:
                    logger.warning("Gateway %s failed: %s", g.name, e)
            return PaymentResult(success=False, gateway="none", order_id=order.order_id, error="No available gateway")
        return gateway.create_order(order)

    def verify_notify(self, gateway_name: str, headers: Dict, body: bytes) -> Optional[NotifyData]:
        gateway = self.gateways.get(gateway_name)
        if not gateway:
            return None
        return gateway.verify_notify(headers, body)


# =========================
# 使用示例
# =========================
if __name__ == "__main__":
    # 生成示例配置（占位凭据，仅用于打通链路，不能用于真实收款）
    # 密钥来源与 PaymentGatewayManager 完全一致，避免再次出现 InvalidToken
    crypto = ConfigCrypto()
    config = {
        "alipay": {
            "app_id": "2021000000000000",
            "private_key_enc": crypto.encrypt("-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"),
            "alipay_public_key_enc": crypto.encrypt("-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"),
            "notify_url": "https://your.domain/alipay/notify",
        },
        "wechat": {
            "appid": "wx1234567890",
            "mch_id": "1600000000",
            "api_v3_key_enc": crypto.encrypt("0123456789abcdef0123456789abcdef"),
            "cert_serial": "1234567890ABCDEF",
            "private_key_enc": crypto.encrypt("-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"),
            "wechatpay_public_key_enc": crypto.encrypt("-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"),
            "notify_url": "https://your.domain/wechat/notify",
        },
    }
    # 必须写绝对路径，否则相对路径会写到进程 CWD 而不是模块目录
    out_path = Path(__file__).resolve().parent / "payment_config.enc"
    out_path.write_text(crypto.encrypt_dict(config), encoding="utf-8")
    print(f"Generated {out_path}")
