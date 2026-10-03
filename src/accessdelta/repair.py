"""Exact subset enumeration with honest candidate bounds and exact integer costs."""
from itertools import combinations
from .model import ModelError, fields, identifier, fingerprint
from .engine import effective


def parse_constraints(model, value):
    fields(value, ("required", "forbidden", "edits", "protected"))
    universe = set(model.universe)
    sets = []
    for name in ("required", "forbidden"):
        if not isinstance(value[name], list) or len(value[name]) > 25000:
            raise ModelError(f"{name} must be a list with at most 25000 requests")
        requests = []
        for req in value[name]:
            if not isinstance(req, list) or len(req) != 3 or not all(isinstance(x, str) for x in req) or tuple(req) not in universe:
                raise ModelError(f"{name} request outside declared universe")
            requests.append(tuple(req))
        if len(requests) != len(set(requests)):
            raise ModelError(f"duplicate {name} request")
        sets.append(frozenset(requests))
    if sets[0] & sets[1]:
        raise ModelError("required and forbidden access overlap")
    valid = {f"{kind}:{x.id}" for kind, items in (("grant", model.grants), ("membership", model.memberships), ("inheritance", model.inheritance)) for x in items}
    if not isinstance(value["protected"], list) or not all(isinstance(k, str) and k in valid for k in value["protected"]):
        raise ModelError("protected must reference existing typed items")
    protected = set(value["protected"])
    if len(protected) != len(value["protected"]):
        raise ModelError("duplicate protected item")
    if not isinstance(value["edits"], list) or len(value["edits"]) > 20:
        raise ModelError("exact repair supports at most 20 declared edits")
    edits = {}
    for edit in value["edits"]:
        fields(edit, ("kind", "id", "cost"))
        if edit["kind"] not in ("grant", "membership", "inheritance"):
            raise ModelError("unknown edit kind")
        key = f"{edit['kind']}:{identifier(edit['id'])}"
        if key not in valid or key in edits:
            raise ModelError("unknown or duplicate edit item")
        if type(edit["cost"]) is not int or edit["cost"] < 0:
            raise ModelError("edit cost must be an exact nonnegative integer")
        edits[key] = edit["cost"]
    normalized = {"required": [list(x) for x in sorted(sets[0])], "forbidden": [list(x) for x in sorted(sets[1])], "protected": sorted(protected), "edits": [{"kind": key.split(":", 1)[0], "id": key.split(":", 1)[1], "cost": cost} for key, cost in sorted(edits.items())]}
    return sets[0], sets[1], {k: v for k, v in edits.items() if k not in protected}, normalized


def feasibility(model, constraints):
    required, forbidden, _, normalized = parse_constraints(model, constraints)
    allowed = effective(model)
    missing, present = sorted(required - allowed), sorted(forbidden & allowed)
    return {"feasible": not missing and not present, "missing_required": [list(x) for x in missing], "present_forbidden": [list(x) for x in present], "allowed_count": len(allowed), "scope": "declared finite requests only", "constraints": fingerprint(normalized)}


def propose(model, constraints, max_candidates=65536):
    if type(max_candidates) is not int or max_candidates < 0:
        raise ModelError("max_candidates must be nonnegative integer")
    required, forbidden, edits, normalized = parse_constraints(model, constraints)
    keys = sorted(edits)
    best_cost, best = None, []
    checked = 0
    complete = True
    for size in range(len(keys) + 1):
        for subset in combinations(keys, size):
            if checked >= max_candidates:
                complete = False
                break
            checked += 1
            candidate = model.remove(subset)
            allowed = effective(candidate)  # full re-evaluation: removals can create ALLOW
            if required <= allowed and not forbidden & allowed:
                cost = sum(edits[k] for k in subset)
                if best_cost is None or cost < best_cost:
                    best_cost, best = cost, [list(subset)]
                elif cost == best_cost:
                    best.append(list(subset))
        if not complete:
            break
    best.sort()
    return {"status": "OPTIMAL" if complete and best else "INFEASIBLE" if complete else "UNKNOWN", "complete": complete, "checked": checked, "candidate_count": 2 ** len(keys), "model": model.digest, "constraints": fingerprint(normalized), "cost": best_cost, "selected": best[0] if best else None, "alternatives": best[1:], "ties_complete": complete, "lower_bound": best_cost if complete and best else 0, "scope": "minimum over declared unprotected deletion subsets"}


def apply(model, constraints, proposal):
    required, forbidden, edits, normalized = validate_proposal(model, constraints, proposal)
    selected = proposal["selected"]
    if selected is None:
        raise ModelError("proposal contains no feasible incumbent")
    repaired = model.remove(selected)
    allowed = effective(repaired)
    if not required <= allowed or forbidden & allowed:
        raise ModelError("selected edits fail complete finite feasibility recheck")
    return repaired


def validate_proposal(model, constraints, proposal):
    """Strict wire structure and source binding, without trusting optimization claims."""
    fields(proposal, ("status", "complete", "checked", "candidate_count", "model", "constraints", "cost", "selected", "alternatives", "ties_complete", "lower_bound", "scope"))
    required, forbidden, edits, normalized = parse_constraints(model, constraints)
    if proposal.get("model") != model.digest or proposal.get("constraints") != fingerprint(normalized):
        raise ModelError("proposal binding differs from model or constraints")
    if proposal["status"] not in ("OPTIMAL", "INFEASIBLE", "UNKNOWN") or type(proposal["complete"]) is not bool or type(proposal["ties_complete"]) is not bool:
        raise ModelError("invalid proposal status/completeness")
    if proposal["complete"] != (proposal["status"] != "UNKNOWN") or proposal["ties_complete"] != proposal["complete"]:
        raise ModelError("inconsistent proposal status/completeness")
    total = 2 ** len(edits)
    if type(proposal["candidate_count"]) is not int or proposal["candidate_count"] != total or type(proposal["checked"]) is not int or not 0 <= proposal["checked"] <= total:
        raise ModelError("invalid candidate accounting")
    if proposal["complete"] and proposal["checked"] != total:
        raise ModelError("complete proposal did not account for every candidate")
    selected, alternatives, cost = proposal["selected"], proposal["alternatives"], proposal["cost"]
    if not isinstance(alternatives, list):
        raise ModelError("alternatives must be a list")
    if selected is None:
        if cost is not None or alternatives or proposal["status"] == "OPTIMAL":
            raise ModelError("no-incumbent proposal has inconsistent result fields")
    else:
        if type(cost) is not int or cost < 0 or proposal["status"] == "INFEASIBLE":
            raise ModelError("incumbent cost must be exact nonnegative integer")
        all_subsets = [selected] + alternatives
        seen = set()
        for subset in all_subsets:
            if not isinstance(subset, list) or not all(isinstance(k, str) and k in edits for k in subset) or len(subset) != len(set(subset)):
                raise ModelError("proposal must select unique editable unprotected items")
            identity = tuple(sorted(subset))
            if identity in seen or sum(edits[k] for k in subset) != cost:
                raise ModelError("duplicate alternative or incorrect declared cost")
            seen.add(identity)
    lower = proposal["lower_bound"]
    if type(lower) is not int or lower < 0 or (cost is not None and lower > cost):
        raise ModelError("invalid finite lower bound")
    return required, forbidden, edits, normalized


def check(source, constraints, proposal, repaired):
    expected = apply(source, constraints, proposal)
    if repaired.digest != expected.digest:
        raise ModelError("edited model does not match proposed source deletions")
    required, forbidden, _, _ = parse_constraints(source, constraints)
    allowed = effective(repaired)
    return {"feasible": required <= allowed and not forbidden & allowed, "repaired": repaired.digest, "cost": proposal["cost"], "scope": "source-bound feasibility only; does not certify optimality or external permissions"}
