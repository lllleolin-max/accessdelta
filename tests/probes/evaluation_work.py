"""Frozen round-3 probe: dense finite requests should not repeat role traversal."""
import json
from time import perf_counter
from unittest.mock import patch
from accessdelta import Model, effective
from accessdelta import engine
from accessdelta.oracle import allowed_by_closure

principals = [f"p{i}" for i in range(8)]
roles = [f"r{i}" for i in range(12)]
actions = [f"a{i}" for i in range(40)]
resources = [f"s{i}" for i in range(50)]
data = {"version": 1, "principals": principals, "roles": roles, "actions": actions, "resources": resources, "memberships": [{"id": f"m{i}", "principal": p, "role": "r0"} for i, p in enumerate(principals)], "inheritance": [{"id": f"e{i}", "role": f"r{i}", "inherits": f"r{i+1}"} for i in range(11)], "grants": [{"id": "dense-allow", "subject": {"kind": "role", "id": "r11"}, "effect": "ALLOW", "actions": actions, "resources": resources}, {"id": "restrict", "subject": {"kind": "role", "id": "r5"}, "effect": "DENY", "actions": actions[:20], "resources": resources[:20]}]}
model = Model.from_dict(data)
start = perf_counter()
with patch.object(engine, "role_paths", wraps=engine.role_paths) as traversal:
    allowed = effective(model)
    traversals = traversal.call_count
elapsed = perf_counter() - start
oracle = allowed_by_closure(model)
print(json.dumps({"universe": len(model.universe), "allowed": len(allowed), "equal_independent_closure": allowed == oracle, "role_traversals": traversals, "traversal_budget": len(principals), "elapsed_seconds": elapsed, "pass": allowed == oracle and traversals <= len(principals)}))
assert allowed == oracle, "effective results differ from independent closure"
assert traversals <= len(principals), "role graph retraversed per action/resource request"
