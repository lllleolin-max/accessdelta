"""Independent successful-proposal consumer closure probe.

Run with an ordinary installed accessdelta interpreter:
python ACCESSDELTA_TIE_CAP_AUDIT_PROBE.py --out NEW_PRIVATE_DIRECTORY

Writes synthetic inputs and actual console stdout privately; result.json is
path-free. All-zero tied subsets are legitimate, not unsafe permissions.
A completed CLI proposal must be consumable by the advertised apply/check.
Honest bounded UNKNOWN/incomplete output is not mislabeled a completed result.
"""
import argparse
import hashlib
import importlib.metadata
import itertools
import json
import os
from pathlib import Path
import subprocess
import sysconfig

from accessdelta import Model, apply, check, propose


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=False)
    console = Path(sysconfig.get_path("scripts")) / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
    assert console.is_file(), "registered target-interpreter console missing"
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    records = []
    closure_ok = True
    for count in (12, 14):
        folder = root / f"case-{count}"
        folder.mkdir()
        names = [f"d{i:02d}-" + "x" * 95 for i in range(count)]
        assert all(len(x) == 99 for x in names)
        raw = {"version": 1, "principals": ["alice"], "roles": [], "actions": ["read"], "resources": ["report", "secret"], "memberships": [], "inheritance": [],
               "grants": [{"id": "keep-required", "subject": {"kind": "principal", "id": "alice"}, "effect": "ALLOW", "actions": ["read"], "resources": ["report"]}] +
                         [{"id": name, "subject": {"kind": "principal", "id": "alice"}, "effect": "ALLOW", "actions": [], "resources": ["report"]} for name in names]}
        rules = {"required": [["alice", "read", "report"]], "forbidden": [["alice", "read", "secret"]], "edits": [{"kind": "grant", "id": name, "cost": 0} for name in names], "protected": ["grant:keep-required"]}
        model_file, constraints_file = folder / "model.json", folder / "constraints.json"
        model_file.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
        constraints_file.write_text(json.dumps(rules, sort_keys=True) + "\n", encoding="utf-8")
        before = {file.name: digest(file.read_bytes()) for file in (model_file, constraints_file)}
        # Primitive oracle: each edited grant has empty actions, so no request
        # is changed. Every subset is feasible and all costs are exactly zero.
        # Bitmask enumeration does not call production traversal/removal helpers.
        keys = ["grant:" + name for name in names]
        expected = {tuple(keys[i] for i in range(count) if mask & (1 << i)) for mask in range(1 << count)}
        model = Model.from_dict(raw)
        sdk = propose(model, rules, max_candidates=1 << count)
        if sdk["status"] == "OPTIMAL":
            assert sdk["complete"] and sdk["ties_complete"] and sdk["checked"] == (1 << count)
            assert sdk["selected"] == [] and sdk["cost"] == 0
            assert {tuple(sdk["selected"]), *(tuple(x) for x in sdk["alternatives"])} == expected
        else:
            assert sdk["status"] == "UNKNOWN" and not sdk["complete"] and not sdk["ties_complete"]
        repaired = apply(model, rules, sdk)
        assert repaired.digest == model.digest and check(model, rules, sdk, repaired)["feasible"]
        commands = []
        def call(label, argv):
            run = subprocess.run([str(console)] + [str(a) for a in argv], env=env, capture_output=True)
            (folder / (label + ".stdout")).write_bytes(run.stdout)
            (folder / (label + ".stderr")).write_bytes(run.stderr)
            parsed = json.loads((run.stdout or run.stderr).decode("utf-8"))
            commands.append({"operation": label, "exit": run.returncode, "stdout_bytes": len(run.stdout), "stderr_bytes": len(run.stderr), "error": parsed.get("error")})
            return run, parsed
        run, plan = call("propose", ["propose", model_file, constraints_file, "--max-candidates", str(1 << count)])
        assert run.returncode in (0, 3)
        assert plan["cost"] == 0 and plan["selected"] == []
        if run.returncode == 0:
            assert plan["status"] == "OPTIMAL" and plan["complete"] and plan["ties_complete"]
            assert {tuple(plan["selected"]), *(tuple(x) for x in plan["alternatives"])} == expected
        else:
            assert plan["status"] == "UNKNOWN" and not plan["complete"] and not plan["ties_complete"]
        proposal = folder / "proposal.json"
        proposal.write_bytes(run.stdout)  # exact actual successful stdout; no rewriting
        output = folder / "repaired.json"
        applied, _ = call("apply", ["apply", model_file, constraints_file, proposal, output])
        # Selected is empty. Original source is the correct repaired model when
        # apply fails before allocation; this independently supplies check's
        # valid fourth input rather than a missing-file harness error.
        checked, _ = call("check", ["check", model_file, constraints_file, proposal, output if output.exists() else model_file])
        consumed = applied.returncode == checked.returncode == 0
        closure_ok &= consumed
        assert before == {file.name: digest(file.read_bytes()) for file in (model_file, constraints_file)}
        records.append({"edits": count, "identifier_characters": 99, "declared_request_count": 2, "max_candidates": 1 << count,
                        "independent_feasible_zero_cost_subset_count": len(expected), "sdk_status": sdk["status"], "sdk_apply_and_check_feasible": True,
                        "model_bytes": model_file.stat().st_size, "constraints_bytes": constraints_file.stat().st_size,
                        "proposal_bytes": proposal.stat().st_size, "proposal_sha256": digest(proposal.read_bytes()), "cli_status": plan["status"],
                        "cli_complete": plan["complete"], "cli_tied_subset_count": 1 + len(plan["alternatives"]), "commands": commands,
                        "proposal_consumed_by_apply_and_check": consumed, "destination_created": output.exists(), "source_bytes_preserved": True})
    result = {"version": importlib.metadata.version("accessdelta"), "passed": closure_ok, "records": records,
              "scope": "finite legal irrelevant zero-cost deletions; no external accounts; SDK correctness versus successful CLI report consumption distinguished"}
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if closure_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
