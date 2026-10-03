import copy
import json
from pathlib import Path
import subprocess
import sysconfig
import tempfile
import unittest
from accessdelta import Model, propose, apply, check, certify

ROOT = Path(__file__).resolve().parents[1] / "examples"


class InstalledCLITests(unittest.TestCase):
    def test_registered_cli_wire_and_write_boundaries(self):
        scripts = Path(sysconfig.get_path("scripts"))
        cli = scripts / ("accessdelta.exe" if (scripts / "accessdelta.exe").exists() else "accessdelta")
        self.assertTrue(cli.exists(), "ordinary installed registered CLI is missing")
        def run(*args):
            return subprocess.run([str(cli), *map(str, args)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        source = ROOT / "simple/after.json"
        rules = ROOT / "simple/constraints.json"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            proposal = folder / "proposal.json"
            result = run("propose", source, rules)
            self.assertEqual(result.returncode, 0, result.stderr)
            proposal.write_text(result.stdout, encoding="utf-8")
            refused = run("apply", source, rules, proposal, source)
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(source.read_bytes(), original)
            target = folder / "repaired.json"
            self.assertEqual(run("apply", source, rules, proposal, target).returncode, 0)
            self.assertEqual(run("check", source, rules, proposal, target).returncode, 0)
            self.assertEqual(run("certify", source, rules, proposal).returncode, 0)
            self.assertEqual(run("propose", source, rules, "--max-candidates", "0").returncode, 3)
            malformed = folder / "malformed.json"
            malformed.write_text('{"effect":"DENY","effect":"ALLOW"}', encoding="utf-8")
            invalid = run("inspect", malformed, "alice", "write", "deploy")
            self.assertEqual(invalid.returncode, 2)
            self.assertNotIn("Traceback", invalid.stderr)
            data = json.loads(original)
            data["grants"][0]["conditions"] = False
            malformed.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(run("inspect", malformed, "alice", "write", "deploy").returncode, 3)
            protected = json.loads(rules.read_text())
            protected["protected"].append("grant:unwanted")
            malformed.write_text(json.dumps(protected), encoding="utf-8")
            self.assertEqual(run("propose", source, malformed).returncode, 4)

    def test_feasibility_checker_does_not_certify_optimum(self):
        model = Model.from_dict(json.loads((ROOT / "cost-trap/after.json").read_text()))
        rules = json.loads((ROOT / "cost-trap/constraints.json").read_text())
        proposal = copy.deepcopy(propose(model, rules))
        proposal["selected"] = ["grant:deploy-write", "grant:secret-read"]
        proposal["cost"] = 4
        repaired = apply(model, rules, proposal)
        self.assertTrue(check(model, rules, proposal, repaired)["feasible"])
        self.assertIn("does not certify optimality", check(model, rules, proposal, repaired)["scope"])
        self.assertFalse(certify(model, rules, proposal)["certified"])


if __name__ == "__main__":
    unittest.main()
