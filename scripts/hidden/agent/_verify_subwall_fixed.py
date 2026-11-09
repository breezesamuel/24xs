#!/usr/bin/env python3
"""验证订阅墙堵白嫖后, 真实付款→开通正路径 (activate/entitle) 仍正确工作"""
import urllib.request, urllib.error, json, time

TARGETS = {
    "Vercel 主站": "https://tools.highkingflower.com",
    "阿里云 tools-cn": "https://tools-cn.highkingflower.com",
}

def post(base, path, payload):
    try:
        req = urllib.request.Request(base+path, data=json.dumps(payload).encode(),
            method="POST", headers={"User-Agent":"audit","Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b"").decode("utf-8","replace")
    except Exception as e:
        return 0, str(e)

ts = int(time.time())
print("="*64)
print("  订阅墙: 白嫖已堵 + 正路径(付费开通/只读/退订)验证")
print("="*64)

for name, base in TARGETS.items():
    print(f"\n### {name}")
    ref = f"legit_{ts}"

    # 1. 白嫖已被堵
    st, b = post(base, "/api/subwall", {"action":"subscribe","ref":ref,"plan":"pro"})
    j = json.loads(b) if b.strip().startswith("{") else {}
    print(f"  [白嫖堵死] subscribe: ok={j.get('ok')} error={j.get('error','(无)')}  → {'✅ 拒绝' if j.get('ok') is False else '❌ 仍可开通!'}")

    # 2. extend 也被堵
    st, b = post(base, "/api/subwall", {"action":"extend","ref":ref,"months":3})
    j = json.loads(b) if b.strip().startswith("{") else {}
    print(f"  [续费堵死] extend: ok={j.get('ok')} error={j.get('error','(无)')}  → {'✅ 拒绝' if j.get('ok') is False else '❌'}")

    # 3. 只读 check/list/entitle 仍正常 (未付款=free)
    st, b = post(base, "/api/subwall", {"action":"check","ref":ref})
    j = json.loads(b) if b.strip().startswith("{") else {}
    print(f"  [只读正常] check: subscribed={j.get('subscribed')} plan={j.get('plan')}  → {'✅ 未付=free' if j.get('plan')=='free' else '❌'}")

    # 4. plans 公开列表仍正常 (前端要展示价格)
    st, b = post(base, "/api/subwall", {"action":"plans"})
    j = json.loads(b) if b.strip().startswith("{") else {}
    plans = j.get("plans", [])
    print(f"  [计划列表] plans: {len(plans)} 个 (pro/trial/pro3/proY/team)  → {'✅' if len(plans)>=4 else '❌'}")

    # 5. 退订正常 (无订阅也允许调用, 幂等)
    st, b = post(base, "/api/subwall", {"action":"unsubscribe","ref":ref})
    j = json.loads(b) if b.strip().startswith("{") else {}
    print(f"  [退订幂等] unsubscribe: ok={j.get('ok')}  → {'✅' if j.get('ok') else '⚠️'}")

print("\n" + "="*64)
print("  正路径说明: 真实付款开通走 /api/order 查单确认 paid → alipay.js 调 subwall.activate()")
print("  (服务端权威, 不经过公共 subscribe 端点) → /api/entitle 读到权益")
print("="*64)
