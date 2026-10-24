import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
REG = BASE.parent / "11_数据资产" / "registry_real_verified"
ALERT_LOG = BASE / "alerts.log"

def check_health():
    try:
        req = urllib.request.Request("https://geo-audit-24xs.vercel.app/api/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "healthy"
    except:
        return False

def check_api():
    endpoints = [
        "/api/assets?limit=1",
        "/api/search?q=test&limit=1",
        "/api/pricing?action=compare",
    ]
    results = []
    for ep in endpoints:
        try:
            url = "https://geo-audit-24xs.vercel.app" + ep
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                results.append(resp.status < 500)
        except:
            results.append(False)
    return all(results)

def check_data():
    assets_path = REG / "assets_verifiable_1M.jsonl"
    if not assets_path.exists():
        return False
    size = assets_path.stat().st_size
    return size > 100 * 1024 * 1024

def log_alert(message):
    timestamp = datetime.now().isoformat()
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[ALERT] {message}")

def main():
    print("=" * 60)
    print("丙大山数字资产平台 - 监控告警")
    print("=" * 60)

    alerts = []

    if not check_health():
        msg = "健康检查失败"
        alerts.append(msg)
        log_alert(msg)
    else:
        print("[OK] 健康检查通过")

    if not check_api():
        msg = "API 端点异常"
        alerts.append(msg)
        log_alert(msg)
    else:
        print("[OK] API 端点正常")

    if not check_data():
        msg = "数据文件异常"
        alerts.append(msg)
        log_alert(msg)
    else:
        print("[OK] 数据文件正常")

    print("=" * 60)
    if alerts:
        print(f"发现 {len(alerts)} 个告警:")
        for a in alerts:
            print(f"  - {a}")
    else:
        print("无告警")
    print("=" * 60)

    return len(alerts) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)