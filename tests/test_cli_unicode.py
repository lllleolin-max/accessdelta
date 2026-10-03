"""Actual registered CLI, UTF-8 and legacy Windows pipes, success/error paths."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile
import unittest
from accessdelta import Model

PRINCIPAL = "user-\U0001f600"
ROLE = "writer-\U0001f40d"
ACTION = "write-\U0001f511"
RESOURCE = "deploy-\U0001f6f0"
GRANT = "grant-\U0001f30d"


def policy():
    return {"version": 1, "principals": [PRINCIPAL], "roles": [ROLE], "actions": ["read", ACTION], "resources": ["report", RESOURCE], "memberships": [{"id": "member-\U0001f680", "principal": PRINCIPAL, "role": ROLE}], "inheritance": [], "grants": [{"id": "keep", "subject": {"kind": "principal", "id": PRINCIPAL}, "effect": "ALLOW", "actions": ["read"], "resources": ["report"]}, {"id": GRANT, "subject": {"kind": "role", "id": ROLE}, "effect": "ALLOW", "actions": [ACTION], "resources": [RESOURCE]}]}


def constraints():
    return {"required": [[PRINCIPAL, "read", "report"]], "forbidden": [[PRINCIPAL, ACTION, RESOURCE]], "edits": [{"kind": "grant", "id": GRANT, "cost": 1}], "protected": ["grant:keep"]}


class UnicodePipeTests(unittest.TestCase):
    def run_cli(self, mode, expected, channel, *args):
        scripts = Path(sysconfig.get_path("scripts"))
        cli = scripts / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
        self.assertTrue(cli.is_file())
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)
        env.pop("PYTHONPATH", None)
        env["PYTHONUTF8"] = str(mode)
        result = subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stderr.decode("utf-8", errors="replace"))
        wire = result.stdout if channel == "stdout" else result.stderr
        other = result.stderr if channel == "stdout" else result.stdout
        self.assertEqual(other, b"")
        self.assertNotIn(b"Traceback", wire)
        self.assertNotIn(b"UnicodeEncodeError", wire)
        self.assertTrue(wire.isascii(), "wire JSON must be ASCII-safe even in legacy pipe mode")
        decoded = json.loads(wire.decode("utf-8"))
        self.assertIsInstance(decoded, dict)
        return decoded

    def test_unicode_full_workflow_preserves_sdk_values(self):
        for mode in (0, 1):
            with self.subTest(utf8_mode=mode), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                after, before, rules, proposal, repaired = (folder / (name + "-\U0001f600.json") for name in ("after", "before", "rules", "proposal", "repaired"))
                data, config = policy(), constraints()
                source = Model.from_dict(data)
                baseline = copy.deepcopy(data)
                baseline["grants"] = baseline["grants"][:1]
                for path, value in ((after, data), (before, baseline), (rules, config)):
                    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                report = self.run_cli(mode, 0, "stdout", "compare", before, after)
                self.assertEqual(report["added"][0]["request"], [PRINCIPAL, ACTION, RESOURCE])
                self.assertEqual(report["added"][0]["decision"], "ALLOW")
                self.assertEqual(report["after"], source.digest)
                inspected = self.run_cli(mode, 0, "stdout", "inspect", after, PRINCIPAL, ACTION, RESOURCE)
                self.assertEqual(inspected["request"], [PRINCIPAL, ACTION, RESOURCE])
                self.assertEqual(inspected["evidence"][0]["grant"], GRANT)
                plan = self.run_cli(mode, 0, "stdout", "propose", after, rules)
                self.assertEqual(plan["selected"], ["grant:" + GRANT])
                self.assertIs(type(plan["cost"]), int)
                self.assertEqual(plan["status"], "OPTIMAL")
                proposal.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
                written = self.run_cli(mode, 0, "stdout", "apply", after, rules, proposal, repaired)
                self.assertEqual(written["written"], str(repaired))
                edited = Model.from_dict(json.loads(repaired.read_text(encoding="utf-8")))
                self.assertEqual(edited.principals, (PRINCIPAL,))
                self.assertEqual(edited.digest, written["model"])
                checked = self.run_cli(mode, 0, "stdout", "check", after, rules, proposal, repaired)
                self.assertIs(checked["feasible"], True)
                self.assertIn("does not certify optimality", checked["scope"])
                certified = self.run_cli(mode, 0, "stdout", "certify", after, rules, proposal)
                self.assertIs(certified["certified"], True)
                self.assertEqual(certified["oracle"]["solutions"], [["grant:" + GRANT]])

    def test_unicode_error_and_bounded_outputs(self):
        for mode in (0, 1):
            with self.subTest(utf8_mode=mode), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                source, rules, invalid = (folder / (name + "-\U0001f600.json") for name in ("source", "rules", "invalid"))
                source.write_text(json.dumps(policy(), ensure_ascii=False), encoding="utf-8")
                rules.write_text(json.dumps(constraints(), ensure_ascii=False), encoding="utf-8")
                invalid.write_text('{"key-\U0001f600":1,"key-\U0001f600":2}', encoding="utf-8")
                error = self.run_cli(mode, 2, "stderr", "inspect", invalid, PRINCIPAL, ACTION, RESOURCE)
                self.assertEqual(error["status"], "INVALID")
                self.assertIn("key-\U0001f600", error["error"])
                missing = folder / "missing-\U0001f600.json"
                error = self.run_cli(mode, 2, "stderr", "inspect", missing, PRINCIPAL, ACTION, RESOURCE)
                self.assertIn("missing-\U0001f600.json", error["error"])
                data = policy()
                data["grants"][0]["conditions"] = False
                invalid.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                self.assertEqual(self.run_cli(mode, 3, "stderr", "inspect", invalid, PRINCIPAL, ACTION, RESOURCE)["status"], "UNKNOWN")
                unknown = self.run_cli(mode, 3, "stdout", "propose", source, rules, "--max-candidates", "0")
                self.assertEqual(unknown["status"], "UNKNOWN")
                self.assertIsNone(unknown["selected"])
                protected = constraints()
                protected["protected"].append("grant:" + GRANT)
                invalid.write_text(json.dumps(protected, ensure_ascii=False), encoding="utf-8")
                self.assertEqual(self.run_cli(mode, 4, "stdout", "propose", source, invalid)["status"], "INFEASIBLE")
                argerror = self.run_cli(mode, 2, "stderr", "propose", source, rules, "--max-candidates", "\U0001f600")
                self.assertIn("\U0001f600", argerror["error"])
                self.assertEqual(self.run_cli(mode, 2, "stderr", "unknown-\U0001f600")["status"], "INVALID")
                self.assertIsInstance(self.run_cli(mode, 0, "stdout", "--help")["help"], str)


if __name__ == "__main__":
    unittest.main()
