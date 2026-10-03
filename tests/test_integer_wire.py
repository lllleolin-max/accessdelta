"""Exact arithmetic versus bounded integer JSON, without global digit changes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest

from accessdelta import Model, ModelError, propose, apply, check, certify
from accessdelta.cli import read
from accessdelta.model import canonical, wire_json, json_integer, JSON_INTEGER_LIMIT
from accessdelta.repair import parse_constraints, feasibility
from accessdelta.oracle import exhaustive_oracle


def independent_grants(count=2, cost=None):
    cost = JSON_INTEGER_LIMIT - 1 if cost is None else cost
    data = {"version": 1, "principals": ["p"], "roles": [], "actions": ["a"], "resources": ["r"], "memberships": [], "inheritance": [], "grants": [{"id": "g" + str(i), "subject": {"kind": "principal", "id": "p"}, "effect": "ALLOW", "actions": ["a"], "resources": ["r"]} for i in range(count)]}
    rules = {"required": [], "forbidden": [["p", "a", "r"]], "edits": [{"kind": "grant", "id": "g" + str(i), "cost": cost} for i in range(count)], "protected": []}
    return Model.from_dict(data), rules


class IntegerWireTests(unittest.TestCase):
    def test_exact_integer_codec_and_one_over_typed_refusal(self):
        limit = sys.get_int_max_str_digits()
        for integer in (0, 1, -1, 10 ** 639, JSON_INTEGER_LIMIT - 1, 1 - JSON_INTEGER_LIMIT):
            value = {"n": integer, "text": "user-\U0001f600", "list": [True, None, integer]}
            raw = wire_json(value)
            self.assertEqual(json.loads(raw, parse_int=json_integer), value)
            self.assertEqual(raw, (json.dumps(value, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii"))
            self.assertEqual(canonical(value), json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        for integer in (JSON_INTEGER_LIMIT, -JSON_INTEGER_LIMIT):
            for encode in (canonical, wire_json):
                with self.assertRaisesRegex(ModelError, "4300 decimal digits"):
                    encode({"n": integer})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "number.json"
            path.write_bytes(b'{"n":' + b"9" * 4300 + b"}")
            self.assertEqual(read(path)["n"], JSON_INTEGER_LIMIT - 1)
            path.write_bytes(b'{"n":1' + b"0" * 4300 + b"}")
            with self.assertRaisesRegex(ModelError, "4300 decimal digits"):
                read(path)
        self.assertEqual(sys.get_int_max_str_digits(), limit)

    def test_bounded_numeric_unknown_preserves_exact_unbounded_sdk(self):
        limit = sys.get_int_max_str_digits()
        model, rules = independent_grants()
        unbounded = propose(model, rules, max_report_bytes=None)
        self.assertEqual(unbounded["cost"], 2 * (JSON_INTEGER_LIMIT - 1))
        self.assertEqual(unbounded["selected"], ["grant:g0", "grant:g1"])
        self.assertTrue(certify(model, rules, unbounded)["certified"])
        self.assertTrue(check(model, rules, unbounded, apply(model, rules, unbounded))["feasible"])
        bounded = propose(model, rules)
        self.assertEqual((bounded["status"], bounded["termination"]), ("UNKNOWN", "MAX_INTEGER_DIGITS"))
        self.assertEqual((bounded["checked"], bounded["candidate_count"]), (4, 4))
        self.assertFalse(bounded["complete"])
        self.assertFalse(bounded["ties_complete"])
        self.assertIsNone(bounded["cost"])
        self.assertIsNone(bounded["selected"])
        self.assertEqual(bounded["alternatives"], [])
        self.assertEqual(bounded["lower_bound"], 0)
        self.assertEqual(json.loads(wire_json(bounded)), bounded)
        with self.assertRaisesRegex(ModelError, "no feasible incumbent"):
            apply(model, rules, bounded)
        self.assertFalse(certify(model, rules, bounded)["certified"])
        # Even a budget adjacent to the required metadata must not escape its
        # byte guard or imply that all checked candidates yielded a certificate.
        envelope_bytes = len(wire_json(bounded))
        self.assertEqual(len(wire_json(propose(model, rules, max_report_bytes=envelope_bytes))), envelope_bytes)
        with self.assertRaisesRegex(ModelError, "required result envelope"):
            propose(model, rules, max_report_bytes=envelope_bytes - 1)
        self.assertEqual(sys.get_int_max_str_digits(), limit)

    def test_source_one_over_rejected_across_sdk_paths_and_fingerprints(self):
        model, rules = independent_grants(cost=1)
        plan = propose(model, rules)
        oversized = copy.deepcopy(rules)
        oversized["edits"][0]["cost"] = JSON_INTEGER_LIMIT
        calls = [lambda: propose(model, oversized), lambda: propose(model, oversized, max_report_bytes=None), lambda: parse_constraints(model, oversized), lambda: feasibility(model, oversized), lambda: exhaustive_oracle(model, oversized), lambda: apply(model, oversized, plan), lambda: check(model, oversized, plan, model), lambda: certify(model, oversized, plan), lambda: canonical(oversized), lambda: wire_json(oversized)]
        for call in calls:
            with self.assertRaisesRegex(ModelError, "4300 decimal digits"):
                call()

    def test_twenty_item_exact_derived_sdk_incumbent_and_small_certification(self):
        model, rules = independent_grants(count=20)
        # Primitive feasibility: all twenty identical ALLOWs must disappear.
        # Construct a source-bound costed SDK incumbent without pretending to
        # enumerate 2**20 subsets or invoking the twelve-edit optimum oracle.
        plan = propose(model, rules, max_candidates=0, max_report_bytes=None)
        plan["selected"] = sorted("grant:g" + str(i) for i in range(20))
        plan["cost"] = 20 * (JSON_INTEGER_LIMIT - 1)
        self.assertLess(plan["cost"], 10 ** 4302)
        self.assertGreaterEqual(plan["cost"], 10 ** 4301)
        repaired = apply(model, rules, plan)
        self.assertFalse(repaired.grants)
        result = check(model, rules, plan, repaired)
        self.assertTrue(result["feasible"])
        self.assertEqual(result["cost"], plan["cost"])
        with self.assertRaisesRegex(ModelError, "4300 decimal digits"):
            wire_json(result)
        with self.assertRaisesRegex(ModelError, "12 edits"):
            certify(model, rules, plan)
        small, small_rules = independent_grants(cost=7)
        self.assertTrue(certify(small, small_rules, propose(small, small_rules))["certified"])

    def test_registered_cli_numeric_closure_and_forged_input_file_preservation(self):
        limit = sys.get_int_max_str_digits()
        scripts = Path(sysconfig.get_path("scripts"))
        cli = scripts / ("accessdelta.exe" if os.name == "nt" else "accessdelta")
        for mode in (0, 1):
            for digits in (4299, 4300):
                with self.subTest(mode=mode, digits=digits), tempfile.TemporaryDirectory() as directory:
                    folder = Path(directory)
                    model, rules = independent_grants(cost=10 ** digits - 1)
                    source, constraints, proposal, target = (folder / (name + ".json") for name in ("source", "constraints", "proposal", "target"))
                    source.write_bytes(canonical(model.to_dict()).encode("utf-8"))
                    constraints.write_bytes(wire_json(rules))
                    originals = (source.read_bytes(), constraints.read_bytes())
                    env = dict(os.environ, PYTHONUTF8=str(mode))
                    env.pop("PYTHONIOENCODING", None)
                    env.pop("PYTHONPATH", None)
                    def call(*args):
                        return subprocess.run([str(cli), *map(str, args)], env=env, capture_output=True, timeout=60)
                    run = call("propose", source, constraints)
                    plan = json.loads(run.stdout)
                    self.assertEqual(run.stdout, wire_json(plan))
                    self.assertEqual(run.stderr, b"")
                    proposal.write_bytes(run.stdout)
                    if digits == 4299:
                        self.assertEqual(run.returncode, 0)
                        self.assertEqual(plan["cost"], 2 * (10 ** digits - 1))
                        for op, tail in (("apply", [target]), ("check", [target]), ("certify", [])):
                            result = call(op, source, constraints, proposal, *tail)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            self.assertEqual(result.stderr, b"")
                            json.loads(result.stdout)
                    else:
                        self.assertEqual(run.returncode, 3)
                        self.assertEqual(plan["termination"], "MAX_INTEGER_DIGITS")
                        self.assertIsNone(plan["selected"])
                        self.assertIsNone(plan["cost"])
                        self.assertFalse(plan["complete"])
                        self.assertFalse(plan["ties_complete"])
                        self.assertEqual(plan["lower_bound"], 0)
                        for op, tail, wanted in (("apply", [target], 2), ("check", [target], 2), ("certify", [], 3)):
                            result = call(op, source, constraints, proposal, *tail)
                            self.assertEqual(result.returncode, wanted)
                            self.assertEqual(result.stdout, b"")
                            self.assertNotIn(b"Traceback", result.stderr)
                            typed = json.loads(result.stderr)
                            self.assertEqual(typed["status"], "UNKNOWN" if op == "certify" else "INVALID")
                        self.assertFalse(target.exists())
                    sentinel = b"existing destination stays"
                    target.write_bytes(sentinel)
                    absent = folder / "missing-parent" / "out.json"
                    # These are syntactically valid JSON numbers, beyond the
                    # documented interoperable integer-token resource bound.
                    for field in ("cost", "lower_bound", "candidate_count", "checked"):
                        marker = b"\"" + field.encode("ascii") + b"\": "
                        original = json.dumps(plan[field]).encode("ascii")
                        forged = run.stdout.replace(marker + original, marker + b"1" + b"0" * 4300)
                        proposal.write_bytes(forged)
                        for destination in (target, absent):
                            refused = call("apply", source, constraints, proposal, destination)
                            self.assertEqual(refused.returncode, 2)
                            self.assertEqual(json.loads(refused.stderr)["status"], "INVALID")
                            self.assertNotIn(b"Traceback", refused.stderr)
                            self.assertEqual(target.read_bytes(), sentinel)
                            self.assertFalse(absent.parent.exists())
                    constraints.write_bytes(originals[1].replace(b'"cost": ' + b"9" * digits, b'"cost": 1' + b"0" * 4300, 1))
                    refused = call("propose", source, constraints)
                    self.assertEqual(refused.returncode, 2)
                    self.assertEqual(json.loads(refused.stderr)["status"], "INVALID")
                    self.assertEqual(target.read_bytes(), sentinel)
                    constraints.write_bytes(originals[1])
                    self.assertEqual((source.read_bytes(), constraints.read_bytes()), originals)
        self.assertEqual(sys.get_int_max_str_digits(), limit)
