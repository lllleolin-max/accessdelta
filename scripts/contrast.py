"""Fair disclosed baselines, all using exactly the same models/constraints/costs."""
import json
from pathlib import Path
from accessdelta import Model, effective, propose, exhaustive_oracle
from accessdelta.repair import parse_constraints

ROOT = Path(__file__).resolve().parents[1] / "examples"


def greedy(model, constraints):
    required, forbidden, costs, _ = parse_constraints(model, constraints)
    chosen = []
    current = model
    while forbidden & effective(current):
        old = forbidden & effective(current)
        options = []
        for key, cost in sorted(costs.items()):
            if key in chosen:
                continue
            candidate = model.remove(chosen + [key])
            allowed = effective(candidate)
            remaining = forbidden & allowed
            # Same preservation constraint; no baseline shortcuts through deny semantics.
            if required <= allowed and len(remaining) < len(old):
                options.append((cost, key, candidate))
        if not options:
            return {"status": "STUCK", "selected": chosen, "cost": sum(costs[x] for x in chosen), "feasible": False}
        cost, key, current = min(options, key=lambda x: (x[0], x[1]))
        chosen.append(key)
    allowed = effective(current)
    return {"status": "FEASIBLE" if required <= allowed else "STUCK", "selected": sorted(chosen), "cost": sum(costs[x] for x in chosen), "feasible": required <= allowed and not forbidden & allowed}


def raw_grant_diff(before, after):
    old = {g.id: g for g in before.grants}
    new = {g.id: g for g in after.grants}
    return sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))


def main():
    results = []
    for name in ("cost-trap", "deny-diamond", "simple", "ties"):
        folder = ROOT / name
        before = Model.from_dict(json.loads((folder / "before.json").read_text()))
        model = Model.from_dict(json.loads((folder / "after.json").read_text()))
        constraints = json.loads((folder / "constraints.json").read_text())
        exact = propose(model, constraints)
        oracle = exhaustive_oracle(model, constraints)
        assert exact["status"] == oracle["status"] and exact["cost"] == oracle["cost"]
        assert [exact["selected"]] + exact["alternatives"] == oracle["solutions"]
        baseline = greedy(model, constraints)
        results.append({"case": name, "synthetic": True, "raw_changed_grants": raw_grant_diff(before, model), "effective_added": [list(x) for x in sorted(effective(model) - effective(before))], "greedy": baseline, "exact": {k: exact[k] for k in ("status", "cost", "selected", "alternatives", "checked")}})
    print(json.dumps({"cases": results, "competitor_benchmark": False}, indent=2))


if __name__ == "__main__":
    main()
