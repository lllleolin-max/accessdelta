"""Producer/consumer byte boundaries, real registered CLI, immutable sources."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile
import unittest
from accessdelta import Model, ModelError, propose, apply, check, certify
from accessdelta.cli import read
from accessdelta.model import MAX_JSON_BYTES, canonical, wire_json


def irrelevant(count=3, unicode=False):
    ids = [f"g{i}-" + ("\U0001f600" * 20 if unicode else "x" * 95) for i in range(count)]
    data = {"version": 1, "principals": ["alice"], "roles": [], "actions": ["read"], "resources": ["report", "secret"], "memberships": [], "inheritance": [], "grants": [{"id": "keep", "subject": {"kind": "principal", "id": "alice"}, "effect": "ALLOW", "actions": ["read"], "resources": ["report"]}] + [{"id": name, "subject": {"kind": "principal", "id": "alice"}, "effect": "ALLOW", "actions": [], "resources": ["report"]} for name in ids]}
    rules = {"required": [["alice", "read", "report"]], "forbidden": [["alice", "read", "secret"]], "edits": [{"kind": "grant", "id": name, "cost": 0} for name in ids], "protected": ["grant:keep"]}
    return Model.from_dict(data), rules


class ReportByteTests(unittest.TestCase):
    def test_exact_report_budget_and_one_byte_less(self):
        for unicode in (False, True):
            with self.subTest(unicode=unicode):
                model, rules = irrelevant(unicode=unicode)
                full = propose(model, rules, max_report_bytes=None)
                budget = len(wire_json(full))
                exact = propose(model, rules, max_report_bytes=budget)
                self.assertEqual(exact, full)
                self.assertEqual(len(wire_json(exact)), budget)
                bounded = propose(model, rules, max_report_bytes=budget - 1)
                self.assertEqual(bounded["status"], "UNKNOWN")
                self.assertEqual(bounded["termination"], "MAX_REPORT_BYTES")
                self.assertFalse(bounded["complete"])
                self.assertFalse(bounded["ties_complete"])
                self.assertLessEqual(len(wire_json(bounded)), budget - 1)
                self.assertEqual(bounded["selected"], [])
                repaired = apply(model, rules, bounded)
                self.assertEqual(repaired.digest, model.digest)
                self.assertTrue(check(model, rules, bounded, repaired)["feasible"])
                self.assertFalse(certify(model, rules, bounded)["certified"])
                self.assertEqual([full["selected"]] + full["alternatives"], certify(model, rules, full)["oracle"]["solutions"])

    def test_budget_validation_and_legacy_proposal_consumption(self):
        model, rules = irrelevant()
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ModelError):
                propose(model, rules, max_report_bytes=value)
        with self.assertRaises(ModelError):
            propose(model, rules, max_report_bytes=10)
        legacy = propose(model, rules)
        del legacy["termination"]
        self.assertTrue(check(model, rules, legacy, apply(model, rules, legacy))["feasible"])

    def test_reader_exact_cap_and_cap_plus_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "json.json"
            raw = b'{"ok":true}'
            path.write_bytes(raw + b" " * (MAX_JSON_BYTES - len(raw)))
            self.assertEqual(read(path), {"ok": True})
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ModelError, "exceeds 4 MiB"):
                read(path)

    def test_registered_cli_bounded_stdout_is_directly_consumable(self):
        model, rules = irrelevant()
        full = propose(model, rules, max_report_bytes=None)
        budget = len(wire_json(full)) - 1
        scripts = Path(sysconfig.get_path("scripts"))
        cli = scripts / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source, constraints, proposal, target = (folder / f"{name}.json" for name in ("source", "constraints", "proposal", "target"))
            source.write_bytes(canonical(model.to_dict()).encode("utf-8"))
            constraints.write_bytes(wire_json(rules))
            originals = (source.read_bytes(), constraints.read_bytes())
            def call(*args):
                return subprocess.run([str(cli), *map(str, args)], capture_output=True, timeout=90)
            planned = call("propose", source, constraints, "--max-report-bytes", budget)
            self.assertEqual(planned.returncode, 3)
            self.assertEqual(planned.stderr, b"")
            self.assertLessEqual(len(planned.stdout), budget)
            self.assertEqual(json.loads(planned.stdout)["termination"], "MAX_REPORT_BYTES")
            proposal.write_bytes(planned.stdout)
            self.assertEqual(call("apply", source, constraints, proposal, target).returncode, 0)
            self.assertEqual(call("check", source, constraints, proposal, target).returncode, 0)
            sentinel = b"existing destination must remain"
            target.write_bytes(sentinel)
            self.assertEqual(call("apply", source, constraints, proposal, target).returncode, 2)
            self.assertEqual(target.read_bytes(), sentinel)
            self.assertEqual((source.read_bytes(), constraints.read_bytes()), originals)
            self.assertEqual(call("propose", source, constraints, "--max-report-bytes", MAX_JSON_BYTES + 1).returncode, 2)

    def test_exact_cap_model_output_without_added_lf_and_refusal_before_allocation(self):
        actions = [f"a{i:04d}" for i in range(500)]
        data = {"version": 1, "principals": ["p"], "roles": [], "actions": actions, "resources": ["r"], "memberships": [], "inheritance": [], "grants": [{"id": f"g{i:04d}", "subject": {"kind": "principal", "id": "p"}, "effect": "ALLOW", "actions": actions, "resources": ["r"]} for i in range(1000)]}
        base = len(canonical(data).encode("utf-8"))
        each, extra = divmod(MAX_JSON_BYTES - base, 1000)
        for i, grant in enumerate(data["grants"]):
            grant["id"] += "x" * (each + (i < extra))
        raw = canonical(data).encode("utf-8")
        self.assertEqual(len(raw), MAX_JSON_BYTES)
        rules = {"required": [["p", actions[0], "r"]], "forbidden": [], "edits": [], "protected": ["grant:" + data["grants"][0]["id"]]}
        scripts = Path(sysconfig.get_path("scripts"))
        cli = scripts / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source, constraints, proposal, target = (folder / f"{name}.json" for name in ("source", "constraints", "proposal", "target"))
            source.write_bytes(raw)
            constraints.write_bytes(wire_json(rules))
            def call(*args):
                return subprocess.run([str(cli), *map(str, args)], capture_output=True, timeout=90)
            planned = call("propose", source, constraints)
            self.assertEqual(planned.returncode, 0, planned.stderr)
            proposal.write_bytes(planned.stdout)
            self.assertEqual(call("apply", source, constraints, proposal, target).returncode, 0)
            self.assertEqual(target.read_bytes(), raw)
            self.assertEqual(target.stat().st_size, MAX_JSON_BYTES)
            self.assertFalse(target.read_bytes().endswith(b"\n"))
            self.assertEqual(call("check", source, constraints, proposal, target).returncode, 0)
            over_source, over_proposal = folder / "source-over.json", folder / "proposal-over.json"
            over_source.write_bytes(raw + b"\n")
            over_proposal.write_bytes(planned.stdout + b" " * (MAX_JSON_BYTES + 1 - len(planned.stdout)))
            sentinel = b"unchanged destination"
            target.write_bytes(sentinel)
            absent = folder / "absent-parent" / "out.json"
            for bad_source, bad_proposal in ((over_source, proposal), (source, over_proposal)):
                for destination in (target, absent):
                    refused = call("apply", bad_source, constraints, bad_proposal, destination)
                    self.assertEqual(refused.returncode, 2)
                    self.assertEqual(json.loads(refused.stderr)["status"], "INVALID")
                    self.assertEqual(target.read_bytes(), sentinel)
                    self.assertFalse(absent.parent.exists())
            self.assertEqual(source.read_bytes(), raw)
