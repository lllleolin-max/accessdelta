"""Generate disclosed synthetic internal deployment-review models."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "examples"


def grant(id, role, action, resource, effect="ALLOW", kind="role"):
    return {"id": id, "subject": {"kind": kind, "id": role}, "effect": effect, "actions": [action], "resources": [resource]}


def base(roles):
    return {"version": 1, "principals": ["alice"], "roles": roles, "actions": ["read", "write"], "resources": ["report", "deploy", "secret"], "memberships": [], "inheritance": [], "grants": []}


def constraints(required, forbidden, edits, protected=()):
    return {"required": required, "forbidden": forbidden, "edits": [{"kind": k.split(":")[0], "id": k.split(":")[1], "cost": v} for k, v in edits], "protected": list(protected)}


def write(name, before, after, rules):
    folder = ROOT / name
    folder.mkdir(parents=True, exist_ok=True)
    for label, data in (("before", before), ("after", after), ("constraints", rules)):
        (folder / f"{label}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    model = base(["entry", "reader", "writer"])
    model["memberships"] = [{"id": "alice-entry", "principal": "alice", "role": "entry"}]
    model["inheritance"] = [{"id": "read-edge", "role": "entry", "inherits": "reader"}, {"id": "write-edge", "role": "entry", "inherits": "writer"}]
    model["grants"] = [grant("read-required", "reader", "read", "report"), grant("deploy-write", "writer", "write", "deploy"), grant("secret-read", "writer", "read", "secret")]
    before = json.loads(json.dumps(model))
    before["inheritance"] = before["inheritance"][:1]
    rules = constraints([["alice", "read", "report"]], [["alice", "write", "deploy"], ["alice", "read", "secret"]], [("grant:deploy-write", 2), ("grant:secret-read", 2), ("inheritance:write-edge", 3), ("membership:alice-entry", 1)], ["grant:read-required", "inheritance:read-edge"])
    write("cost-trap", before, model, rules)
    model = base(["entry", "allow-branch", "deny-branch", "common"])
    model["memberships"] = [{"id": "entry-member", "principal": "alice", "role": "entry"}]
    model["inheritance"] = [{"id": "allow-edge", "role": "entry", "inherits": "allow-branch"}, {"id": "deny-edge", "role": "entry", "inherits": "deny-branch"}, {"id": "allow-common", "role": "allow-branch", "inherits": "common"}, {"id": "deny-common", "role": "deny-branch", "inherits": "common"}]
    model["grants"] = [grant("read-required", "alice", "read", "report", kind="principal"), grant("alternate-secret", "alice", "read", "secret", kind="principal"), grant("common-secret", "common", "read", "secret"), grant("deny-secret", "deny-branch", "read", "secret", effect="DENY"), grant("bad-write", "deny-branch", "write", "deploy")]
    before = json.loads(json.dumps(model))
    before["grants"] = [g for g in before["grants"] if g["id"] != "bad-write"]
    rules = constraints([["alice", "read", "report"]], [["alice", "write", "deploy"], ["alice", "read", "secret"]], [("inheritance:deny-edge", 0), ("membership:entry-member", 0), ("grant:bad-write", 4)], ["grant:read-required", "grant:deny-secret"])
    write("deny-diamond", before, model, rules)
    model = base([])
    model["grants"] = [grant("required", "alice", "read", "report", kind="principal"), grant("unwanted", "alice", "write", "deploy", kind="principal")]
    before = json.loads(json.dumps(model))
    before["grants"] = before["grants"][:1]
    write("simple", before, model, constraints([["alice", "read", "report"]], [["alice", "write", "deploy"]], [("grant:unwanted", 2)], ["grant:required"]))
    model = base(["writer"])
    model["memberships"] = [{"id": "join", "principal": "alice", "role": "writer"}]
    model["grants"] = [grant("one", "writer", "write", "deploy"), grant("two", "writer", "write", "deploy"), grant("irrelevant", "alice", "read", "report", kind="principal")]
    before = json.loads(json.dumps(model))
    before["memberships"] = []
    write("ties", before, model, constraints([], [["alice", "write", "deploy"]], [("membership:join", 2), ("grant:one", 1), ("grant:two", 1), ("grant:irrelevant", 0)]))


if __name__ == "__main__":
    main()
