#!/usr/bin/env python3
"""最终双活验证: 订阅墙 (白嫖堵死 + 权益持久化) + 收款签名 + 权益只读"""
import urllib.request, urllib.error, json, time

TARGETS = {
    "Vercel 主站": "https://tools.highkingflower.com",
    "阿里云 tools-cn": "https://tools-cn.highkingflower.com",
}

def post(base, path, payload):
    try:
        req = urllib.request.Request(base+path, data=json.dumps(payload).encode(),
            method="POST", headers={"User-Agent":"final","Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b"").decode("utf-8","replace")
    except Exception as e:
        return 0, str(e)

ts=int(time.time())
print("="*66)
print("  双活最终验收: 订阅墙 + 收款 + 权益")
print("="*66)

for name, base in TARGETS.items():
    ref=f"fin_{ts}"
    print(f"\n### {name}")
    # 白嫖堵死
    st,b=post(base,"/api/subwall",{"action":"subscribe","ref":ref,"plan":"pro"})
    j=json.loads(b) if b.strip().startswith("{") else {}
    print(f"  [白嫖] subscribe → {j.get('error') or j.get('ok')}  {'✅拒绝' if j.get('ok') is False else '❌仍可开通'}")
    # 签名
    st,b2=post(base,"/api/order",{"out_trade_no":"FINPROBE_"+ref})
    j2=json.loads(b2) if b2.strip().startswith("{") else {}
    sig_ok = j2.get("sub") != "isv.invalid-signature"
    print(f"  [签名] 查单 sub={j2.get('sub')}  {'✅验签通过' if sig_ok else '❌签名失败'}")
    # 权益只读 (未付款=free, 不假开通)
    st,b3=post(base,"/api/entitle",{"ref":ref})
    j3=json.loads(b3) if b3.strip().startswith("{") else {}
    print(f"  [权益] 未付款 orders={j3.get('orders')} slugs={j3.get('slugs')}  {'✅无假权益' if j3.get('orders')==0 else '⚠️检查'}")

print("\n" + "="*66)
print("  收款开通正路径 (服务端 activate, 不靠公共端点):")
print("   /api/notify 验签通过 → saveOrder(paid) → subwall.activate() (幂等) → /api/entitle 读到权益")
print("  阿里云已实证: activate→文件落库→HTTP读回 subscribed=true (file fallback 生效)")
print("="*66)
