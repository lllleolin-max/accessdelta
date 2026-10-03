"""Replace machine path prefixes only inside JSON strings; never rewrite numbers.

Original evidence bytes must be backed up before current tracked receipts change.
This is publication sanitation, not an application correction or history rewrite.
"""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
FILES = ("round1-after.json", "round1-before-decoding-failure.json", "round1-before.json", "round2-after.json", "round2-before.json", "round3-after.json", "round3-before.json")
JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def portable_string(value):
    paths = ((ROOT, "<REPO>"), (ROOT.parent.parent.parent, "<WORKSPACE>"), (Path(tempfile.gettempdir()), "<TEMP>"), (Path.home(), "<USER>"))
    for path, marker in sorted(paths, key=lambda x: len(str(x[0])), reverse=True):
        variants = {str(path), path.as_posix()}
        for _ in range(3):
            variants |= {json.dumps(x, ensure_ascii=ascii_mode)[1:-1] for x in list(variants) for ascii_mode in (False, True)}
        for prefix in sorted(variants, key=len, reverse=True):
            value = re.sub(re.escape(prefix), lambda _: marker, value, flags=re.IGNORECASE)
    return value


def portable_json(text):
    # Operate on string tokens, preserving byte representations of numbers,
    # indentation, newlines, booleans and null. Do not json.load/dump a report.
    def replace(match):
        original = match.group()
        value = json.loads(original)
        portable = portable_string(value)
        return original if portable == value else json.dumps(portable, ensure_ascii=False)
    result = JSON_STRING.sub(replace, text)
    json.loads(result)  # validate only; never serialize the parsed numeric values
    return result


def main():
    backup = ROOT.parent / "publication/private-local/accessdelta" / ("raw-evidence-" + uuid.uuid4().hex)
    backup.mkdir(parents=True, exist_ok=False)
    manifest = {"scope": "seven pre-sanitation current receipts; no Git history rewrite", "files": []}
    originals = []
    for name in FILES:
        source = ROOT / "docs/evidence" / name
        data = source.read_bytes()
        target = backup / name
        target.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        manifest["files"].append({"file": name, "sha256": digest, "size": len(data)})
        originals.append((source, data))
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    for source, data in originals:
        transformed = portable_json(data.decode("utf-8"))
        source.write_bytes(transformed.encode("utf-8"))
    print(json.dumps({"backup": str(backup), "files": len(originals), "history_rewritten": False}))


if __name__ == "__main__":
    main()
