"""JSON CLI. Only apply writes a new local model; no cloud or account operations."""
import argparse
import json
from pathlib import Path
import sys
from . import Model, ModelError, UnsupportedModel, compare, explain, propose, apply, check, certify


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load(path):
    return Model.from_dict(read(path))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="accessdelta")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("compare")
    p.add_argument("before")
    p.add_argument("after")
    p = commands.add_parser("inspect")
    p.add_argument("model")
    p.add_argument("principal")
    p.add_argument("action")
    p.add_argument("resource")
    p = commands.add_parser("propose")
    p.add_argument("model")
    p.add_argument("constraints")
    p.add_argument("--max-candidates", type=int, default=65536)
    for name in ("apply", "check", "certify"):
        p = commands.add_parser(name)
        p.add_argument("model")
        p.add_argument("constraints")
        p.add_argument("proposal")
        if name == "apply":
            p.add_argument("output")
        if name == "check":
            p.add_argument("repaired")
    args = parser.parse_args(argv)
    try:
        if args.command == "compare":
            result = compare(load(args.before), load(args.after))
        elif args.command == "inspect":
            result = explain(load(args.model), (args.principal, args.action, args.resource))
        elif args.command == "propose":
            result = propose(load(args.model), read(args.constraints), args.max_candidates)
        else:
            source, constraints, proposal = load(args.model), read(args.constraints), read(args.proposal)
            if args.command == "apply":
                target = Path(args.output)
                repaired = apply(source, constraints, proposal)
                with target.open("x", encoding="utf-8", newline="\n") as stream:
                    json.dump(repaired.to_dict(), stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
                result = {"written": str(target), "model": repaired.digest, "scope": "new local JSON only"}
            elif args.command == "check":
                result = check(source, constraints, proposal, load(args.repaired))
            else:
                result = certify(source, constraints, proposal)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if result.get("status") == "UNKNOWN":
            return 3
        if result.get("status") == "INFEASIBLE" or result.get("certified") is False:
            return 4
        return 0
    except UnsupportedModel as exc:
        print(json.dumps({"status": "UNKNOWN", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3
    except (ModelError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
