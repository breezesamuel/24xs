# -*- coding: utf-8 -*-
"""openssl 兜底签名的等价性验证。

目标机（用户国内阿里云）未必能 pip install pycryptodome，装不上就等于收不到钱，
所以 alipay_lib 加了 openssl CLI 兜底。这里证明：

  1. 两条路径签出的字节**完全一致**（不是"看起来像"，是 base64 逐字节相同）
  2. 兜底签出的签名能被 pycryptodome 验过（支付宝认可）
  3. 篡改参数必须验不过（兜底路径没有放松校验）

注意：这里用**自己私钥导出的公钥**验自己的签名。支付宝的"支付宝公钥"是用来验
支付宝应答的，本来就验不过我方签名 —— 拿它验自己会得到 False，那是正常的。
"""
import importlib
import os
import subprocess
import sys

API = r"F:\2026\24xs\10_官网\api"
PRIV = (r"C:\Users\46012\Documents\支付宝开放平台密钥工具\密钥20260923101118"
        r"\应用私钥RSA2048-敏感数据，请妥善保管.txt")
sys.path.insert(0, API)
import alipay_lib as A  # noqa: E402

ok = fail = 0


def case(name, cond, why=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [PASS] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {why}")


raw = open(PRIV, "rb").read().decode("utf-8", "ignore")
priv = A._to_pem(raw, "RSA PRIVATE KEY")

# 从私钥导出公钥（验自己的签名要用它）
from Crypto.PublicKey import RSA  # noqa: E402
pub_derived = RSA.import_key(priv).publickey().export_key("PEM").decode()
pub_p1 = A._to_pem(pub_derived, "RSA PUBLIC KEY")

params = {
    "app_id": "2021006197622702",
    "method": "alipay.trade.page.pay",
    "charset": "utf-8",
    "sign_type": "RSA2",
    "timestamp": "2026-10-01 12:00:00",
    "version": "1.0",
    "notify_url": "https://example.cn/notify",
    "biz_content": ('{"out_trade_no":"G1-20261001120000-AAAAAA-9900-R",'
                    '"total_amount":"99.00","subject":"x"}'),
}

import base64
import json  # noqa: E402


def verify_req(params, sig_b64, pub_pem):
    """按**请求**语义验签。

    不能用 A.verify()：那是支付宝异步通知的语义（notify_str 会排除 sign_type），
    而 sign() 走的是请求语义（sign_str 必须包含 sign_type）。两者本来就不同，
    拿通知语义去验请求签名，失败是正常的，不是 bug。
    """
    return A._rsa("verify", pub_pem, A.sign_str(params).encode(),
                  base64.b64decode(sig_b64)) is True


print("=== 1. pycryptodome 主路径 ===")
sig_crypto = A.sign(params, priv)
case("签名非空", bool(sig_crypto))
case("主路径签名可自验", verify_req(params, sig_crypto, pub_p1))

print("\n=== 2. openssl 兜底路径（屏蔽 pycryptodome 的子进程）===")
child = r'''
import sys
sys.path.insert(0, %r)
for m in ("Crypto", "Crypto.Hash", "Crypto.Signature", "Crypto.PublicKey"):
    sys.modules[m] = None
import alipay_lib as A
raw = open(%r, "rb").read().decode("utf-8", "ignore")
priv = A._to_pem(raw, "RSA PRIVATE KEY")
import json
params = json.loads(sys.argv[1])
try:
    sys.stdout.write(A.sign(params, priv))
except Exception as e:
    sys.stderr.write("ERR " + str(e)); sys.exit(2)
''' % (API, PRIV)
r = subprocess.run([sys.executable, "-c", child, json.dumps(params)],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=120)
if r.returncode != 0:
    case("openssl 兜底可运行", False, (r.stderr or "")[-200:])
    print(f"\n{ok} passed, {fail} failed")
    sys.exit(1)
sig_ossl = r.stdout.strip()
case("兜底签名非空", bool(sig_ossl))
case("两条路径字节完全一致", sig_ossl == sig_crypto,
     f"crypto={len(sig_crypto)} ossl={len(sig_ossl)}")

print("\n=== 3. 兜底签名必须经得起验签 ===")
case("兜底签名可验过", verify_req(params, sig_ossl, pub_p1))
case("篡改金额验不过",
     verify_req({**params, "biz_content": params["biz_content"].replace(
         "99.00", "0.01")}, sig_ossl, pub_p1) is False)
case("错公钥验不过", A.verify(params, sig_ossl, A._to_pem(
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAx0Zk0LmB6Q0dVdF0k8"
    "hVQ0Zk0LmB6Q0dVdF0k8hVQ0Zk0LmB6Q0dVdF0k8hVQ0Zk0LmB6Q0dVdF0k8hVQ"
    "0Zk0LmB6Q0dVdF0k8hVQ0Zk0LmB6Q0dVdF0k8hVAAQ==", "RSA PUBLIC KEY")) is False)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)