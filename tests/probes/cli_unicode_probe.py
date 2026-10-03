"""Independent frozen probe: registered Windows CLI must emit JSON for Unicode IDs.

Run with an ordinary installed wheel. This exercises legacy Windows pipe encoding
explicitly because Python 3.11 and the local Python 3.14 environment use it.
No package helpers or source imports are injected.
"""
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile


def main():
    scripts = Path(sysconfig.get_path("scripts"))
    cli = scripts / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
    policy = {"version": 1, "principals": ["user-\U0001f600"], "roles": [],
              "actions": ["read"], "resources": ["report"], "memberships": [],
              "inheritance": [], "grants": [{"id": "g", "subject": {"kind": "principal", "id": "user-\U0001f600"},
              "effect": "ALLOW", "actions": ["read"], "resources": ["report"]}]}
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)
    # Reproducible supported-platform stdout pipe condition, not malformed JSON.
    env["PYTHONUTF8"] = "0"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "unicode.json"
        path.write_text(json.dumps(policy, ensure_ascii=False), encoding="utf-8")
        p = subprocess.run([str(cli), "inspect", str(path), "user-\U0001f600", "read", "report"],
                           env=env, capture_output=True, timeout=15)
    valid = False
    if p.returncode == 0:
        try:
            result = json.loads(p.stdout.decode("utf-8"))
            valid = result["decision"] == "ALLOW" and result["request"][0] == "user-\U0001f600"
        except (ValueError, UnicodeError, KeyError):
            pass
    summary = {"pass": valid, "returncode": p.returncode,
               "stdout_is_utf8_json": valid,
               "stderr_contains_UnicodeEncodeError": b"UnicodeEncodeError" in p.stderr,
               "condition": "Windows legacy pipe encoding, PYTHONUTF8=0; printable emoji identifier"}
    print(json.dumps(summary, sort_keys=True))
    assert valid, "registered CLI cannot emit supported Unicode identifier as UTF-8 JSON"


if __name__ == "__main__":
    main()
