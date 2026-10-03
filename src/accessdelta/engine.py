"""Evaluate the complete finite model; an ALLOW path alone is never access."""
from collections import deque
from .model import ModelError


def role_paths(model, principal):
    paths = {}
    queue = deque()
    for member in model.memberships:
        if member.principal == principal and member.role not in paths:
            paths[member.role] = [f"principal:{principal}", f"membership:{member.id}", f"role:{member.role}"]
            queue.append(member.role)
    outgoing = {}
    for edge in model.inheritance:
        outgoing.setdefault(edge.role, []).append(edge)
    while queue:
        role = queue.popleft()
        for edge in outgoing.get(role, ()):
            if edge.inherits not in paths:
                paths[edge.inherits] = paths[role] + [f"inheritance:{edge.id}", f"role:{edge.inherits}"]
                queue.append(edge.inherits)
    return paths


def explain(model, request):
    request = tuple(request)
    if len(request) != 3 or request[0] not in model.principals or request[1] not in model.actions or request[2] not in model.resources:
        raise ModelError("request outside declared principal/action/resource universe")
    principal, action, resource = request
    paths = role_paths(model, principal)
    evidence = []
    for grant in model.grants:
        path = [f"principal:{principal}"] if grant.kind == "principal" and grant.subject == principal else paths.get(grant.subject) if grant.kind == "role" else None
        if path is not None and action in grant.actions and resource in grant.resources:
            evidence.append({"grant": grant.id, "effect": grant.effect, "path": path + [f"grant:{grant.id}"]})
    deny = any(x["effect"] == "DENY" for x in evidence)
    allow = any(x["effect"] == "ALLOW" for x in evidence)
    return {"request": list(request), "decision": "DENY" if deny or not allow else "ALLOW", "reason": "EXPLICIT_DENY" if deny else "MATCHED_ALLOW" if allow else "DEFAULT_DENY", "evidence": evidence}


def effective(model):
    return frozenset(request for request in model.universe if explain(model, request)["decision"] == "ALLOW")


def compare(before, after):
    if (before.principals, before.actions, before.resources) != (after.principals, after.actions, after.resources):
        raise ModelError("comparison requires identical declared request universes")
    old, new = effective(before), effective(after)
    added, removed = sorted(new - old), sorted(old - new)
    return {"before": before.digest, "after": after.digest, "universe_size": len(after.universe), "added": [explain(after, x) for x in added], "removed": [explain(before, x) for x in removed], "retained_count": len(old & new)}
