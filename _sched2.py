# Post-ingest rebuild (merkle + search)
import subprocess, sys
from pathlib import Path

rebuild = r"""
import sys
sys.path.insert(0, r"F:\2026\24xs")
exec(open(r"F:\2026\24xs\_merkle.py").read())
exec(open(r"F:\2026\24xs\_search.py").read())
"""

rebuild_path = r"F:\2026\24xs\rebuild_daily.py"
Path(rebuild_path).write_text(rebuild, encoding="utf-8")

cmd = "schtasks /create /tn 24xs_Asset_Rebuild /tr \"python F:\\\\2026\\\\24xs\\\\rebuild_daily.py\" /sc daily /st 03:30 /f"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)
print("Rebuild task registered")
