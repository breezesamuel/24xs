# -*- coding: utf-8 -*-
"""本地起服务，按真实环境变量测试下单与回调判定逻辑。

注意：不设置 ALIPAY_PRIVATE_KEY 时下单必须 503（fail-closed），
绝不能在没凭据的情况下假装成功。
"""
import base64
import json
import re
import sys
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path

API = Path(r"F:\2026\24xs\10_官网\api")
sys.path.insert(0, str(API))
import alipay_lib as A  # noqa: E402

PORT = 8931
ok = fail = 0


def case(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [PASS] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {extra}")


def post(path, payload=None, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}", data=body,
        headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def serve(mod):
    srv = HTTPServer(("127.0.0.1", PORT), mod.handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


print("\n=== 无凭据时必须拒绝 ===")
import os
for k in ("ALIPAY_APP_ID", "ALIPAY_PRIVATE_KEY"):
    os.environ.pop(k, None)
srv = serve(__import__("alipay_pay"))
code, d = post("/api/alipay_pay", {"plan": "month", "email": "a@b.com"})
case("无凭据下单返回 503", code == 503, f"got {code} {d}")
srv.shutdown()

print("\n=== 参数校验 ===")
srv = serve(__import__("alipay_pay"))
case("非法套餐被拒", post("/api/alipay_pay", {"plan": "lifetime",
                          "email": "a@b.com"})[0] == 400)
case("非法邮箱被拒", post("/api/alipay_pay",
                        {"plan": "month", "email": "not-an-email"})[0] == 400)
srv.shutdown()

print("\n=== 单号编解码（金额不可篡改）===")
# 随机段是 base32，字母表为 A-Z2-7，**不会出现 0 和 1**
NO = "G1-20260930120000-NLTRFV-50000-Y"
case("正常单号可还原", A.parse_order_no(NO) == ("year", 50000))
case("季付单号可还原", A.parse_order_no("G1-20260930120000-ABCD23-15000-Q")
     == ("quarter", 15000))
case("月付单号可还原", A.parse_order_no("G1-20260930120000-ZZZZ77-6000-M")
     == ("month", 6000))
case("随机段含 '9'（非 base32）被拒",
     A.parse_order_no("G1-20260930120000-ZZZZ99-6000-M") is None)
case("非法 base32 字符 '1' 被拒",
     A.parse_order_no("G1-20260930120000-A1B2C3-50000-Y") is None)
case("非本系统单号拒绝", A.parse_order_no("EVIL-123") is None)
case("缺段拒绝", A.parse_order_no("G1-20260930120000-1-M") is None)
case("空单号拒绝", A.parse_order_no("") is None)
case("含下划线/斜杠的注入被拒",
     A.parse_order_no("G1-20260930120000-AB_-50000-Y") is None)

print("\n=== 回调判定：只信支付宝查询结果 ===")
import alipay_notify as N

REAL = {"code": "10000", "trade_status": "TRADE_SUCCESS",
        "total_amount": "500.00", "trade_no": "2026xxx"}


def fake(truth):
    N.A.query_trade = lambda no: truth
    return N.check(NO)


N.A.query_trade = lambda no: REAL
good, why = N.check(NO)
case("支付宝确认 500.00 -> 判定通过", good, why)
case("通过时带出套餐与金额", "year" in why and "500.00" in why, why)

N.A.query_trade = lambda no: {**REAL, "total_amount": "0.01"}
good, why = N.check(NO)
case("支付宝只收到 0.01 -> 拒绝", not good, why)

N.A.query_trade = lambda no: {**REAL, "trade_status": "WAIT_BUYER_PAY"}
good, why = N.check(NO)
case("未支付完成 -> 拒绝", not good, why)

N.A.query_trade = lambda no: None
good, why = N.check(NO)
case("查不到订单 -> 拒绝（不发货）", not good, why)

N.A.query_trade = lambda no: {"code": "40004", "sub_code": "ACQ.TRADE_NOT_EXIST"}
good, why = N.check(NO)
case("订单不存在 -> 拒绝", not good, why)

N.A.query_trade = lambda no: {k: v for k, v in REAL.items()
                              if k != "total_amount"}
good, why = N.check(NO)
case("应答缺金额 -> 拒绝", not good, why)

good, why = N.check("EVIL-ORDER")
case("非本系统单号直接拒绝", not good, why)

print("\n=== 真实凭据：生成支付链接 ===")
good = Path(r"C:\Users\46012\Documents\支付宝开放平台密钥工具"
            r"\密钥20260923101118\应用私钥RSA2048-敏感数据，请妥善保管.txt")
blob = "".join(re.search(r"MII[A-Za-z0-9+/]{600,}={0,2}",
                         good.read_text(encoding="utf-8",
                                        errors="replace")).group().split())
os.environ["ALIPAY_APP_ID"] = "2021006197622702"
os.environ["ALIPAY_PRIVATE_KEY"] = blob
srv = serve(__import__("alipay_pay"))
code, d = post("/api/alipay_pay", {"plan": "year", "email": "test@x.com"})
if code == 200:
    case("下单返回支付链接", d["pay_url"].startswith("https://openapi.alipay.com"))
    case("订单号含金额 50000", "50000" in d["order_id"])
    case("金额显示 500.00", d["amount"] == "500.00")
    case("响应不含私钥", "MII" not in json.dumps(d))
    import urllib.parse as up
    q = dict(up.parse_qsl(up.urlparse(d["pay_url"]).query))
    case("链接含 sign 与 sign_type", "sign" in q and q.get("sign_type") == "RSA2")
    # 验证签名可被支付宝公钥对应的私钥验过
    from Crypto.Hash import SHA256
    from Crypto.Signature import pkcs1_15
    from Crypto.PublicKey import RSA
    p = {k: v for k, v in q.items() if k != "sign"}
    raw = base64.b64decode(blob + "=" * (-len(blob) % 4))
    try:
        pkcs1_15.new(RSA.import_key(raw)).verify(
            SHA256.new(A.sign_str(p).encode()), base64.b64decode(q["sign"]))
        case("签名可被应用私钥对应公钥验证", True)
    except Exception as e:
        case("签名可被应用私钥对应公钥验证", False, str(e))
else:
    case("下单返回支付链接", False, f"code={code} {d}")
srv.shutdown()

print("\n=== 签名规则回归（用支付宝真实应答夹具，不自证）===")
# 之前那条"签名可被应用私钥对应公钥验证"是用 A.sign_str 自己验自己签的，
# 属于自证循环：sign_str 规则写错也照样通过，于是 invalid-signature
# 那种"根本收不了款"的致命错误一路绿灯放行。这里换成外部事实。
p0 = {"app_id": "2021006197622702", "method": "alipay.trade.page.pay",
      "charset": "utf-8", "sign_type": "RSA2", "timestamp": "2026-10-01 12:00:00",
      "version": "1.0", "format": "JSON", "biz_content": {"a": "b"}}
s_req = A.sign_str(p0)
case("请求签名原文含 sign_type", "sign_type=RSA2" in s_req,
     "支付宝签名错误时会回显待签名串，实测其中含 sign_type")
case("请求签名原文不含裸 sign 字段", "&sign=" not in s_req)
s_notify = A.notify_str({**p0, "sign": "xx"})
case("通知验签原文不含 sign_type", "sign_type" not in s_notify,
     "官方文档要求通知验签剔除 sign 与 sign_type")
case("通知验签原文剔除 sign", "sign=xx" not in s_notify)

fixp = Path(__file__).with_name("_alipay_resp_fixture.json")
if fixp.exists():
    raw_fix = fixp.read_text(encoding="utf-8")
    resp = json.loads(raw_fix)
    alipay_pub = Path(r"C:\Users\46012\Downloads\alipayPublicKey_RSA2 (1).txt")
    if alipay_pub.exists():
        pubb = re.search(r"MII[A-Za-z0-9+/]{100,}={0,2}",
                         alipay_pub.read_text(encoding="utf-8",
                                              errors="replace")).group()
        case("真实应答可用支付宝公钥验签",
             A.verify_response(resp, resp["sign"], A._to_pem(pubb, "public")))
        from Crypto.PublicKey import RSA as _RSA
        wrong = _RSA.generate(2048).public_key().export_key().decode()
        case("真实应答用错公钥必须验签失败",
             A.verify_response(resp, resp["sign"], wrong) is False)
        tampered = json.loads(raw_fix)
        tampered["alipay_trade_query_response"]["total_amount"] = "0.01"
        case("应答被篡改金额后必须验签失败",
             A.verify_response(tampered, tampered["sign"],
                               A._to_pem(pubb, "public")) is False)
    else:
        print("  (跳过真实应答验签：未找到支付宝公钥文件)")
else:
    print("  (跳过真实应答验签：缺少夹具)")

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)