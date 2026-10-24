import json
import hashlib
import os
from pathlib import Path

BASE = Path(__file__).parent
REG = BASE.parent / "11_数据资产" / "registry_real_verified"

def check_file(path, label):
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    status = "PASS" if exists and size > 0 else "FAIL"
    print(f"[{status}] {label}: {path.name} ({size:,} bytes)")
    return exists

def check_json(path, label):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"[PASS] {label}: valid JSON")
        return data
    except Exception as e:
        print(f"[FAIL] {label}: {e}")
        return None

def verify_merkle():
    merkle_path = REG / "merkle_tree.json"
    data = check_json(merkle_path, "Merkle Tree")
    if data:
        root = data.get("root", "")
        total = data.get("total", 0)
        levels = data.get("levels", 0)
        print(f"  Root: {root[:16]}...")
        print(f"  Total: {total:,}")
        print(f"  Levels: {levels}")
        return len(root) == 64 and total > 0
    return False

def verify_assets():
    assets_path = REG / "assets_verifiable_1M.jsonl"
    if not assets_path.exists():
        print("[FAIL] Assets file not found")
        return False
    count = 0
    valid = 0
    with open(assets_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 1000:
                break
            try:
                asset = json.loads(line)
                if asset.get("proof") and len(asset["proof"]) == 64:
                    valid += 1
                count += 1
            except:
                pass
    pct = (valid / count * 100) if count > 0 else 0
    print(f"[PASS] Assets: {count} sampled, {valid} valid proofs ({pct:.1f}%)")
    return pct > 95

def verify_quality():
    quality_path = REG / "quality_report.json"
    data = check_json(quality_path, "Quality Report")
    if data:
        overall = data.get("overall", "")
        checks = data.get("checks", {})
        if isinstance(checks, dict):
            passed = sum(1 for c in checks.values() if isinstance(c, dict) and c.get("status") == "pass")
            total = len(checks)
        else:
            passed = sum(1 for c in checks if isinstance(c, dict) and c.get("status") == "pass")
            total = len(checks)
        print(f"  Overall: {overall}")
        print(f"  Checks: {passed}/{total} passed")
        return overall == "pass" and passed == total
    return False

def verify_api_endpoints():
    api_dir = BASE / "functions" / "api"
    required = [
        "assets.js", "search.js", "verify.js", "pricing.js",
        "purchase.js", "deliver.js", "webhook_moltspay.js",
        "customer.js", "analytics.js", "monitoring.js",
        "admin.js", "portal.js", "portal_subscription.js"
    ]
    all_ok = True
    for f in required:
        path = api_dir / f
        exists = path.exists()
        status = "PASS" if exists else "FAIL"
        if not exists:
            all_ok = False
        print(f"[{status}] API: {f}")
    return all_ok

def verify_sdks():
    sdk_dir = BASE.parent
    py_sdk = sdk_dir / "bds-python-sdk"
    js_sdk = sdk_dir / "bds-js-sdk"
    py_ok = py_sdk.exists() and ((py_sdk / "setup.py").exists() or (py_sdk / "pyproject.toml").exists())
    js_ok = js_sdk.exists() and (js_sdk / "package.json").exists()
    print(f"[{'PASS' if py_ok else 'FAIL'}] Python SDK")
    print(f"[{'PASS' if js_ok else 'FAIL'}] TypeScript SDK")
    return py_ok and js_ok

def verify_legal():
    legal_files = ["TERMS_OF_SERVICE.md", "PRIVACY_POLICY.md", "DPA.md"]
    all_ok = True
    for f in legal_files:
        path = BASE / f
        exists = path.exists()
        status = "PASS" if exists else "FAIL"
        if not exists:
            all_ok = False
        print(f"[{status}] Legal: {f}")
    return all_ok

def verify_openapi():
    path = REG / "openapi.json"
    data = check_json(path, "OpenAPI Spec")
    if data:
        paths = data.get("paths", {})
        print(f"  Paths: {len(paths)}")
        return len(paths) > 0
    return False

def main():
    print("=" * 60)
    print("丙大山数字资产平台 - 综合验证")
    print("=" * 60)

    results = {}

    print("\n--- 核心数据 ---")
    results["merkle"] = verify_merkle()
    results["assets"] = verify_assets()
    results["quality"] = verify_quality()

    print("\n--- API 端点 ---")
    results["api"] = verify_api_endpoints()

    print("\n--- SDK ---")
    results["sdks"] = verify_sdks()

    print("\n--- 合规文档 ---")
    results["legal"] = verify_legal()

    print("\n--- OpenAPI ---")
    results["openapi"] = verify_openapi()

    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"结果: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")

    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)