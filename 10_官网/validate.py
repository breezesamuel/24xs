import json
import hashlib
from pathlib import Path

BASE = Path(__file__).parent
REG = BASE.parent / "11_数据资产" / "registry_real_verified"

def validate_merkle():
    print("验证 Merkle Tree...")
    merkle_path = REG / "merkle_tree.json"
    if not merkle_path.exists():
        print("  [FAIL] merkle_tree.json 不存在")
        return False
    data = json.loads(merkle_path.read_text(encoding="utf-8"))
    root = data.get("root", "")
    total = data.get("total", 0)
    levels = data.get("levels", 0)
    if len(root) != 64:
        print(f"  [FAIL] root 长度错误: {len(root)}")
        return False
    if total < 1000000:
        print(f"  [FAIL] total 数量不足: {total}")
        return False
    if levels < 20:
        print(f"  [FAIL] levels 层数不足: {levels}")
        return False
    print(f"  [PASS] root={root[:16]}... total={total:,} levels={levels}")
    return True

def validate_assets():
    print("验证资产数据...")
    assets_path = REG / "assets_verifiable_1M.jsonl"
    if not assets_path.exists():
        print("  [FAIL] assets_verifiable_1M.jsonl 不存在")
        return False
    count = 0
    valid = 0
    with open(assets_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 10000:
                break
            try:
                asset = json.loads(line)
                proof = asset.get("proof", "")
                if len(proof) == 64:
                    valid += 1
                count += 1
            except:
                pass
    pct = (valid / count * 100) if count > 0 else 0
    if pct < 95:
        print(f"  [FAIL] 有效率过低: {pct:.1f}%")
        return False
    print(f"  [PASS] 采样 {count} 条，有效 {valid} 条 ({pct:.1f}%)")
    return True

def validate_quality():
    print("验证质量报告...")
    quality_path = REG / "quality_report.json"
    if not quality_path.exists():
        print("  [FAIL] quality_report.json 不存在")
        return False
    data = json.loads(quality_path.read_text(encoding="utf-8"))
    overall = data.get("overall", "")
    if overall != "pass":
        print(f"  [FAIL] overall 状态错误: {overall}")
        return False
    checks = data.get("checks", [])
    passed = sum(1 for c in checks if c.get("status") == "pass")
    if passed < 8:
        print(f"  [FAIL] 检查通过数不足: {passed}/8")
        return False
    print(f"  [PASS] {passed}/8 检查通过")
    return True

def validate_configs():
    print("验证配置文件...")
    configs = [
        "pricing_engine.json",
        "license_registry.json",
        "customer_schema.json",
        "analytics_config.json",
        "runbooks.json",
        "openapi.json",
    ]
    all_ok = True
    for c in configs:
        path = REG / c
        if not path.exists():
            print(f"  [FAIL] {c} 不存在")
            all_ok = False
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            print(f"  [PASS] {c}")
        except:
            print(f"  [FAIL] {c} JSON 格式错误")
            all_ok = False
    return all_ok

def validate_legal():
    print("验证合规文档...")
    docs = ["TERMS_OF_SERVICE.md", "PRIVACY_POLICY.md", "DPA.md"]
    all_ok = True
    for d in docs:
        path = BASE / d
        if not path.exists():
            print(f"  [FAIL] {d} 不存在")
            all_ok = False
        else:
            print(f"  [PASS] {d}")
    return all_ok

def main():
    print("=" * 60)
    print("丙大山数字资产平台 - 数据验证")
    print("=" * 60)
    results = []
    results.append(validate_merkle())
    results.append(validate_assets())
    results.append(validate_quality())
    results.append(validate_configs())
    results.append(validate_legal())
    print("=" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"结果: {passed}/{total} 通过")
    if passed == total:
        print("ALL VALIDATIONS PASSED")
    else:
        print("SOME VALIDATIONS FAILED")
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)