"""A deliberately small authorization language; never cloud IAM."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import hashlib
import json

MAX_JSON_BYTES = 4 * 1024 * 1024


def wire_json(value):
    """Exact ASCII-safe JSON protocol bytes, including one LF on every platform."""
    return (json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n").encode("ascii")


class ModelError(ValueError):
    """Malformed data or references."""


class UnsupportedModel(ModelError):
    """Input asks for semantics outside this finite language."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ModelError(f"expected keys {sorted(required)}, optional {sorted(optional)}")


def identifier(value):
    if not isinstance(value, str) or not value or len(value) > 160 or not value.isprintable() or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ModelError("identifiers must be nonempty strings of at most 160 printable characters")
    if any(c in value for c in "*?["):
        raise UnsupportedModel("wildcard syntax is unsupported; enumerate exact identifiers")
    return value


def names(value):
    if not isinstance(value, list) or len(value) > 1000:
        raise ModelError("expected list with at most 1000 identifiers")
    out = tuple(sorted(identifier(x) for x in value))
    if len(set(out)) != len(out):
        raise ModelError("duplicate identifier")
    return out


@dataclass(frozen=True)
class Member:
    id: str
    principal: str
    role: str


@dataclass(frozen=True)
class Edge:
    id: str
    role: str
    inherits: str


@dataclass(frozen=True)
class Grant:
    id: str
    kind: str
    subject: str
    effect: str
    actions: tuple[str, ...]
    resources: tuple[str, ...]


@dataclass(frozen=True)
class Model:
    principals: tuple[str, ...]
    roles: tuple[str, ...]
    actions: tuple[str, ...]
    resources: tuple[str, ...]
    memberships: tuple[Member, ...]
    inheritance: tuple[Edge, ...]
    grants: tuple[Grant, ...]

    @classmethod
    def from_dict(cls, data):
        fields(data, ("version", "principals", "roles", "actions", "resources", "memberships", "inheritance", "grants"))
        if type(data["version"]) is not int or data["version"] != 1:
            raise UnsupportedModel("only internal model version 1 is supported")
        p, r, a, s = (names(data[k]) for k in ("principals", "roles", "actions", "resources"))
        if len(p) * len(a) * len(s) > 25000:
            raise ModelError("finite request universe exceeds 25000 triples")
        parsed = {"memberships": [], "inheritance": [], "grants": []}
        for key in parsed:
            if not isinstance(data[key], list) or len(data[key]) > 1000:
                raise ModelError(f"{key} must be a list of at most 1000 items")
            seen = set()
            for item in data[key]:
                required = {"memberships": ("id", "principal", "role"), "inheritance": ("id", "role", "inherits"), "grants": ("id", "subject", "effect", "actions", "resources")}[key]
                fields(item, required, ("conditions",) if key == "grants" else ())
                ident = identifier(item["id"])
                if ident in seen:
                    raise ModelError(f"duplicate {key} id {ident}")
                seen.add(ident)
                if key == "memberships":
                    if item["principal"] not in p or item["role"] not in r:
                        raise ModelError("unknown membership reference")
                    parsed[key].append(Member(ident, item["principal"], item["role"]))
                elif key == "inheritance":
                    if item["role"] not in r or item["inherits"] not in r:
                        raise ModelError("unknown inheritance reference")
                    parsed[key].append(Edge(ident, item["role"], item["inherits"]))
                else:
                    fields(item["subject"], ("kind", "id"))
                    kind, subject = item["subject"]["kind"], item["subject"]["id"]
                    if kind not in ("principal", "role") or subject not in (p if kind == "principal" else r):
                        raise ModelError("unknown grant subject")
                    if item["effect"] not in ("ALLOW", "DENY"):
                        raise ModelError("effect must be ALLOW or DENY")
                    aa, ss = names(item["actions"]), names(item["resources"])
                    if not set(aa) <= set(a) or not set(ss) <= set(s):
                        raise ModelError("unknown grant action/resource")
                    if "conditions" in item and item["conditions"] != {}:
                        raise UnsupportedModel("conditions are unsupported; remove them only after explicit model review")
                    parsed[key].append(Grant(ident, kind, subject, item["effect"], aa, ss))
        # Kahn's algorithm rejects cycles, including unreachable ones, without recursion.
        children = {role: [] for role in r}
        incoming = {role: 0 for role in r}
        for edge in parsed["inheritance"]:
            children[edge.role].append(edge.inherits)
            incoming[edge.inherits] += 1
        queue = sorted(role for role in r if incoming[role] == 0)
        visited = 0
        while queue:
            role = queue.pop()
            visited += 1
            for parent in children[role]:
                incoming[parent] -= 1
                if incoming[parent] == 0:
                    queue.append(parent)
        if visited != len(r):
            raise ModelError("role inheritance cycle")
        return cls(p, r, a, s, *(tuple(sorted(parsed[k], key=lambda x: x.id)) for k in parsed))

    def to_dict(self):
        return {"version": 1, "principals": list(self.principals), "roles": list(self.roles), "actions": list(self.actions), "resources": list(self.resources), "memberships": [vars(x) for x in self.memberships], "inheritance": [vars(x) for x in self.inheritance], "grants": [{"id": x.id, "subject": {"kind": x.kind, "id": x.subject}, "effect": x.effect, "actions": list(x.actions), "resources": list(x.resources)} for x in self.grants]}

    @property
    def digest(self):
        return fingerprint(self.to_dict())

    @property
    def universe(self):
        return tuple(product(self.principals, self.actions, self.resources))

    def remove(self, keys):
        keys = set(keys)
        valid = {f"{kind}:{x.id}" for kind, items in (("grant", self.grants), ("membership", self.memberships), ("inheritance", self.inheritance)) for x in items}
        if not keys <= valid:
            raise ModelError("deletion references absent item")
        return Model(self.principals, self.roles, self.actions, self.resources, tuple(x for x in self.memberships if f"membership:{x.id}" not in keys), tuple(x for x in self.inheritance if f"inheritance:{x.id}" not in keys), tuple(x for x in self.grants if f"grant:{x.id}" not in keys))
