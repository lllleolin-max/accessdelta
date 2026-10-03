"""Independent bounded-proposal numeric closure probe; installed package only.

python ACCESSDELTA_NUMERIC_CLOSURE_PROBE.py --out NEW_PRIVATE_DIRECTORY
No digit-limit setting is changed. Raw console logs stay in that directory;
result.json contains no host paths or giant numeric tokens. Exit 1 denotes a
supported-input raw exception or failed completed-result closure, not wrong
permission arithmetic. Exit 0 requires the legitimate controls and closure.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

from accessdelta import Model, ModelError, apply, check, propose


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=False)
    limit = sys.get_int_max_str_digits()
    assert limit == 4300, "requires unchanged standard 4300-digit interpreter limit"
    console = Path(sysconfig.get_path("scripts")) / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
    assert console.is_file(), "registered installed-console missing"
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    raw = {"version": 1, "principals": ["p"], "roles": [], "actions": ["a"], "resources": ["r1", "r2"], "memberships": [], "inheritance": [],
           "grants": [{"id": "g" + str(i), "subject": {"kind": "principal", "id": "p"}, "effect": "ALLOW", "actions": ["a"], "resources": ["r" + str(i)]} for i in (1, 2)]}
    records = []
    passed = True
    for digits in (4299, 4300):
        case = root / ("digits-" + str(digits))
        case.mkdir()
        individual = int("9" * digits)
        expected = 2 * individual
        rules = {"required": [], "forbidden": [["p", "a", "r1"], ["p", "a", "r2"]], "edits": [{"kind": "grant", "id": "g" + str(i), "cost": individual} for i in (1, 2)], "protected": []}
        model_file, constraints_file = case / "model.json", case / "constraints.json"
        model_file.write_bytes(json.dumps(raw, sort_keys=True).encode("utf-8"))
        constraints_file.write_bytes(json.dumps(rules, sort_keys=True).encode("utf-8"))
        before = {p.name: sha(p.read_bytes()) for p in (model_file, constraints_file)}
        assert all(p.stat().st_size < 4 * 1024 * 1024 for p in (model_file, constraints_file))
        # Primitive oracle: each forbidden request has exactly one independent
        # unconditional ALLOW; only deleting both grants removes both requests.
        # No production subset/effective helpers determine this expected set.
        source = Model.from_dict(json.loads(model_file.read_bytes()))
        admitted = json.loads(constraints_file.read_bytes())
        oracle_keys = ["grant:g1", "grant:g2"]
        unbounded = propose(source, admitted, max_report_bytes=None)
        exact_arithmetic = unbounded["status"] == "OPTIMAL" and unbounded["cost"] == expected and unbounded["selected"] == oracle_keys and unbounded["alternatives"] == [] and unbounded["checked"] == 4
        assert exact_arithmetic
        repaired = apply(source, admitted, unbounded)
        assert not repaired.grants and check(source, admitted, unbounded, repaired)["feasible"]
        sdk = {"bounded_call": "returned"}
        try:
            bounded = propose(source, admitted)
            sdk.update(status=bounded["status"], complete=bounded["complete"], selected=bounded["selected"], cost_matches_oracle=bounded["cost"] == expected)
            if bounded["status"] == "OPTIMAL":
                sdk_ok = bounded["cost"] == expected and bounded["selected"] == oracle_keys
            else:
                sdk_ok = bounded["status"] == "UNKNOWN" and not bounded["complete"]
        except Exception as exc:
            sdk = {"bounded_call": "exception", "type": type(exc).__name__, "is_model_error": isinstance(exc, ModelError), "message": str(exc)}
            sdk_ok = False
        cli = subprocess.run([str(console), "propose", str(model_file), str(constraints_file)], env=env, capture_output=True)
        (case / "propose.stdout").write_bytes(cli.stdout)
        (case / "propose.stderr").write_bytes(cli.stderr)
        cli_record = {"operation": "propose", "exit": cli.returncode, "stdout_bytes": len(cli.stdout), "stderr_bytes": len(cli.stderr), "traceback": b"Traceback (most recent call last)" in cli.stderr}
        cli_ok = False
        try:
            payload = json.loads((cli.stdout or cli.stderr).decode("utf-8"))
            cli_record.update(json_valid=True, status=payload.get("status"), complete=payload.get("complete"))
            if cli.returncode == 0 and payload.get("status") == "OPTIMAL":
                cli_ok = payload.get("cost") == expected and payload.get("selected") == oracle_keys
                # Preserve successful proposal bytes exactly for real consumers.
                proposal_file = case / "proposal.json"
                proposal_file.write_bytes(cli.stdout)
                target = case / "repaired.json"
                operations = []
                for op, argv in (("apply", [model_file, constraints_file, proposal_file, target]), ("check", [model_file, constraints_file, proposal_file, target])):
                    run = subprocess.run([str(console), op] + [str(p) for p in argv], env=env, capture_output=True)
                    (case / (op + ".stdout")).write_bytes(run.stdout)
                    (case / (op + ".stderr")).write_bytes(run.stderr)
                    operations.append({"operation": op, "exit": run.returncode, "traceback": b"Traceback (most recent call last)" in run.stderr})
                    cli_ok &= run.returncode == 0
                cli_record["consumers"] = operations
            elif cli.returncode == 3 and payload.get("status") == "UNKNOWN" and payload.get("complete") is False:
                cli_ok = True
        except (UnicodeError, ValueError):
            cli_record["json_valid"] = False
        preserved = before == {p.name: sha(p.read_bytes()) for p in (model_file, constraints_file)}
        assert preserved and sys.get_int_max_str_digits() == limit
        records.append({"individual_cost_digits": digits, "sum_cost_digits": digits + 1, "sum_matches_2_times_10_power_minus_2": exact_arithmetic,
                        "candidate_count": 4, "unique_feasible_subset": oracle_keys, "unbounded_sdk_exact_feasible": True,
                        "model_bytes": model_file.stat().st_size, "constraints_bytes": constraints_file.stat().st_size,
                        "bounded_sdk": sdk, "console": cli_record, "source_hashes": before, "source_preserved": preserved,
                        "destination_allocated": (case / "repaired.json").exists(), "passed": bool(sdk_ok and cli_ok)})
        passed &= sdk_ok and cli_ok
    result = {"version": importlib.metadata.version("accessdelta"), "python_version": ".".join(map(str, sys.version_info[:3])), "int_max_str_digits_before_after": [limit, sys.get_int_max_str_digits()],
              "registered_console": "target-interpreter sysconfig scripts", "independent_oracle": "two independent ALLOWs require both deletions; exact integer sum, no production traversal or subset helpers", "cases": records, "passed": bool(passed)}
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
