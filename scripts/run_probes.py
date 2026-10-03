"""Run the unchanged review probes against the installed package."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
results = []
for path in sorted((root / "tests/probes").glob("*.py")):
    result = subprocess.run([sys.executable, path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    results.append({"probe": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
print(json.dumps({"results": results, "pass": all(x["returncode"] == 0 for x in results)}, indent=2))
raise SystemExit(0 if all(x["returncode"] == 0 for x in results) else 1)
