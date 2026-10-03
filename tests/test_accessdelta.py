import copy
import json
from pathlib import Path
import random
import unittest
from accessdelta import Model, ModelError, UnsupportedModel, compare, effective, explain, propose, apply, check, certify, exhaustive_oracle
from accessdelta.oracle import allowed_by_closure

ROOT = Path(__file__).resolve().parents[1] / "examples"


def fixture(name="deny-diamond"):
    folder = ROOT / name
    return Model.from_dict(json.loads((folder / "after.json").read_text())), json.loads((folder / "constraints.json").read_text())


class AuthorizationTests(unittest.TestCase):
    def test_deny_diamond(self):
        model, _ = fixture()
        item = explain(model, ("alice", "read", "secret"))
        self.assertEqual(item["reason"], "EXPLICIT_DENY")
        self.assertEqual({x["effect"] for x in item["evidence"]}, {"ALLOW", "DENY"})
        self.assertIn("inheritance:deny-edge", next(x["path"] for x in item["evidence"] if x["effect"] == "DENY"))

    def test_nonmonotone_member_and_edge_deletion(self):
        model, constraints = fixture()
        for key in ("inheritance:deny-edge", "membership:entry-member"):
            allowed = effective(model.remove([key]))
            self.assertIn(("alice", "read", "secret"), allowed)
            self.assertNotIn(("alice", "write", "deploy"), allowed)
        proposal = propose(model, constraints)
        self.assertEqual(proposal["selected"], ["grant:bad-write"])
        self.assertEqual(proposal["cost"], 4)
        repaired = apply(model, constraints, proposal)
        self.assertTrue(check(model, constraints, proposal, repaired)["feasible"])

    def test_compare_full_models(self):
        model, _ = fixture("cost-trap")
        before = Model.from_dict(json.loads((ROOT / "cost-trap" / "before.json").read_text()))
        report = compare(before, model)
        self.assertEqual(len(report["added"]), 2)
        self.assertEqual(report["removed"], [])
        self.assertEqual(report["retained_count"], 1)

    def test_default_and_direct_deny(self):
        model, _ = fixture("simple")
        self.assertEqual(explain(model, ("alice", "read", "secret"))["reason"], "DEFAULT_DENY")
        data = model.to_dict()
        data["grants"].append({"id": "deny", "subject": {"kind": "principal", "id": "alice"}, "effect": "DENY", "actions": ["write"], "resources": ["deploy"]})
        self.assertNotIn(("alice", "write", "deploy"), effective(Model.from_dict(data)))

    def test_cycle_and_unknown_references(self):
        model, _ = fixture()
        data = model.to_dict()
        data["inheritance"].append({"id": "cycle", "role": "common", "inherits": "entry"})
        with self.assertRaises(ModelError):
            Model.from_dict(data)
        data = model.to_dict()
        data["memberships"][0]["principal"] = "nobody"
        with self.assertRaises(ModelError):
            Model.from_dict(data)

    def test_unsupported_conditions_and_wildcards(self):
        model, _ = fixture()
        data = model.to_dict()
        data["grants"][0]["conditions"] = {"eq": {"region": "east"}}
        with self.assertRaises(UnsupportedModel):
            Model.from_dict(data)
        data = model.to_dict()
        data["resources"] = ["*"]
        with self.assertRaises(UnsupportedModel):
            Model.from_dict(data)

    def test_unknown_inspection_universe(self):
        model, _ = fixture()
        with self.assertRaises(ModelError):
            explain(model, ("bob", "read", "secret"))

    def test_permutation_invariance(self):
        model, rules = fixture("ties")
        data = model.to_dict()
        for value in data.values():
            if isinstance(value, list):
                value.reverse()
        rules2 = copy.deepcopy(rules)
        rules2["edits"].reverse()
        self.assertEqual(model.digest, Model.from_dict(data).digest)
        self.assertEqual(propose(model, rules), propose(Model.from_dict(data), rules2))

    def test_empty_universe(self):
        data = {"version": 1, "principals": [], "roles": [], "actions": [], "resources": [], "memberships": [], "inheritance": [], "grants": []}
        model = Model.from_dict(data)
        rules = {"required": [], "forbidden": [], "edits": [], "protected": []}
        proposal = propose(model, rules)
        self.assertEqual((proposal["status"], proposal["cost"], proposal["selected"]), ("OPTIMAL", 0, []))
        self.assertTrue(certify(model, rules, proposal)["certified"])


class RepairTests(unittest.TestCase):
    def test_ties_zero_cost(self):
        model, rules = fixture("ties")
        proposal = propose(model, rules)
        self.assertEqual(proposal["cost"], 2)
        self.assertEqual(len(proposal["alternatives"]), 3)
        self.assertTrue(certify(model, rules, proposal)["certified"])

    def test_protected_impossible(self):
        model, rules = fixture("simple")
        rules["protected"].append("grant:unwanted")
        result = propose(model, rules)
        self.assertEqual(result["status"], "INFEASIBLE")
        self.assertEqual(result, propose(model, rules, 1))

    def test_bound_without_and_with_incumbent(self):
        model, rules = fixture("simple")
        self.assertEqual(propose(model, rules, 0)["status"], "UNKNOWN")
        model, rules = fixture("ties")
        result = propose(model, rules, 5)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNotNone(result["selected"])
        self.assertFalse(result["ties_complete"])
        self.assertFalse(certify(model, rules, result)["certified"])

    def test_protected_required_cannot_break(self):
        model, rules = fixture("cost-trap")
        proposal = propose(model, rules)
        self.assertEqual(proposal["selected"], ["inheritance:write-edge"])
        self.assertEqual(proposal["cost"], 3)
        self.assertIn(("alice", "read", "report"), effective(apply(model, rules, proposal)))

    def test_tampered_cost_binding_and_model(self):
        model, rules = fixture("simple")
        proposal = propose(model, rules)
        proposal["cost"] = 0
        with self.assertRaises(ModelError):
            apply(model, rules, proposal)
        proposal = propose(model, rules)
        proposal["model"] = "changed"
        with self.assertRaises(ModelError):
            apply(model, rules, proposal)
        proposal = propose(model, rules)
        with self.assertRaises(ModelError):
            check(model, rules, proposal, model)

    def test_exact_integer_and_request_constraints(self):
        model, rules = fixture("simple")
        rules["edits"][0]["cost"] = 0.5
        with self.assertRaises(ModelError):
            propose(model, rules)
        _, rules = fixture("simple")
        rules["required"] = rules["forbidden"][:]
        with self.assertRaises(ModelError):
            propose(model, rules)

    def test_random_dags_independent_oracle(self):
        rng = random.Random(713)
        for case in range(64):
            roles = [f"r{i}" for i in range(4)]
            data = {"version": 1, "principals": ["p"], "roles": roles, "actions": ["read", "write"], "resources": ["x", "y"], "memberships": [{"id": "m", "principal": "p", "role": "r0"}], "inheritance": [], "grants": []}
            for i in range(4):
                for j in range(i + 1, 4):
                    if rng.random() < 0.45:
                        data["inheritance"].append({"id": f"e{i}{j}", "role": roles[i], "inherits": roles[j]})
                data["grants"].append({"id": f"g{i}", "subject": {"kind": "role", "id": roles[i]}, "effect": rng.choice(["ALLOW", "DENY"]), "actions": [rng.choice(["read", "write"])], "resources": [rng.choice(["x", "y"])]})
            model = Model.from_dict(data)
            self.assertEqual(effective(model), allowed_by_closure(model))
            edits = [{"kind": "grant", "id": g["id"], "cost": rng.randrange(4)} for g in data["grants"]] + [{"kind": "membership", "id": "m", "cost": rng.randrange(4)}]
            rules = {"required": [], "forbidden": [["p", "write", "x"], ["p", "read", "y"]], "edits": edits, "protected": []}
            exact, oracle = propose(model, rules), exhaustive_oracle(model, rules)
            self.assertEqual((exact["status"], exact["cost"], [exact["selected"]] + exact["alternatives"]), (oracle["status"], oracle["cost"], oracle["solutions"]))


if __name__ == "__main__":
    unittest.main()
