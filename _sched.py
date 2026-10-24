# Daily ingestion task - registers as Windows scheduled task
import subprocess, sys
from pathlib import Path

script = r"F:\2026\24xs\_ingest.py"
script2 = r"F:\2026\24xs\_ingest2.py"
task_name = "24xs_Asset_Ingestion"

# Create a combined script that runs both
combined = r"""
import sys
sys.path.insert(0, r"F:\2026\24xs")
exec(open(r"F:\2026\24xs\_ingest.py").read())
exec(open(r"F:\2026\24xs\_ingest2.py").read())
"""

# Write combined
combined_path = r"F:\2026\24xs\ingest_daily.py"
Path(combined_path).write_text(combined, encoding="utf-8")

# Register task (run daily at 03:00)
cmd = f"schtasks /create /tn {task_name} /tr \"python {combined_path}\" /sc daily /st 03:00 /f"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
print("Task registered" if result.returncode == 0 else "Failed")
