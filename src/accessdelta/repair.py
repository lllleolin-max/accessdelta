"""Exact subset enumeration with honest candidate bounds and exact integer costs."""
from itertools import combinations
from .model import ModelError, fields, identifier, fingerprint, MAX_JSON_BYTES, wire_json, integer_fits_wire
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
        if not integer_fits_wire(edit["cost"]):
            raise ModelError("source edit cost exceeds 4300 decimal digits")
        edits[key] = edit["cost"]
    normalized = {"required": [list(x) for x in sorted(sets[0])], "forbidden": [list(x) for x in sorted(sets[1])], "protected": sorted(protected), "edits": [{"kind": key.split(":", 1)[0], "id": key.split(":", 1)[1], "cost": cost} for key, cost in sorted(edits.items())]}
    return sets[0], sets[1], {k: v for k, v in edits.items() if k not in protected}, normalized


def feasibility(model, constraints):
    required, forbidden, _, normalized = parse_constraints(model, constraints)
    allowed = effective(model)
    missing, present = sorted(required - allowed), sorted(forbidden & allowed)
    return {"feasible": not missing and not present, "missing_required": [list(x) for x in missing], "present_forbidden": [list(x) for x in present], "allowed_count": len(allowed), "scope": "declared finite requests only", "constraints": fingerprint(normalized)}


def propose(model, constraints, max_candidates=65536, *, max_report_bytes=MAX_JSON_BYTES):
    if type(max_candidates) is not int or max_candidates < 0:
        raise ModelError("max_candidates must be nonnegative integer")
    if max_report_bytes is not None and (type(max_report_bytes) is not int or max_report_bytes <= 0):
        raise ModelError("max_report_bytes must be a positive integer or None for explicit unbounded SDK output")
    required, forbidden, edits, normalized = parse_constraints(model, constraints)
    keys = sorted(edits)
    total = 2 ** len(keys)
    model_hash, constraints_hash = model.digest, fingerprint(normalized)
    def envelope(cost, complete, checked, termination):
        return {"status": "OPTIMAL" if complete and cost is not None else "INFEASIBLE" if complete else "UNKNOWN", "complete": complete, "checked": checked, "candidate_count": total, "model": model_hash, "constraints": constraints_hash, "cost": cost, "selected": None, "alternatives": [], "ties_complete": complete, "lower_bound": cost if complete and cost is not None else 0, "scope": "minimum over declared unprotected deletion subsets", "termination": termination}
    if max_report_bytes is not None and len(wire_json(envelope(None, False, total, "MAX_INTEGER_DIGITS"))) > max_report_bytes:
        raise ModelError("report byte budget cannot fit the required result envelope")
    key_bytes = {key: len(wire_json(key)) - 1 for key in keys}
    best_cost, best = None, []
    best_bytes = 0
    checked = 0
    complete = True
    termination = "COMPLETE"
    for size in range(len(keys) + 1):
        for subset in combinations(keys, size):
            if checked >= max_candidates:
                complete = False
                termination = "MAX_CANDIDATES"
                break
            checked += 1
            candidate = model.remove(subset)
            allowed = effective(candidate)  # full re-evaluation: removals can create ALLOW
            if required <= allowed and not forbidden & allowed:
                cost = sum(edits[k] for k in subset)
                if best_cost is None or cost <= best_cost:
                    if max_report_bytes is not None and not integer_fits_wire(cost):
                        complete = False
                        termination = "MAX_INTEGER_DIGITS"
                        break
                    lower = best_cost is None or cost < best_cost
                    subset_bytes = 2 + sum(key_bytes[k] for k in subset) + 2 * max(len(subset) - 1, 0)
                    byte_sum = subset_bytes if lower else best_bytes + subset_bytes
                    count = 1 if lower else len(best) + 1
                    if max_report_bytes is not None:
                        # Reserve the largest incomplete metadata (including
                        # final checked/cost digits). If this is the last
                        # candidate, use the exact complete envelope instead.
                        last = checked == total
                        shell = envelope(cost, last, total, "COMPLETE" if last else "MAX_REPORT_BYTES")
                        if not last:
                            shell["lower_bound"] = cost  # sizing only, never emitted as an UNKNOWN proof
                        # Replace selected:null and alternatives:[] by their
                        # incremental JSON lengths. Selection order does not
                        # change the sum of encoded subset lengths.
                        projected = len(wire_json(shell)) - 4 + byte_sum + 2 * max(count - 2, 0)
                        if projected > max_report_bytes:
                            complete = False
                            termination = "MAX_REPORT_BYTES"
                            break
                    if lower:
                        best_cost, best = cost, [list(subset)]
                    else:
                        best.append(list(subset))
                    best_bytes = byte_sum
        if not complete:
            break
    best.sort()
    result = envelope(best_cost, complete, checked, termination)
    result.update(selected=best[0] if best else None, alternatives=best[1:])
    if max_report_bytes is not None and len(wire_json(result)) > max_report_bytes:
        raise ModelError("report byte accounting exceeded its declared budget")
    return result


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
    fields(proposal, ("status", "complete", "checked", "candidate_count", "model", "constraints", "cost", "selected", "alternatives", "ties_complete", "lower_bound", "scope"), ("termination",))
    required, forbidden, edits, normalized = parse_constraints(model, constraints)
    if proposal.get("model") != model.digest or proposal.get("constraints") != fingerprint(normalized):
        raise ModelError("proposal binding differs from model or constraints")
    if proposal["status"] not in ("OPTIMAL", "INFEASIBLE", "UNKNOWN") or type(proposal["complete"]) is not bool or type(proposal["ties_complete"]) is not bool:
        raise ModelError("invalid proposal status/completeness")
    if proposal["complete"] != (proposal["status"] != "UNKNOWN") or proposal["ties_complete"] != proposal["complete"]:
        raise ModelError("inconsistent proposal status/completeness")
    if "termination" in proposal and (proposal["termination"] not in ("COMPLETE", "MAX_CANDIDATES", "MAX_REPORT_BYTES", "MAX_INTEGER_DIGITS") or (proposal["termination"] == "COMPLETE") != proposal["complete"]):
        raise ModelError("inconsistent proposal termination/completeness")
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
