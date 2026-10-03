"""Use the actual registered sysconfig Scripts entry point for the local workflow."""
import json
from pathlib import Path
import subprocess
import sysconfig
import tempfile


def main():
    scripts = Path(sysconfig.get_path("scripts"))
    cli = scripts / ("accessdelta.exe" if (scripts / "accessdelta.exe").exists() else "accessdelta")
    root = Path(__file__).resolve().parents[1] / "examples" / "deny-diamond"
    before, after, rules = (root / f"{x}.json" for x in ("before", "after", "constraints"))
    def run(*args):
        result = subprocess.run([str(cli), *map(str, args)], capture_output=True, text=True, check=True, encoding="utf-8")
        return json.loads(result.stdout)
    with tempfile.TemporaryDirectory(prefix="accessdelta-demo-") as folder:
        folder = Path(folder)
        proposal = folder / "proposal.json"
        repaired = folder / "repaired.json"
        delta = run("compare", before, after)
        evidence = run("inspect", after, "alice", "read", "secret")
        plan = run("propose", after, rules)
        proposal.write_text(json.dumps(plan), encoding="utf-8")
        applied = run("apply", after, rules, proposal, repaired)
        checked = run("check", after, rules, proposal, repaired)
        certified = run("certify", after, rules, proposal)
        assert evidence["decision"] == "DENY" and plan["selected"] == ["grant:bad-write"] and checked["feasible"] and certified["certified"]
        print(json.dumps({"registered_cli": str(cli), "delta": delta, "secret_evidence": evidence, "proposal": plan, "apply": applied, "check": checked, "certify": certified}, indent=2))


if __name__ == "__main__":
    main()
