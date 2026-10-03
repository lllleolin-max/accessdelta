"""Independent supported compact-source -> generated-model consumer closure.

Not a permission/optimum defect: no edits are needed. Inputs and all item counts
are admitted. Save exact generated model and call registered check on it.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sysconfig


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=False)
    actions = [f"a{i:04d}" for i in range(500)]
    raw = {"version": 1, "principals": ["p"], "roles": [], "actions": actions,
           "resources": ["r"], "memberships": [], "inheritance": [],
           "grants": [{"id": f"g{i:04d}", "subject": {"kind": "principal", "id": "p"},
                       "effect": "ALLOW", "actions": actions, "resources": ["r"]} for i in range(1000)]}
    rules = {"required": [["p", actions[0], "r"]], "forbidden": [], "edits": [], "protected": ["grant:g0000"]}
    source, constraints, proposal, repaired = (root / name for name in ("source.json", "constraints.json", "proposal.json", "repaired.json"))
    source.write_text(json.dumps(raw, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    constraints.write_text(json.dumps(rules, separators=(",", ":")), encoding="utf-8")
    assert source.stat().st_size < 4 * 1024 * 1024
    initial = {p.name: sha(p.read_bytes()) for p in (source, constraints)}
    cli = Path(sysconfig.get_path("scripts")) / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
    assert cli.is_file()
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONIOENCODING", None)
    env["PYTHONUTF8"] = "0"
    records = []
    def call(name, args):
        p = subprocess.run([str(cli)] + [str(a) for a in args], env=env, capture_output=True, timeout=90)
        (root / (name + ".stdout")).write_bytes(p.stdout)
        (root / (name + ".stderr")).write_bytes(p.stderr)
        data = json.loads((p.stdout or p.stderr).decode("utf-8"))
        records.append({"operation": name, "returncode": p.returncode, "stdout_bytes": len(p.stdout), "stderr_bytes": len(p.stderr),
                        "status": data.get("status"), "error_is_input_cap": data.get("error") == "JSON input exceeds 4 MiB"})
        return p, data
    p, plan = call("propose", ["propose", source, constraints])
    assert p.returncode == 0 and plan["status"] == "OPTIMAL" and plan["selected"] == [] and plan["cost"] == 0
    assert plan["complete"] and plan["ties_complete"] and plan["alternatives"] == []
    proposal.write_bytes(p.stdout)
    p, applied = call("apply", ["apply", source, constraints, proposal, repaired])
    assert p.returncode == 0 and repaired.exists(), "setup/apply failure is not a generated-model consumer counterexample"
    p, checked = call("check", ["check", source, constraints, proposal, repaired])
    assert p.returncode in (0, 2)
    assert initial == {p.name: sha(p.read_bytes()) for p in (source, constraints)}
    result = {"version": importlib.metadata.version("accessdelta"), "passed": p.returncode == 0 and checked.get("feasible") is True,
              "model_counts": {"principals": 1, "roles": 0, "actions": 500, "resources": 1, "grants": 1000, "requests": 500, "edits": 0},
              "source_bytes": source.stat().st_size, "constraints_bytes": constraints.stat().st_size, "proposal_bytes": proposal.stat().st_size,
              "repaired_bytes": repaired.stat().st_size, "source_sha256": initial["source.json"], "repaired_sha256": sha(repaired.read_bytes()),
              "commands": records, "source_bytes_preserved": True,
              "scope": "supported compact input, no edit or tie complexity; actual generated model consumed by registered check"}
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
