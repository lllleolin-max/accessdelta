"""Frozen round-1 probe: an optimum certificate must bind the claimed source."""
import copy
import json
from accessdelta import Model, propose, certify

model = Model.from_dict({"version": 1, "principals": ["p"], "roles": [], "actions": ["a"], "resources": ["r"], "memberships": [], "inheritance": [], "grants": [{"id": "g", "subject": {"kind": "principal", "id": "p"}, "effect": "ALLOW", "actions": ["a"], "resources": ["r"]}]})
rules = {"required": [], "forbidden": [["p", "a", "r"]], "edits": [{"kind": "grant", "id": "g", "cost": 1}], "protected": []}
plan = propose(model, rules)
checks = []
for field, value in (("model", "other-model"), ("constraints", "other-constraints"), ("ties_complete", False)):
    tampered = copy.deepcopy(plan)
    tampered[field] = value
    certified = certify(model, rules, tampered)["certified"]
    checks.append({"tampered": field, "certified": certified})
print(json.dumps({"checks": checks, "pass": not any(x["certified"] for x in checks)}))
assert not any(x["certified"] for x in checks), "source-unbound or incomplete certificate accepted"
