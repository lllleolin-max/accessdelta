"""Run the unchanged review probes against the installed package."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
results = []
for path in sorted((root / "tests/probes").glob("*.py")):
    with tempfile.TemporaryDirectory(prefix="accessdelta-probe-") as directory:
        args = [sys.executable, path]
        if path.name in ("tie_cap_probe.py", "repaired_file_cap_probe.py", "numeric_closure_probe.py"):
            args += ["--out", str(Path(directory) / "consumer")]
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    results.append({"probe": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
print(json.dumps({"results": results, "pass": all(x["returncode"] == 0 for x in results)}, indent=2))
raise SystemExit(0 if all(x["returncode"] == 0 for x in results) else 1)
