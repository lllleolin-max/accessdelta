"""Independent small-instance oracle: Boolean closure, bitmasks, no engine calls."""
from itertools import product
from .model import ModelError
from .repair import parse_constraints


def allowed_by_closure(model, deleted=()):
    deleted = set(deleted)
    reachable = {(r, r) for r in model.roles}
    reachable.update((e.role, e.inherits) for e in model.inheritance if f"inheritance:{e.id}" not in deleted)
    changed = True
    while changed:
        new = {(a, d) for a, b in reachable for c, d in reachable if b == c}
        changed = not new <= reachable
        reachable |= new
    attached = {(m.principal, parent) for m in model.memberships if f"membership:{m.id}" not in deleted for child, parent in reachable if child == m.role}
    allowed = set()
    for p, a, r in product(model.principals, model.actions, model.resources):
        effects = {g.effect for g in model.grants if f"grant:{g.id}" not in deleted and a in g.actions and r in g.resources and ((g.kind == "principal" and g.subject == p) or (g.kind == "role" and (p, g.subject) in attached))}
        if "ALLOW" in effects and "DENY" not in effects:
            allowed.add((p, a, r))
    return frozenset(allowed)


def exhaustive_oracle(model, constraints):
    required, forbidden, edits, _ = parse_constraints(model, constraints)
    if len(edits) > 12 or len(model.roles) > 24 or len(model.universe) > 256:
        raise ModelError("independent oracle limited to 12 edits, 24 roles, 256 requests")
    keys = sorted(edits)
    best, solutions = None, []
    for bits in range(1 << len(keys)):
        subset = [key for i, key in enumerate(keys) if bits & (1 << i)]
        allowed = allowed_by_closure(model, subset)
        if required <= allowed and not forbidden & allowed:
            cost = sum(edits[k] for k in subset)
            if best is None or cost < best:
                best, solutions = cost, [subset]
            elif cost == best:
                solutions.append(subset)
    solutions.sort()
    return {"status": "OPTIMAL" if solutions else "INFEASIBLE", "cost": best, "solutions": solutions, "checked": 1 << len(keys)}


def certify(model, constraints, proposal):
    """Recompute small optimum independently; never trust proposal status/claimed ties."""
    oracle = exhaustive_oracle(model, constraints)
    claimed = [proposal["selected"]] + proposal["alternatives"] if proposal.get("selected") is not None else []
    valid = proposal.get("complete") is True and proposal.get("status") == oracle["status"] and proposal.get("cost") == oracle["cost"] and claimed == oracle["solutions"]
    return {"certified": valid, "oracle": oracle, "scope": "independent finite deletion optimum only; not cloud or outside-universe safety"}
