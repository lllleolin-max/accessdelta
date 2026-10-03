"""JSON CLI. Only apply writes a new local model; no cloud or account operations."""
import argparse
import json
from pathlib import Path
import sys
from . import Model, ModelError, UnsupportedModel, compare, explain, propose, apply, check, certify
from .model import MAX_JSON_BYTES, canonical, wire_json, json_integer


def emit(value, file=None):
    # ASCII is valid UTF-8 and is encodable by legacy Windows pipe codecs.
    # JSON escapes change only wire representation, never identifiers/values.
    stream = file or sys.stdout
    data = wire_json(value)
    if hasattr(stream, "buffer"):
        stream.buffer.write(data)
    else:
        stream.write(data.decode("ascii"))


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ModelError("arguments: " + message)

    def print_help(self, file=None):
        emit({"help": self.format_help()}, file)


def read(path):
    def unique_object(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ModelError(f"duplicate JSON object key: {key}")
            obj[key] = value
        return obj
    def no_constant(value):
        raise ModelError(f"nonfinite JSON constant: {value}")
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
        raise ModelError("JSON input exceeds 4 MiB")
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object, parse_constant=no_constant, parse_int=json_integer)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ModelError(f"invalid UTF-8 JSON: {exc}") from exc


def load(path):
    return Model.from_dict(read(path))


def main(argv=None):
    parser = JSONArgumentParser(prog="accessdelta")
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
    p.add_argument("--max-report-bytes", type=int, default=MAX_JSON_BYTES)
    for name in ("apply", "check", "certify"):
        p = commands.add_parser(name)
        p.add_argument("model")
        p.add_argument("constraints")
        p.add_argument("proposal")
        if name == "apply":
            p.add_argument("output")
        if name == "check":
            p.add_argument("repaired")
    try:
        args = parser.parse_args(argv)
        if args.command == "compare":
            result = compare(load(args.before), load(args.after))
        elif args.command == "inspect":
            result = explain(load(args.model), (args.principal, args.action, args.resource))
        elif args.command == "propose":
            if not 0 < args.max_report_bytes <= MAX_JSON_BYTES:
                raise ModelError("CLI report budget must be positive and at most 4 MiB")
            result = propose(load(args.model), read(args.constraints), args.max_candidates, max_report_bytes=args.max_report_bytes)
        else:
            source, constraints, proposal = load(args.model), read(args.constraints), read(args.proposal)
            if args.command == "apply":
                target = Path(args.output)
                repaired = apply(source, constraints, proposal)
                # Compact canonical bytes cannot exceed their admitted source
                # representation. Avoid pretty-print inflation of consumable files.
                output = canonical(repaired.to_dict()).encode("utf-8")
                if len(output) > MAX_JSON_BYTES:
                    raise ModelError("edited model exceeds 4 MiB; no destination written")
                with target.open("xb") as stream:
                    stream.write(output)
                result = {"written": str(target), "model": repaired.digest, "scope": "new local JSON only"}
            elif args.command == "check":
                result = check(source, constraints, proposal, load(args.repaired))
            else:
                result = certify(source, constraints, proposal)
        emit(result)
        if result.get("status") == "UNKNOWN":
            return 3
        if result.get("status") == "INFEASIBLE" or result.get("certified") is False:
            return 4
        return 0
    except UnsupportedModel as exc:
        emit({"status": "UNKNOWN", "error": str(exc)}, sys.stderr)
        return 3
    except (ModelError, OSError, json.JSONDecodeError) as exc:
        emit({"status": "INVALID", "error": str(exc)}, sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
