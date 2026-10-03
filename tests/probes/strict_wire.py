"""Frozen round-2 probe: no ambiguous wire input becomes unconditional ALLOW."""
import copy
import json
from pathlib import Path
import tempfile
from accessdelta import Model, ModelError
from accessdelta.cli import read

base = {"version": 1, "principals": ["p"], "roles": [], "actions": ["a"], "resources": ["r"], "memberships": [], "inheritance": [], "grants": [{"id": "g", "subject": {"kind": "principal", "id": "p"}, "effect": "ALLOW", "actions": ["a"], "resources": ["r"]}]}
checks = []
for condition in ([], False, 0, "", None):
    data = copy.deepcopy(base)
    data["grants"][0]["conditions"] = condition
    try:
        Model.from_dict(data)
        rejected = False
    except ModelError:
        rejected = True
    checks.append({"case": f"condition-{condition!r}", "rejected": rejected})
data = copy.deepcopy(base)
data["version"] = True
try:
    Model.from_dict(data)
    rejected = False
except ModelError:
    rejected = True
checks.append({"case": "boolean-version", "rejected": rejected})
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "ambiguous.json"
    path.write_text('{"effect":"DENY","effect":"ALLOW"}', encoding="utf-8")
    try:
        read(path)
        rejected = False
    except ModelError:
        rejected = True
    checks.append({"case": "duplicate-json-effect", "rejected": rejected})
print(json.dumps({"checks": checks, "pass": all(x["rejected"] for x in checks)}))
assert all(x["rejected"] for x in checks), "ambiguous/restriction-shaped input silently accepted"
