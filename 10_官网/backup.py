import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
REG = BASE.parent / "11_数据资产" / "registry_real_verified"
BACKUP_DIR = BASE / "backups"

def create_backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    backup_path.mkdir(exist_ok=True)

    files_to_backup = [
        "assets_verifiable_1M.jsonl",
        "merkle_tree.json",
        "quality_report.json",
        "pricing_engine.json",
        "license_registry.json",
        "customer_schema.json",
        "analytics_config.json",
        "runbooks.json",
        "openapi.json",
    ]

    for f in files_to_backup:
        src = REG / f
        if src.exists():
            shutil.copy2(src, backup_path / f)
            print(f"[OK] {f}")

    config_files = [
        "TERMS_OF_SERVICE.md",
        "PRIVACY_POLICY.md",
        "DPA.md",
        "README.md",
        "DEPLOYMENT.md",
    ]
    for f in config_files:
        src = BASE / f
        if src.exists():
            shutil.copy2(src, backup_path / f)
            print(f"[OK] {f}")

    zip_path = BACKUP_DIR / f"{backup_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in backup_path.iterdir():
            zf.write(f, f.name)

    shutil.rmtree(backup_path)
    print(f"\nBackup created: {zip_path}")
    print(f"Size: {zip_path.stat().st_size:,} bytes")
    return zip_path

def list_backups():
    if not BACKUP_DIR.exists():
        print("No backups found")
        return
    backups = sorted(BACKUP_DIR.glob("backup_*.zip"), reverse=True)
    if not backups:
        print("No backups found")
        return
    print(f"Found {len(backups)} backup(s):")
    for b in backups:
        size = b.stat().st_size
        print(f"  {b.name} ({size:,} bytes)")

def restore_backup(backup_name):
    zip_path = BACKUP_DIR / backup_name
    if not zip_path.exists():
        print(f"Backup not found: {backup_name}")
        return False
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(REG)
    print(f"Restored from: {backup_name}")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_backups()
        elif sys.argv[1] == "restore" and len(sys.argv) > 2:
            restore_backup(sys.argv[2])
        else:
            print("Usage: python backup.py [list|restore <name>]")
    else:
        create_backup()